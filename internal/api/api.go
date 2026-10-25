// Package api implements the PolluTrace HTTP JSON API.
package api

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"

	"github.com/pankurajasaivardhan/pollutrace-india-air-quality/internal/database"
)

// Server serves the read-only PolluTrace API from a database.
type Server struct {
	DB   *database.Queries
	Live *LiveConfig
	// AllowOrigin is sent as Access-Control-Allow-Origin when non-empty.
	AllowOrigin string
	// InferenceURL is the base URL of the Python inference service; empty disables /api/predict.
	InferenceURL string
}

// Handler returns the routed, CORS-aware HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/healthz", s.health)
	mux.HandleFunc("GET /api/live", s.live)
	mux.HandleFunc("GET /api/cities", s.cities)
	mux.HandleFunc("GET /api/pollution", s.pollution)
	mux.HandleFunc("GET /api/anomalies", s.anomalies)
	mux.HandleFunc("GET /api/sources", s.sources)
	mux.HandleFunc("GET /api/metrics", s.metrics)
	mux.HandleFunc("GET /api/predictions", s.predictions)
	mux.HandleFunc("POST /api/predict", s.predict)
	return s.cors(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.DB == nil && r.URL.Path != "/api/live" && r.URL.Path != "/api/healthz" && r.URL.Path != "/api/cities" && r.URL.Path != "/api/predict" && r.Method != http.MethodOptions {
			writeError(w, 503, "Historical database is not configured; station readings are available separately at /api/live.")
			return
		}
		mux.ServeHTTP(w, r)
	}))
}

func (s *Server) cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.AllowOrigin != "" {
			w.Header().Set("Access-Control-Allow-Origin", s.AllowOrigin)
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("encode response: %v", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (s *Server) internal(w http.ResponseWriter, err error) {
	log.Printf("internal error: %v", err)
	writeError(w, http.StatusInternalServerError, "internal server error")
}

func nullCity(r *http.Request) (sql.NullString, bool) {
	c := r.URL.Query().Get("city")
	return sql.NullString{String: c, Valid: c != ""}, c != ""
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("OK"))
}

func (s *Server) cities(w http.ResponseWriter, r *http.Request) {
	if s.DB == nil {
		writeJSON(w, 200, []string{"Delhi", "Mumbai", "Bengaluru", "Hyderabad"})
		return
	}
	rows, err := s.DB.ListCities(r.Context())
	if err != nil {
		s.internal(w, err)
		return
	}
	out := make([]string, 0, len(rows))
	for _, c := range rows {
		out = append(out, c)
	}
	writeJSON(w, http.StatusOK, out)
}

func (s *Server) pollution(w http.ResponseWriter, r *http.Request) {
	city, ok := nullCity(r)
	if !ok {
		writeError(w, http.StatusBadRequest, "query parameter 'city' is required")
		return
	}
	rows, err := s.DB.GetCityPollutionRecord(r.Context(), city)
	if err != nil {
		s.internal(w, err)
		return
	}
	type rec struct {
		City  string   `json:"city"`
		Date  *string  `json:"date"`
		Pm25  *float64 `json:"pm25"`
		Pm10  *float64 `json:"pm10"`
		No2   *float64 `json:"no2"`
		Co    *float64 `json:"co"`
		Nox   *float64 `json:"nox"`
		So2   *float64 `json:"so2"`
		Ozone *float64 `json:"ozone"`
	}
	out := make([]rec, 0, len(rows))
	for _, x := range rows {
		out = append(out, rec{
			City: x.City.String, Date: dateStr(x.Date),
			Pm25: f(x.Pm25), Pm10: f(x.Pm10), No2: f(x.No2), Co: f(x.Co),
			Nox: f(x.Nox), So2: f(x.So2), Ozone: f(x.Ozone),
		})
	}
	writeJSON(w, http.StatusOK, out)
}

func requireCity(w http.ResponseWriter, r *http.Request) (string, bool) {
	c := r.URL.Query().Get("city")
	if c == "" {
		writeError(w, http.StatusBadRequest, "query parameter 'city' is required")
		return "", false
	}
	return c, true
}

func (s *Server) anomalies(w http.ResponseWriter, r *http.Request) {
	city, ok := requireCity(w, r)
	if !ok {
		return
	}
	rows, err := s.DB.GetCityAnomalies(r.Context(), city)
	if err != nil {
		s.internal(w, err)
		return
	}
	type rec struct {
		City      string   `json:"city"`
		Date      string   `json:"date"`
		Pm25      *float64 `json:"pm25"`
		IsAnomaly *bool    `json:"is_anomaly"`
		Severity  *string  `json:"severity"`
	}
	out := make([]rec, 0, len(rows))
	for _, x := range rows {
		var an *bool
		if x.IsAnomaly.Valid {
			v := x.IsAnomaly.Bool
			an = &v
		}
		var sev *string
		if x.Severity.Valid {
			v := x.Severity.String
			sev = &v
		}
		out = append(out, rec{City: x.City, Date: x.Date.Format("2006-01-02"), Pm25: f(x.Pm25), IsAnomaly: an, Severity: sev})
	}
	writeJSON(w, http.StatusOK, out)
}

// sources returns the pollutants most associated with PM2.5 for a city.
// This is a statistical association, not source apportionment.
func (s *Server) sources(w http.ResponseWriter, r *http.Request) {
	city, ok := requireCity(w, r)
	if !ok {
		return
	}
	rows, err := s.DB.GetSourceAnalysis(r.Context(), city)
	if err != nil {
		s.internal(w, err)
		return
	}
	if len(rows) == 0 {
		writeError(w, http.StatusNotFound, "no pollutant association results for that city")
		return
	}
	type item struct {
		Rank        int      `json:"rank"`
		Pollutant   string   `json:"pollutant"`
		MeanAbsShap *float64 `json:"mean_abs_shap"`
	}
	items := make([]item, 0, len(rows))
	for _, x := range rows {
		items = append(items, item{int(x.Rank), x.Pollutant, f(x.MeanAbsShap)})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"city": city, "model_test_r2": f(rows[0].ModelTestR2), "ranking": items,
		"note": "statistical association with PM2.5 in a predictive model; not causal and not source apportionment",
	})
}

