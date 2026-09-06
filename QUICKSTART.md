# Quick Start Guide

Get Pearls AQI Predictor running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

## Step 2: Run Demo Workflow

```bash
# Option A: Run complete demo (Windows)
scripts\run_demo.bat

# Option B: Run complete demo (Linux/Mac)
bash scripts/run_demo.sh

# Option C: Run step by step
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
python scripts/train.py --demo
python scripts/predict.py --city delhi --demo
```

## Step 3: Start Services

```bash
# Terminal 1: Start API
python -m uvicorn src.pearls_aqi.api.app:app --reload

# Terminal 2: Start Dashboard
streamlit run dashboard/streamlit_app.py
```

## Step 4: Access

- **Dashboard:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## What You'll See

### Dashboard
- Current AQI: 100 (Moderate) - color-coded display
- 3-Day Forecast: Day-by-day predictions
- Historical Charts: AQI trends over time
- Model Info: Random Forest with metrics

### API
Try these endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Get forecast
curl http://localhost:8000/api/v1/forecast?location_id=delhi

# Current observation
curl http://localhost:8000/api/v1/current?location_id=delhi
```

## Next Steps

### Use Real APIs

1. **Get API Keys:**
   - AQICN: https://aqicn.org/data-platform/token/
   - OpenWeather: https://openweathermap.org/api

2. **Configure:**
   ```bash
   copy .env.example .env
   # Edit .env and set:
   DEMO_MODE=false
   DATA_PROVIDER=aqicn
   AQICN_TOKEN=your_token_here
   ```

3. **Run with real data:**
   ```bash
   python scripts/fetch_current.py
   python scripts/backfill.py --city Delhi --start 2024-01-01 --end 2025-01-01
   python scripts/train.py
   ```

### Run Tests

```bash
# All tests
pytest

# Specific tests
pytest tests/unit/
pytest tests/smoke/

# With coverage
pytest --cov=src/pearls_aqi
```

### Add New Locations

Edit `configs/locations.yaml`:
```yaml
locations:
  - location_id: "new_city"
    city: "New City"
    country: "Country"
    latitude: 0.0
    longitude: 0.0
    aqicn_station: "@AXXXXX"
    enabled: true
```

## Troubleshooting

**Issue:** Import errors
```bash
# Solution: Ensure virtual environment is activated
.venv\Scripts\activate
```

**Issue:** No training data
```bash
# Solution: Run backfill first
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
```

**Issue:** Port already in use
```bash
# Solution: Use different ports
uvicorn src.pearls_aqi.api.app:app --port 8001
streamlit run dashboard/streamlit_app.py --server.port 8502
```

## Documentation

- **Architecture:** docs/architecture.md
- **Data Dictionary:** docs/data_dictionary.md
- **Model Report:** docs/model_report.md
- **Operations:** docs/operations.md
- **Full Project Report:** docs/project_report.md

## Support

For issues or questions:
1. Check documentation in `/docs`
2. Review API docs at http://localhost:8000/docs
3. Check logs for error details

---

**Enjoy forecasting air quality! 🌍**
