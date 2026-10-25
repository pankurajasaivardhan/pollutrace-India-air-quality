-- +goose Up
-- Held-out TEST-period next-day PM2.5 predictions, produced by pipeline/run_all.py.
CREATE TABLE lstm_predictions (
    id                    SERIAL PRIMARY KEY,
    city                  VARCHAR(50) NOT NULL,
    date                  DATE NOT NULL,
    actual_pm25           FLOAT,
    predicted_pm25_lstm   FLOAT,
    predicted_pm25_persistence FLOAT,
    predicted_pm25_xgboost     FLOAT
);

-- +goose Down
DROP TABLE lstm_predictions;