func (s *Server) metrics(w http.ResponseWriter, r *http.Request) {
	rows, err := s.DB.GetModelMetrics(r.Context())
	if err != nil {
		s.internal(w, err)
		return
	}
	type rec struct {
		City      string   `json:"city"`
		ModelType string   `json:"model_type"`
		Rmse      *float64 `json:"rmse"`
		Mae       *float64 `json:"mae"`
		R2Score   *float64 `json:"r2_score"`
		NTestDays *int32   `json:"n_test_days"`
	}
	out := make([]rec, 0, len(rows))
	for _, x := range rows {
		var n *int32
		if x.NTestDays.Valid {
			v := x.NTestDays.Int32
			n = &v
		}
		out = append(out, rec{x.City, x.ModelType, f(x.Rmse), f(x.Mae), f(x.R2Score), n})
	}
	writeJSON(w, http.StatusOK, out)
}

// predictions returns held-out test-period next-day forecasts against actuals.
func (s *Server) predictions(w http.ResponseWriter, r *http.Request) {
	city, ok := requireCity(w, r)
	if !ok {
		return
	}
	rows, err := s.DB.GetCityPredictions(r.Context(), city)
	if err != nil {
		s.internal(w, err)
		return
	}
	type rec struct {
		Date                string   `json:"date"`
		Actual              *float64 `json:"actual_pm25"`
		PredictedLSTM       *float64 `json:"predicted_pm25_lstm"`
		PredictedPersistent *float64 `json:"predicted_pm25_persistence"`
		PredictedXGBoost    *float64 `json:"predicted_pm25_xgboost"`
	}
	out := make([]rec, 0, len(rows))
	for _, x := range rows {
		out = append(out, rec{x.Date.Format("2006-01-02"), f(x.ActualPm25), f(x.PredictedPm25Lstm), f(x.PredictedPm25Persistence), f(x.PredictedPm25Xgboost)})
	}
	writeJSON(w, http.StatusOK, out)
}

func f(n sql.NullFloat64) *float64 {
	if !n.Valid {
		return nil
	}
	v := n.Float64
	return &v
}

func dateStr(t sql.NullTime) *string {
	if !t.Valid {
		return nil
	}
	s := t.Time.Format("2006-01-02")
	return &s
}
