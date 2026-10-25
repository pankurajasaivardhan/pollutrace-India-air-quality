package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"os"

	"github.com/joho/godotenv"
	_ "github.com/lib/pq"

	"github.com/pankurajasaivardhan/pollutrace-India-air-quality/internal/api"
	"github.com/pankurajasaivardhan/pollutrace-India-air-quality/internal/database"
)

func main() {
	_ = godotenv.Load()

	var queries *database.Queries
	if os.Getenv("LIVE_ONLY") != "true" {
		dbURL := os.Getenv("DB_URL")
		if dbURL == "" {
			log.Fatal("DB_URL is not set; use LIVE_ONLY=true for station readings without a database")
		}
		db, err := sql.Open("postgres", dbURL)
		if err != nil {
			log.Fatal(err)
		}
		if err = db.Ping(); err != nil {
			log.Fatal(err)
		}
		queries = database.New(db)
	}
	stations := map[string]int{"Delhi": 8118, "Mumbai": 8039}
	if raw := os.Getenv("OPENAQ_STATIONS"); raw != "" {
		if err := json.Unmarshal([]byte(raw), &stations); err != nil {
			log.Fatal("invalid OPENAQ_STATIONS JSON")
		}
	}

	addr := os.Getenv("PORT")
	if addr == "" {
		addr = "8080"
	}
	srv := &api.Server{DB: queries, Live: &api.LiveConfig{Key: os.Getenv("OPENAQ_API_KEY"), Stations: stations}, AllowOrigin: os.Getenv("CORS_ALLOW_ORIGIN"), InferenceURL: os.Getenv("INFERENCE_URL")}
	log.Printf("PolluTrace API listening on :%s", addr)
	log.Fatal(http.ListenAndServe(":"+addr, srv.Handler()))
}
