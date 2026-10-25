-- +goose Up
-- Autoencoder flags on the held-out test period (unsupervised, no ground-truth labels).
CREATE TABLE anomalies (
    id                   SERIAL PRIMARY KEY,
    city                 VARCHAR(50) NOT NULL,
    date                 DATE NOT NULL,
    pm25                 FLOAT,
    reconstruction_error FLOAT,
    threshold            FLOAT,
    is_anomaly           BOOLEAN,
    severity             VARCHAR(20)
);

-- +goose Down
DROP TABLE anomalies;
