-- name: GetCityAnomalies :many
SELECT city, date, pm25, is_anomaly, severity FROM anomalies
WHERE city = $1
ORDER BY date;
