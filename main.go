package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"

	"github.com/joho/godotenv"
	_ "github.com/lib/pq"

	"github.com/pankurajasaivardhan/pollutrace-india-air-quality/internal/api"
	"github.com/pankurajasaivardhan/pollutrace-india-air-quality/internal/database"
)

func main() {
	_ = godotenv.Load()

	dbURL := os.Getenv("DB_URL")
	if dbURL == "" {
		log.Fatal("DB_URL is not set (see .env.example)")
	}
	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	if err := db.Ping(); err != nil {
		log.Fatalf("connect to database: %v", err)
	}

	addr := os.Getenv("PORT")
	if addr == "" {
		addr = "8080"
	}
	srv := &api.Server{DB: database.New(db), AllowOrigin: os.Getenv("CORS_ALLOW_ORIGIN"), InferenceURL: os.Getenv("INFERENCE_URL")}
	log.Printf("PolluTrace API listening on :%s", addr)
	log.Fatal(http.ListenAndServe(":"+addr, srv.Handler()))
}
