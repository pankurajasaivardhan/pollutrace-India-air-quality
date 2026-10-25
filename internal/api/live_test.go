package api_test

import (
	"encoding/json"
	"github.com/pankurajasaivardhan/pollutrace-India-air-quality/internal/api"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func liveGet(s *api.Server, path string) *httptest.ResponseRecorder {
	r := httptest.NewRecorder()
	s.Handler().ServeHTTP(r, httptest.NewRequest("GET", path, nil))
	return r
}
func TestLiveNotConfigured(t *testing.T) {
	if r := liveGet(&api.Server{}, "/api/live?city=Delhi"); r.Code != 503 {
		t.Fatal(r.Code)
	}
}
func TestLiveNoCity(t *testing.T) {
	if r := liveGet(&api.Server{}, "/api/live"); r.Code != 400 {
		t.Fatal(r.Code)
	}
}
func TestLiveUnverifiedCity(t *testing.T) {
	if r := liveGet(&api.Server{Live: &api.LiveConfig{Key: "test"}}, "/api/live?city=Delhi"); r.Code != 404 {
		t.Fatal(r.Code)
	}
}
func TestLiveHistoricalUnavailable(t *testing.T) {
	if r := liveGet(&api.Server{}, "/api/metrics"); r.Code != 503 {
		t.Fatal(r.Code)
	}
}
func TestLiveNoDBCityList(t *testing.T) {
	if r := liveGet(&api.Server{}, "/api/cities"); r.Code != 200 {
		t.Fatal(r.Code)
	}
}
func stationStub(t *testing.T, mode string) (*api.Server, *int) {
	calls := new(int)
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		*calls++
		if r.Header.Get("X-API-Key") != "test-secret" {
			t.Error("missing key")
		}
		if mode == "down" {
			w.WriteHeader(429)
			return
		}
		if mode == "malformed" {
			w.Write([]byte("not json"))
			return
		}
		if r.URL.Path == "/licenses/33" {
			w.Write([]byte(`{"results":[{"id":33,"name":"US Public Domain","redistributionAllowed":true,"sourceUrl":"http://www.usa.gov/publicdomain/label/1.0/"}]}`))
			return
		}
		if r.URL.Path == "/locations/123" {
			license := `[{"id":33,"name":"US Public Domain"}]`
			if mode == "unlicensed" {
				license = `[]`
			}
			w.Write([]byte(`{"results":[{"id":123,"name":"Test station","country":{"code":"IN"},"sensors":[{"id":10,"parameter":{"name":"pm25","displayName":"PM2.5","units":"µg/m³"}}],"licenses":` + license + `}]}`))
			return
		}
		tm := time.Now().Add(-30 * time.Minute)
		if mode == "stale" {
			tm = time.Now().Add(-24 * time.Hour)
		}
		if mode == "future" {
			tm = time.Now().Add(24 * time.Hour)
		}
		value := "12.5"
		if mode == "null" {
			value = "null"
		}
		if mode == "negative" {
			value = "-1"
		}
		w.Write([]byte(`{"results":[{"datetime":{"utc":"` + tm.UTC().Format(time.RFC3339) + `"},"value":` + value + `,"sensorsId":10,"locationsId":123}]}`))
	}))
	t.Cleanup(up.Close)
	return &api.Server{Live: &api.LiveConfig{Key: "test-secret", Stations: map[string]int{"Delhi": 123}, BaseURL: up.URL}}, calls
}
func TestLiveSuccessCacheNoKeyLeak(t *testing.T) {
	s, c := stationStub(t, "")
	for i := 0; i < 2; i++ {
		r := liveGet(s, "/api/live?city=Delhi")
		if r.Code != 200 || strings.Contains(r.Body.String(), "test-secret") || !strings.Contains(r.Body.String(), "station_observations") {
			t.Fatal(r.Code, r.Body.String())
		}
	}
	if *c != 3 {
		t.Fatalf("calls %d", *c)
	}
}
func TestLiveStaleFlag(t *testing.T) {
	s, _ := stationStub(t, "stale")
	r := liveGet(s, "/api/live?city=Delhi")
	if !strings.Contains(r.Body.String(), `"stale":true`) {
		t.Fatal(r.Body.String())
	}
}
func TestLiveInvalidValuesOmitted(t *testing.T) {
	for _, mode := range []string{"null", "negative", "future"} {
		t.Run(mode, func(t *testing.T) {
			s, _ := stationStub(t, mode)
			r := liveGet(s, "/api/live?city=Delhi")
			var v struct {
				Readings []any `json:"readings"`
			}
			json.Unmarshal(r.Body.Bytes(), &v)
			if r.Code != 200 || len(v.Readings) != 0 {
				t.Fatal(r.Code, r.Body.String())
			}
		})
	}
}
func TestLiveProviderErrorsCached(t *testing.T) {
	for _, mode := range []string{"down", "malformed", "unlicensed"} {
		t.Run(mode, func(t *testing.T) {
			s, c := stationStub(t, mode)
			for i := 0; i < 2; i++ {
				r := liveGet(s, "/api/live?city=Delhi")
				if r.Code != 502 {
					t.Fatal(r.Code)
				}
			}
			if *c != 1 {
				t.Fatal(*c)
			}
		})
	}
}
