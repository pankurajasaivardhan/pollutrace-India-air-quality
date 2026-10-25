# PolluTrace AI
### Urban Air Pollution Source Analysis and Prediction System


## Project Overview

PolluTrace AI is an end-to-end AI system that analyses urban air pollution in Indian cities. It goes beyond traditional monitoring by:

- Predicting future PM2.5 pollution levels using LSTM deep learning
- Identifying dominant pollution sources using XGBoost and Random Forest
- Detecting unusual pollution spikes using Autoencoder anomaly detection
- Explaining predictions with confidence scores using SHAP
- Visualizing all results through an interactive React/Next.js dashboard

**Cities Covered:** Delhi, Bengaluru, Mumbai, Hyderabad  
**Data:** 6 million+ hourly records from 87 stations (2010–2023)

---

## Project Structure

```
PolluTrace-AI/
│
├── data/
│   ├── raw/                          # Raw CSV files from Kaggle (not pushed - too large)
│   └── processed/
│       ├── four_cities_raw.csv
│       ├── station_daily_clean.csv
│       └── city_daily_clean.csv
│
├── notebooks/
│   ├── 01_EDA.ipynb
│   ├── 02_Preprocessing.ipynb
│   ├── 03_LSTM_Model.ipynb
│   ├── 04_XGBoost_Source_Analysis.ipynb
│   ├── 05_Autoencoder_Anomaly.ipynb
│   ├── 06_Explainable_AI.ipynb
│   ├── 07_Database_Setup.ipynb
│   └── 08_Final_Metrics_Report.ipynb
│
├── src/
│   └── models/                       # All saved AI models (16 files)
│       ├── lstm_delhi.keras
│       ├── lstm_bengaluru.keras
│       ├── lstm_mumbai.keras
│       ├── lstm_hyderabad.keras
│       ├── xgboost_source.json
│       ├── random_forest_source.pkl
│       ├── autoencoder_delhi.keras
│       ├── autoencoder_bengaluru.keras
│       ├── autoencoder_mumbai.keras
│       ├── autoencoder_hyderabad.keras
│       ├── scalers.pkl
│       ├── anomaly_scalers.pkl
│       ├── shap_explainer.pkl
│       ├── confidence_results.pkl
│       ├── city_importances.pkl
│       └── top_anomalies.pkl
│
├── backend/                          # Go REST API
│   ├── main.go
│   ├── internal/
│   │   └── database/
│   │       └── db.go
│   └── handlers/
│
├── frontend/                         # Next.js Dashboard
│   ├── app/
│   │   ├── page.tsx                  # Dashboard
│   │   ├── predictions/page.tsx
│   │   ├── sources/page.tsx
│   │   ├── anomalies/page.tsx
│   │   ├── metrics/page.tsx
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── Navigation.tsx
│   │   ├── AQICard.tsx
│   │   ├── PM25TrendChart.tsx
│   │   ├── PredictionChart.tsx
│   │   ├── SourceAnalysis.tsx
│   │   ├── AnomalyAnalysis.tsx
│   │   └── MetricsDashboard.tsx
│   └── lib/
│       ├── mockData.ts
│       └── utils/
│           └── aqiCalculations.ts
│
└── requirements.txt
```

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15
- Node.js 18+ and pnpm
- Go 1.21+
- macOS or Linux

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PolluTrace-AI.git
cd PolluTrace-AI
```

### 2. Python Environment Setup

```bash
python3.11 -m venv pollutrace-env
source pollutrace-env/bin/activate
pip install pandas numpy matplotlib seaborn scikit-learn xgboost tensorflow jupyter ipykernel shap psycopg2-binary sqlalchemy
```

### 3. Download Dataset

Download from Kaggle and place CSV files in `data/raw/`:  
https://www.kaggle.com/datasets/abhisheksjha/time-series-air-quality-data-of-india-2010-2023

### 4. Set Up PostgreSQL Database

```bash
psql postgres
CREATE DATABASE pollutrace_db;
\q
```

### 5. Run Notebooks in Order

```
01_EDA.ipynb
02_Preprocessing.ipynb
03_LSTM_Model.ipynb
04_XGBoost_Source_Analysis.ipynb
05_Autoencoder_Anomaly.ipynb
06_Explainable_AI.ipynb
07_Database_Setup.ipynb
08_Final_Metrics_Report.ipynb
```

### 6. Run the Go Backend

```bash
cd backend
go mod tidy
go run main.go
# Server starts at http://localhost:8080
```

### 7. Run the Frontend

```bash
cd frontend
pnpm install
pnpm dev
# Open http://localhost:3000
```

---

## Model Results

### LSTM — Pollution Prediction

| City | RMSE | MAE | R² Score | Accuracy |
|------|------|-----|----------|----------|
| Delhi | 33.42 | 21.53 | 0.805 | 81.75% |
| Bengaluru | 6.15 | 4.74 | 0.742 | 85.18% |
| Mumbai | 7.66 | 5.57 | 0.877 | 87.55% |
| Hyderabad | 9.03 | 6.87 | 0.809 | 83.67% |

### XGBoost — Source Analysis

| Metric | Score |
|--------|-------|
| R² Score | 0.9367 |
| Accuracy | 88.44% |
| Within 20% | 83.97% |

### Autoencoder — Anomaly Detection

| City | F1 Score | Detection Rate | Anomalies Found |
|------|----------|----------------|-----------------|
| Delhi | 0.237 | 28.51% | 210 |
| Bengaluru | 0.082 | 12.40% | 270 |
| Mumbai | 0.288 | 50.41% | 316 |
| Hyderabad | 0.318 | 30.66% | 123 |

### SHAP — Model Confidence

| City | Confidence |
|------|------------|
| Delhi | 54.6% |
| Bengaluru | 73.8% |
| Mumbai | 80.3% |
| Hyderabad | 69.4% |

---

## Key Findings

- **PM10** is the top global pollution driver (SHAP: 22.11) — dust, construction, roads
- **CO** is second (SHAP: 10.04) — vehicle combustion and open burning
- **NH3** is third (SHAP: 6.28) — agriculture and waste burning
- Delhi PM2.5 peaks at 800+ µg/m³ in winter — 26× WHO safe limit
- Mumbai has the most predictable pollution patterns (confidence: 80.3%)

---

## API Endpoints (Go Backend)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pollution?city=Delhi` | GET | Daily pollution data for city |
| `/api/predict?city=Delhi` | GET | LSTM predicted vs actual PM2.5 |
| `/api/anomalies?city=Delhi` | GET | Detected anomaly events |
| `/api/sources?city=Delhi` | GET | Pollution source importance |
| `/api/metrics` | GET | Model performance metrics for all cities |

