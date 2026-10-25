package api_test

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	_ "github.com/lib/pq"

	"github.com/pankurajasaivardhan/pollutrace-india-air-quality/internal/api"
	"github.com/pankurajasaivardhan/pollutrace-india-air-quality/internal/database"
)

// These are integration tests against a REAL PostgreSQL server.
// Set TEST_DB_URL to run them; they are skipped otherwise.
// They create and drop tables in the target database.
func setup(t *testing.T) *httptest.Server {
	t.Helper()
	url := os.Getenv("TEST_DB_URL")
	if url == "" {
		t.Skip("TEST_DB_URL not set; skipping real-database tests")
	}
	db, err := sql.Open("postgres", url)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })

	files, _ := filepath.Glob("../../sql/schema/*.sql")
	sort.Strings(files)
	for _, f := range files {
		b, _ := os.ReadFile(f)
		up := strings.SplitN(string(b), "-- +goose Down", 2)[0]
		if _, err := db.Exec(up); err != nil {
			t.Fatalf("apply %s: %v", f, err)
		}
	}
	t.Cleanup(func() {
		for _, tb := range []string{"city_pollution", "lstm_predictions", "source_analysis", "anomalies", "model_metrics"} {
			db.Exec("DROP TABLE IF EXISTS " + tb)
		}
	})
	seed := []string{
		`INSERT INTO city_pollution(city,date,pm25,pm10,no2,co) VALUES ('Delhi','2020-01-02',150.5,200,40,1.2),('Delhi','2020-01-01',120,NULL,35,1.0),('Mumbai','2020-01-01',60,90,20,0.8)`,
		`INSERT INTO anomalies(city,date,pm25,is_anomaly,severity) VALUES ('Delhi','2020-01-01',300,true,'high')`,
		`INSERT INTO source_analysis(city,rank,pollutant,mean_abs_shap,model_test_r2) VALUES ('Delhi',2,'CO',1.5,0.8),('Delhi',1,'PM10',9.0,0.8)`,
		`INSERT INTO model_metrics(city,model_type,rmse,mae,r2_score,n_test_days) VALUES ('Delhi','lstm',10,7,0.5,100),('Delhi','persistence',9,6,0.6,100)`,
		`INSERT INTO lstm_predictions(city,date,actual_pm25,predicted_pm25_lstm,predicted_pm25_persistence,predicted_pm25_xgboost) VALUES ('Delhi','2022-01-02',100,90,NULL,NULL),('Delhi','2022-01-01',80,85,70,75)`,
	}
	for _, q := range seed {
		if _, err := db.Exec(q); err != nil {
			t.Fatalf("seed: %v", err)
		}
	}
	srv := httptest.NewServer((&api.Server{DB: database.New(db)}).Handler())
	t.Cleanup(srv.Close)
	return srv
}

func get(t *testing.T, url string, out any) int {
	t.Helper()
	res, err := http.Get(url)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	if out != nil {
		if err := json.NewDecoder(res.Body).Decode(out); err != nil {
			t.Fatalf("decode: %v", err)
		}
	}
	return res.StatusCode
}

func TestPollutionFiltersByCityAndOrders(t *testing.T) {
	srv := setup(t)
	var rows []map[string]any
	if c := get(t, srv.URL+"/api/pollution?city=Delhi", &rows); c != 200 {
		t.Fatalf("status %d", c)
	}
	if len(rows) != 2 || rows[0]["date"] != "2020-01-01" || rows[0]["pm10"] != nil {
		t.Fatalf("unexpected rows: %v", rows)
	}
	if rows[1]["pm25"].(float64) != 150.5 {
		t.Fatalf("unexpected pm25: %v", rows[1])
	}
}

func TestUnknownCityIsEmptyList(t *testing.T) {
	srv := setup(t)
	var rows []any
	if c := get(t, srv.URL+"/api/pollution?city=Nowhere", &rows); c != 200 || len(rows) != 0 {
		t.Fatalf("status %d rows %v", c, rows)
	}
}

func TestMissingCityIs400(t *testing.T) {
	srv := setup(t)
	for _, p := range []string{"pollution", "anomalies", "sources"} {
		if c := get(t, srv.URL+"/api/"+p, nil); c != 400 {
			t.Errorf("%s: status %d, want 400", p, c)
		}
	}
}

func TestSourcesAnd404(t *testing.T) {
	srv := setup(t)
	var m map[string]any
	if c := get(t, srv.URL+"/api/sources?city=Delhi", &m); c != 200 {
		t.Fatalf("status %d body %v", c, m)
	}
	rk := m["ranking"].([]any)
	if len(rk) != 2 || rk[0].(map[string]any)["pollutant"] != "PM10" {
		t.Fatalf("ranking not ordered by rank: %v", rk)
	}
	if c := get(t, srv.URL+"/api/sources?city=Mumbai", nil); c != 404 {
		t.Fatalf("status %d, want 404", c)
	}
}

func TestAnomaliesMetricsCities(t *testing.T) {
	srv := setup(t)
	var an []map[string]any
	if c := get(t, srv.URL+"/api/anomalies?city=Delhi", &an); c != 200 || len(an) != 1 || an[0]["severity"] != "high" {
		t.Fatalf("anomalies: %d %v", c, an)
	}
	var mt []map[string]any
	if c := get(t, srv.URL+"/api/metrics", &mt); c != 200 || len(mt) != 2 || mt[0]["model_type"] != "lstm" || mt[0]["n_test_days"].(float64) != 100 {
		t.Fatalf("metrics: %d %v", c, mt)
	}
	var cs []string
	if c := get(t, srv.URL+"/api/cities", &cs); c != 200 || len(cs) != 2 || cs[0] != "Delhi" {
		t.Fatalf("cities: %d %v", c, cs)
	}
}

func TestPredictionsOrderedWithNulls(t *testing.T) {
	srv := setup(t)
	var p []map[string]any
	if c := get(t, srv.URL+"/api/predictions?city=Delhi", &p); c != 200 || len(p) != 2 {
		t.Fatalf("predictions: %d %v", c, p)
	}
	if p[0]["date"] != "2022-01-01" || p[1]["predicted_pm25_persistence"] != nil || p[0]["predicted_pm25_xgboost"] != 75.0 || p[1]["predicted_pm25_xgboost"] != nil {
		t.Fatalf("unexpected: %v", p)
	}
}

func TestHealth(t *testing.T) {
	srv := setup(t)
	if c := get(t, srv.URL+"/api/healthz", nil); c != 200 {
		t.Fatalf("status %d", c)
	}
}
