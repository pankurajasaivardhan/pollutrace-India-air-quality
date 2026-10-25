package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// Station IDs are selected only after checking location, license and PM2.5 coverage.
// Configure OPENAQ_STATIONS as JSON: {"Delhi":123,...}. Keys never reach the browser.
type LiveConfig struct {
	Key      string
	Stations map[string]int
	BaseURL  string // test injection only; main uses the official default
	Client   *http.Client
	mu       sync.Mutex
	cache    map[string]liveCache
}
type liveCache struct {
	data  any
	until time.Time
}
type aqParameter struct {
	Name        string `json:"name"`
	Units       string `json:"units"`
	DisplayName string `json:"displayName"`
}
type aqSensor struct {
	ID        int         `json:"id"`
	Parameter aqParameter `json:"parameter"`
}
type aqLicense struct {
	ID                    int    `json:"id"`
	Name                  string `json:"name"`
	Attribution           any    `json:"attribution"`
	SourceURL             string `json:"sourceUrl"`
	RedistributionAllowed *bool  `json:"redistributionAllowed"`
}
type aqLocation struct {
	ID       int    `json:"id"`
	Name     string `json:"name"`
	Locality string `json:"locality"`
	Timezone string `json:"timezone"`
	Country  struct {
		Code string `json:"code"`
	} `json:"country"`
	Coordinates any         `json:"coordinates"`
	Provider    any         `json:"provider"`
	Owner       any         `json:"owner"`
	Sensors     []aqSensor  `json:"sensors"`
	Licenses    []aqLicense `json:"licenses"`
}
type aqLatest struct {
	Datetime struct {
		UTC   string `json:"utc"`
		Local string `json:"local"`
	} `json:"datetime"`
	Value      *float64 `json:"value"`
	SensorID   int      `json:"sensorsId"`
	LocationID int      `json:"locationsId"`
}

func (c *LiveConfig) get(r *http.Request, path string, out any) error {
	base := c.BaseURL
	if base == "" {
		base = "https://api.openaq.org/v3"
	}
	req, err := http.NewRequestWithContext(r.Context(), http.MethodGet, base+path, nil)
	if err != nil {
		return err
	}
	req.Header.Set("X-API-Key", c.Key)
	client := c.Client
	if client == nil {
		client = &http.Client{Timeout: 12 * time.Second}
	}
	res, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("station provider unavailable")
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return fmt.Errorf("station provider returned HTTP %d", res.StatusCode)
	}
	if err := json.NewDecoder(io.LimitReader(res.Body, 1<<20)).Decode(out); err != nil {
		return fmt.Errorf("invalid station provider response")
	}
	return nil
}

func (s *Server) live(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	city, ok := requireCity(w, r)
	if !ok {
		return
	}
	c := s.Live
	if c == nil || c.Key == "" {
		writeError(w, 503, "Station readings are not configured. Set OPENAQ_API_KEY and verified OPENAQ_STATIONS on the server.")
		return
	}
	id, ok := c.Stations[city]
	if !ok || id <= 0 {
		writeError(w, 404, "No verified station configured for that city. Coverage is not assumed.")
		return
	}
	// One hour cache, including errors: reloads cannot hammer the provider.
	c.mu.Lock()
	defer c.mu.Unlock()
	if hit, ok := c.cache[city]; ok && time.Now().Before(hit.until) {
		if e, ok := hit.data.(string); ok {
			writeError(w, 502, e)
		} else {
			writeJSON(w, 200, hit.data)
		}
		return
	}
	if c.cache == nil {
		c.cache = make(map[string]liveCache)
	}
	fail := func(err error) {
		c.cache[city] = liveCache{err.Error(), time.Now().Add(time.Hour)}
		writeError(w, 502, err.Error())
	}
	var locs struct {
		Results []aqLocation `json:"results"`
	}
	if err := c.get(r, "/locations/"+strconv.Itoa(id), &locs); err != nil {
		fail(err)
		return
	}
	if len(locs.Results) != 1 || locs.Results[0].ID != id || locs.Results[0].Country.Code != "IN" {
		fail(fmt.Errorf("station metadata did not match the verified Indian location"))
		return
	}
	loc := locs.Results[0]
	if len(loc.Licenses) == 0 {
		fail(fmt.Errorf("station license information missing; readings withheld"))
		return
	}
	// Only the license reviewed for the configured ambient monitors is approved.
	for i, l := range loc.Licenses {
		if l.ID != 33 {
			fail(fmt.Errorf("station license has not been reviewed for this integration"))
			return
		}
		var licenses struct {
			Results []aqLicense `json:"results"`
		}
		if err := c.get(r, "/licenses/"+strconv.Itoa(l.ID), &licenses); err != nil {
			fail(err)
			return
		}
		if len(licenses.Results) != 1 || licenses.Results[0].ID != l.ID || licenses.Results[0].RedistributionAllowed == nil || !*licenses.Results[0].RedistributionAllowed {
			fail(fmt.Errorf("station license does not confirm display/redistribution rights"))
			return
		}
		loc.Licenses[i].SourceURL = licenses.Results[0].SourceURL
		loc.Licenses[i].RedistributionAllowed = licenses.Results[0].RedistributionAllowed
	}

	var latest struct {
		Results []aqLatest `json:"results"`
	}
	if err := c.get(r, "/locations/"+strconv.Itoa(id)+"/latest?limit=100", &latest); err != nil {
		fail(err)
		return
	}
	sensors := map[int]aqParameter{}
	for _, s := range loc.Sensors {
		sensors[s.ID] = s.Parameter
	}
	readings := []map[string]any{}
	now := time.Now().UTC()
	for _, v := range latest.Results {
		p, ok := sensors[v.SensorID]
		if !ok || p.Name != "pm25" || (p.Units != "µg/m³" && p.Units != "μg/m³") || v.LocationID != id || v.Value == nil || *v.Value < 0 {
			continue
		}
		tm, err := time.Parse(time.RFC3339, v.Datetime.UTC)
		if err != nil || tm.After(now.Add(15*time.Minute)) {
			continue
		}
		age := now.Sub(tm).Hours()
		if age < 0 {
			age = 0
		}
		readings = append(readings, map[string]any{"sensor_id": v.SensorID, "pollutant": p.DisplayName, "parameter": p.Name, "unit": p.Units, "value": v.Value, "measured_at": tm.Format(time.RFC3339), "age_hours": age, "stale": age > 3})
	}
	data := map[string]any{"city": city, "kind": "station_observations", "station_id": id, "station_name": loc.Name, "locality": loc.Locality, "coordinates": loc.Coordinates, "provider": loc.Provider, "owner": loc.Owner, "licenses": loc.Licenses, "source": "OpenAQ", "source_url": "https://explore.openaq.org/locations/" + strconv.Itoa(id), "retrieved_at": now.Format(time.RFC3339), "next_refresh_at": now.Add(time.Hour).Format(time.RFC3339), "readings": readings, "note": "One selected station, not a city-wide average. Latest available measurements may be delayed, provisional or stale. Values older than 3 hours are marked stale (project display rule, not an official standard). No AQI is inferred from instantaneous concentrations. Not a validated live forecasting or health-advice service."}
	c.cache[city] = liveCache{data, now.Add(time.Hour)}
	writeJSON(w, 200, data)
}
