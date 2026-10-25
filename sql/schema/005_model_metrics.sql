-- +goose Up
-- Held-out TEST-period metrics for each forecaster, including the persistence baseline.
CREATE TABLE model_metrics (
    id          SERIAL PRIMARY KEY,
    city        VARCHAR(50) NOT NULL,
    model_type  VARCHAR(50) NOT NULL,
    rmse        FLOAT,
    mae         FLOAT,
    r2_score    FLOAT,
    n_test_days INT
);

-- +goose Down
DROP TABLE model_metrics;
