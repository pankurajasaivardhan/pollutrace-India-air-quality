-- name: GetCityPredictions :many
SELECT city, date, actual_pm25, predicted_pm25_lstm, predicted_pm25_persistence, predicted_pm25_xgboost
FROM lstm_predictions WHERE city = $1 ORDER BY date;
