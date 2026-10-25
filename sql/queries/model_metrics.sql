-- name: GetModelMetrics :many
SELECT city, model_type, rmse, mae, r2_score, n_test_days FROM model_metrics ORDER BY city, model_type;