---

## Frontend — Dashboard Features

### 5 Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Real-time AQI overview for all 4 cities with PM2.5 trend chart |
| **Predictions** | LSTM forecast dual line chart (actual vs predicted) with health advice |
| **Source Analysis** | XGBoost feature importance bar charts and SHAP confidence scores |
| **Anomaly Detection** | Timeline chart and anomaly events table with severity indicators |
| **Model Metrics** | Technical performance benchmarks across all models and cities |

### Tech Stack

| Technology | Purpose |
|------------|---------|
| Next.js 15 | React framework with App Router |
| React 19 | UI component library |
| TypeScript | Type safety |
| Tailwind CSS | Styling and responsive design |
| Recharts | Interactive charts and visualizations |
| Lucide Icons | UI icons |

### AQI Color Scale

```
0–50:    🟢 Good         (#00B050)
51–100:  🟢 Satisfactory (#92D050)
101–200: 🟡 Moderate     (#FFFF00)
201–300: 🟠 Poor         (#FF6600)
301–400: 🔴 Very Poor    (#FF0000)
401+:    🟣 Severe       (#7030A0)
```

### Switching to Real API

1. Update `apiService` methods in `frontend/lib/mockData.ts`
2. Set environment variable:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```
3. Ensure CORS is enabled on the Go backend

---

## Database Schema (PostgreSQL)

```sql
city_pollution     (id, city, date, pm25, pm10, no, no2, nox, nh3, so2, co, ozone, benzene, month, season, day_of_week, year)
lstm_predictions   (id, city, date, predicted_pm25, actual_pm25, rmse, mae, r2_score, created_at)
source_analysis    (id, city, top_source_1, top_source_2, top_source_3, pm10_importance, co_importance, nh3_importance, confidence, created_at)
anomalies          (id, city, date, pm25, reconstruction_error, threshold, is_anomaly, severity, created_at)
model_metrics      (id, city, model_type, rmse, mae, r2_score, confidence, trained_at)
```

---

## Full Technology Stack

| Layer | Technology |
|-------|------------|
| Data Processing | Python, Pandas, NumPy |
| Prediction | TensorFlow, Keras (LSTM) |
| Source Analysis | XGBoost, Scikit-learn |
| Anomaly Detection | Keras Autoencoder |
| Explainability | SHAP |
| Database | PostgreSQL 15 |
| Backend | Go (Golang), pgx, REST API |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts |

---

## Project Status

| Component | Status |
|-----------|--------|
| Data Collection and EDA | ✅ Completed |
| Data Preprocessing | ✅ Completed |
| LSTM Prediction Model | ✅ Completed |
| XGBoost Source Analysis | ✅ Completed |
| Autoencoder Anomaly Detection | ✅ Completed |
| Explainable AI (SHAP) | ✅ Completed |
| PostgreSQL Database | ✅ Completed |
| Go Backend REST API | ✅ Completed |
| Frontend Dashboard | ✅ Completed |

---

## Deployment

### Frontend (Vercel)

```bash
git push origin main
# Deploy via Vercel dashboard or CLI: vercel deploy
```

Set production environment variable:
```env
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

---

## Ethical Considerations

| Dimension | How Addressed |
|-----------|---------------|
| Data Privacy | Only aggregated city/station-level data used. No personal data collected. |
| Transparency | SHAP values make all AI decisions fully explainable |
| Geographic Fairness | Four cities with diverse geographies, climates, and pollution types |
| Data Credibility | All data from official CPCB government monitoring stations |
| Model Uncertainty | MAPE and Within-20% metrics reported alongside R² |



**Built with ❤️ for clean air in Indian cities**
