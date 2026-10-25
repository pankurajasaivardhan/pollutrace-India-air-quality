package api_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/pankurajasaivardhan/pollutrace-India-air-quality/internal/api"
)

// These test only the Go proxy layer (status mapping, size and type limits, CORS preflight).
// The upstream here is a stub. The real models behind pipeline/serve.py are exercised by
// the end-to-end check described in the README, not by these tests.
func post(t *testing.T, s *api.Server, ct, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, "/api/predict", strings.NewReader(body))
	if ct != "" {
		req.Header.Set("Content-Type", ct)
	}
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, req)
	return rec
}

func TestPredictNotConfigured503(t *testing.T) {
	if r := post(t, &api.Server{}, "application/json", "{}"); r.Code != 503 {
		t.Fatalf("got %d", r.Code)
	}
}

func TestPredictRejectsWrongContentType(t *testing.T) {
	up := httptest.NewServer(http.NotFoundHandler())
	defer up.Close()
	if r := post(t, &api.Server{InferenceURL: up.URL}, "text/plain", "{}"); r.Code != 415 {
		t.Fatalf("got %d", r.Code)
	}
}

func TestPredictRelaysStatusAndBody(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/predict" || r.Method != http.MethodPost {
			t.Errorf("unexpected upstream call %s %s", r.Method, r.URL.Path)
		}
		w.WriteHeader(422)
		w.Write([]byte(`{"error":"need at least 30 calendar days of history, got 10"}`))
	}))
	defer up.Close()
	r := post(t, &api.Server{InferenceURL: up.URL}, "application/json", `{"city":"Delhi","rows":[]}`)
	if r.Code != 422 || !strings.Contains(r.Body.String(), "at least 30") {
		t.Fatalf("got %d %s", r.Code, r.Body.String())
	}
}

func TestPredictUpstreamDown502(t *testing.T) {
	up := httptest.NewServer(http.NotFoundHandler())
	url := up.URL
	up.Close()
	if r := post(t, &api.Server{InferenceURL: url}, "application/json", "{}"); r.Code != 502 {
		t.Fatalf("got %d", r.Code)
	}
}

func TestPredictBodyTooLarge413(t *testing.T) {
	up := httptest.NewServer(http.NotFoundHandler())
	defer up.Close()
	big := `{"x":"` + strings.Repeat("a", 2<<20) + `"}`
	if r := post(t, &api.Server{InferenceURL: up.URL}, "application/json", big); r.Code != 413 {
		t.Fatalf("got %d", r.Code)
	}
}

func TestCORSPreflight(t *testing.T) {
	s := &api.Server{AllowOrigin: "http://localhost:3000"}
	req := httptest.NewRequest(http.MethodOptions, "/api/predict", nil)
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, req)
	if rec.Code != 204 || !strings.Contains(rec.Header().Get("Access-Control-Allow-Methods"), "POST") {
		t.Fatalf("got %d %v", rec.Code, rec.Header())
	}
}
