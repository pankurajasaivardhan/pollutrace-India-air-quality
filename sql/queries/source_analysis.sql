-- name: GetSourceAnalysis :many
SELECT city, rank, pollutant, mean_abs_shap, model_test_r2
FROM source_analysis WHERE city = $1 ORDER BY rank;
