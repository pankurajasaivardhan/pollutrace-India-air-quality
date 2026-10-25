-- +goose Up
-- Pollutant association with PM2.5 (XGBoost + TreeSHAP). NOT source apportionment.
CREATE TABLE source_analysis (
    id               SERIAL PRIMARY KEY,
    city             VARCHAR(50) NOT NULL,
    rank             INT NOT NULL,
    pollutant        VARCHAR(20) NOT NULL,
    mean_abs_shap    FLOAT,
    model_test_r2    FLOAT
);

-- +goose Down
DROP TABLE source_analysis;
