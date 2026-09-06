# Pearls AQI Predictor

An end-to-end air quality forecasting platform that predicts Air Quality Index (AQI) for the next three days using machine learning.

## Overview

Pearls AQI Predictor collects pollutant and weather observations from external APIs, transforms them into time-series features, trains multiple forecasting models, and exposes predictions through an interactive web dashboard.

**Key Features:**
- 🌍 Real-time AQI data collection from AQICN and OpenWeather
- 🤖 Multiple ML models (Ridge, Random Forest, TensorFlow LSTM)
- 📊 Interactive Streamlit dashboard with 3-day forecasts
- 🔍 Model explainability with SHAP
- ⚠️ Hazardous AQI alerts
- 🎯 Demo mode for testing without API keys

## Architecture

```
Data Sources → Data Ingestion → Feature Engineering → Feature Store
                                                          ↓
Dashboard ← Prediction Service ← Model Registry ← Model Training
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/munawar123421/Pearl-AQI-Predictor.git
cd Pearl-AQI-Predictor

# Start with Docker Compose
docker-compose up

# Access:
# API: http://localhost:8000
# Dashboard: http://localhost:8501
```

### Option 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/munawar123421/Pearl-AQI-Predictor.git
cd Pearl-AQI-Predictor

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configuration
copy .env.example .env
# Edit .env with your settings (optional for demo mode)
```

### 3. Run Demo Mode

```bash
# Run complete demo workflow (Windows)
scripts\run_demo.bat

# Or run individual steps:

# 1. Generate demo data
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01

# 2. Train models
python scripts/train.py --demo

# 3. Generate forecast
python scripts/predict.py --city karachi --demo

# 4. Start services
# Terminal 1 - API
python -m uvicorn src.pearls_aqi.api.app:app --reload

# Terminal 2 - Dashboard
streamlit run dashboard/streamlit_app.py
```

### 4. Run with Real APIs

1. **Get API Keys:**
   - AQICN: https://aqicn.org/data-platform/token/
   - OpenWeather: https://openweathermap.org/api

2. **Configure .env:**
   ```bash
   DEMO_MODE=false
   DATA_PROVIDER=aqicn
   AQICN_TOKEN=your_token_here
   AQICN_STATION=@A113155
   ```

3. **Run pipelines:**
   ```bash
   python scripts/fetch_current.py
   python scripts/backfill.py --city Karachi --start 2024-01-01 --end 2025-01-01
   python scripts/train.py
   ```

## Commands

```bash
# Testing
pytest -q                           # Quick test run
pytest -v                           # Verbose test run
pytest tests/unit                   # Unit tests only
pytest tests/integration            # Integration tests only

# Data Pipeline
python scripts/fetch_current.py --demo
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01

# Model Training
python scripts/train.py --demo

# Prediction
python scripts/predict.py --city Karachi --demo

# Services
uvicorn src.pearls_aqi.api.app:app --reload  # FastAPI
streamlit run dashboard/streamlit_app.py      # Dashboard
```

## Testing

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/data_contract/
pytest tests/smoke/

# Run with coverage
pytest --cov=src/pearls_aqi --cov-report=html
```

## Project Structure

```
pearls-aqi-predictor/
├── src/pearls_aqi/       # Main source code
│   ├── providers/        # Data provider adapters
│   ├── ingestion/        # Data ingestion
│   ├── features/         # Feature engineering
│   ├── modeling/         # ML models and training
│   ├── api/              # FastAPI application
│   └── pipeline/         # Automated workflows
├── dashboard/            # Streamlit dashboard
├── tests/                # Test suite
├── configs/              # Configuration files
├── data/                 # Data storage
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## Demo Mode

Demo mode allows you to run the entire system without external API keys. It generates synthetic but realistic data for testing and evaluation.

**Features:**
- Deterministic data generation
- Complete pipeline testing
- Model training and evaluation
- Dashboard and API functionality

## Real API Setup

### AQICN Setup

1. Register at https://aqicn.org/data-platform/token/
2. Get your API token
3. Find your station ID from https://aqicn.org/
4. Add to `.env`:
   ```
   AQICN_TOKEN=your_token_here
   AQICN_STATION=your_station_id
   ```

### OpenWeather Setup

1. Register at https://openweathermap.org/api
2. Get your API key
3. Add to `.env`:
   ```
   OPENWEATHER_API_KEY=your_key_here
   OPENWEATHER_LATITUDE=28.6139
   OPENWEATHER_LONGITUDE=77.2090
   ```

## Automation

### GitHub Actions

Automated workflows run on schedule:
- **Hourly Features**: Fetches current data and updates feature store
- **Daily Training**: Retrains models with latest data
- **Tests**: Runs on all pull requests

### Apache Airflow (Optional)

```bash
# Start Airflow with Docker Compose
docker-compose up -d

# Access UI at http://localhost:8080
```

## API Endpoints

FastAPI server provides REST endpoints:

- `GET /health` - Service health check
- `GET /api/v1/locations` - Configured locations
- `GET /api/v1/current?location_id=karachi` - Current observations
- `GET /api/v1/forecast?location_id=karachi` - 3-day forecast
- `GET /api/v1/features?location_id=karachi` - Recent features
- `GET /api/v1/model` - Model metadata
- `GET /api/v1/explanation?location_id=karachi` - Feature importance

API documentation: http://localhost:8000/docs

## Dashboard Features

The Streamlit dashboard provides:

1. **Location Selection** - Choose city and view status
2. **Current Air Quality** - Real-time AQI and pollutants
3. **3-Day Forecast** - Predictions with uncertainty
4. **Historical Trends** - Interactive time series charts
5. **Alerts** - Warnings for hazardous conditions
6. **Explanations** - SHAP feature importance
7. **Model Performance** - Metrics and comparison
8. **Data Quality** - Freshness and completeness

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow

## Configuration

Key environment variables:

```
APP_ENV=development
DEMO_MODE=true
LOG_LEVEL=INFO
DEFAULT_CITY=Karachi
FORECAST_HORIZON_DAYS=3
POLLUTION_ALERT_AQI=150
HAZARDOUS_AQI=300
```

See `.env.example` for complete list.

## Limitations

- Forecasts are estimates, not medical or legal advice
- Model accuracy depends on data quality and quantity
- Historical data coverage may be limited
- API rate limits apply to real-mode usage
- Uncertainty estimates are approximations

## License

See [LICENSE](LICENSE) file.

## Support

For issues and questions, please refer to the documentation or open an issue.

---

**Disclaimer**: This is an engineering and forecasting project. Predictions should be compared with official environmental and public health sources. Not intended as medical, legal, or official guidance.
