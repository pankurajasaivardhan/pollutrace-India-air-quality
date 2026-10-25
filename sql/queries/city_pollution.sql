-- name: GetCityPollutionRecord :many
SELECT city, date, pm25, pm10, no2, nox, so2, co, ozone FROM city_pollution
WHERE city = $1
ORDER BY date;

-- name: ListCities :many
SELECT city::text AS city FROM (
    SELECT city FROM city_pollution
    UNION SELECT city FROM model_metrics
) c WHERE city IS NOT NULL ORDER BY city;
