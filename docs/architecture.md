# Architecture

## System Overview

Pearls AQI Predictor is an end-to-end ML system for forecasting Air Quality Index. The architecture follows a modular design with clear separation between data ingestion, feature engineering, model training, and inference.

## High-Level Architecture

```
┌─────────────────┐
│  Data Sources   │
│  (AQICN, OWM,   │
│   Mock)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Ingestion │
│  - Fetch API    │
│  - Validate     │
│  - Store Raw    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Feature Engine  │
│  - Time Features│
│  - Lags/Rolling │
│  - Targets      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Feature Store  │
│  (Local/Cloud)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Model Training  │
│  - Baselines    │
│  - Ridge/RF     │
│  - LSTM         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Model Registry  │
│  - Versioning   │
│  - Champion     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prediction API  │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Dashboard     │
│  (Streamlit)    │
└─────────────────┘
```

## Components

### 1. Data Providers

**Purpose:** Abstract interface for fetching air quality and weather data from multiple sources.

**Implementations:**
- `MockProvider`: Synthetic data generator for demo mode
- `AQICNProvider`: World Air Quality Index API client
- `OpenWeatherProvider`: OpenWeather API client

**Key Methods:**
- `fetch_current()`: Get latest observation
- `fetch_historical()`: Get historical time series
- `fetch_forecast()`: Get forecast data (if available)

### 2. Data Ingestion

**Purpose:** Fetch, validate, and persist raw observations.

**Features:**
- Request retry logic with exponential backoff
- Response validation against data contract
- Raw data persistence for audit trail
- Deduplication based on location + timestamp
- Structured logging

### 3. Feature Engineering

**Purpose:** Transform raw observations into ML-ready features.

**Feature Categories:**
- **Time**: hour, day_of_week, cyclical encodings
- **Current**: AQI, PM2.5, PM10, O3, NO2, SO2, CO
- **Weather**: temperature, humidity, pressure, wind
- **Lags**: 1h, 3h, 6h, 12h, 24h
- **Rolling**: mean, std, min, max over windows
- **Changes**: 1h and 3h differences
- **Data Quality**: missing count, imputation flags

**Target Creation:**
- Daily aggregated AQI for next 3 days
- Prevents future information leakage
- Configurable aggregation (mean/max/median)

### 4. Feature Store

**Purpose:** Centralized storage for features with versioning and time-travel.

**Local Implementation:**
- Parquet files partitioned by location and date
- Append-only writes with deduplication
- Efficient columnar storage
- Metadata tracking

**Interface:**
- Cloud-compatible abstraction
- Supports Hopsworks or Vertex AI backends
- Health checks and freshness monitoring

### 5. Model Training

**Purpose:** Train and evaluate multiple forecasting models.

**Models:**
1. **Naive Baseline**: Last known AQI
2. **Persistence**: Current AQI propagated forward
3. **Ridge Regression**: Linear model with regularization
4. **Random Forest**: Ensemble of decision trees
5. **LSTM**: (Optional) Sequence model for time series

**Training Pipeline:**
- Chronological train/val/test split
- Feature scaling (StandardScaler)
- Hyperparameter search
- Cross-validation on time series
- Metric calculation (MAE, RMSE, R²)

**Champion Selection:**
- Lowest validation MAE
- Test set evaluation
- Metadata tracking

### 6. Model Registry

**Purpose:** Version control and deployment management for trained models.

**Features:**
- Model artifact storage (pickle)
- Scaler and preprocessor persistence
- Metadata (metrics, features, dates)
- Champion model promotion
- Version history

### 7. Prediction Service

**Purpose:** Generate forecasts using champion model.

**Process:**
1. Load champion model from registry
2. Fetch latest features from feature store
3. Apply preprocessing
4. Generate 3-day predictions
5. Estimate uncertainty intervals
6. Classify AQI categories
7. Generate alerts if thresholds exceeded

### 8. FastAPI Application

**Purpose:** RESTful API for accessing predictions and data.

**Endpoints:**
- `/health`: Service status
- `/api/v1/locations`: Available locations
- `/api/v1/current`: Latest observation
- `/api/v1/forecast`: 3-day prediction
- `/api/v1/features`: Recent feature vectors
- `/api/v1/model`: Champion model info
- `/api/v1/explanation`: Feature importance

**Features:**
- OpenAPI documentation
- CORS support
- Error handling
- Request logging

### 9. Streamlit Dashboard

**Purpose:** Interactive web UI for visualization and exploration.

**Sections:**
- Current AQI with category
- 3-day forecast cards
- Historical trend charts
- Pollutant time series
- Weather correlations
- Alert banners
- Model performance metrics
- Data quality indicators

## Data Flow

### Hourly Pipeline

```
1. Scheduler triggers fetch_current.py
2. Provider fetches latest observation
3. Observation validated and saved
4. Features computed
5. Feature store updated
6. Health checks logged
```

### Daily Training Pipeline

```
1. Scheduler triggers train.py
2. Load training data from feature store
3. Create train/val/test split
4. Train multiple models
5. Evaluate on validation set
6. Select champion
7. Register all models
8. Promote champion
9. Publish metrics
```

### Inference Flow

```
1. User requests forecast via API/dashboard
2. Load champion model from registry
3. Fetch latest features from store
4. Apply preprocessing
5. Generate predictions
6. Add uncertainty bounds
7. Check alert thresholds
8. Return response
```

## Deployment Options

### Local Development

- Run all components on single machine
- SQLite/Parquet for storage
- Manual script execution
- Streamlit on localhost:8501
- FastAPI on localhost:8000

### Cloud Deployment

**Option 1: Serverless**
- Cloud Functions for pipelines
- Cloud Storage for feature store
- Cloud Run for API
- Vertex AI for model registry

**Option 2: Container-based**
- Docker containers for each service
- Kubernetes orchestration
- Cloud SQL for metadata
- Load balancer for API

**Option 3: Managed ML**
- Vertex AI Pipelines
- Hopsworks feature store
- Vertex AI Prediction
- Cloud Monitoring

## Scalability Considerations

1. **Data Volume**: Parquet partitioning by date
2. **Multiple Locations**: Parallel processing
3. **Model Training**: Distributed training (optional)
4. **API Load**: Horizontal scaling of FastAPI
5. **Feature Store**: Cloud backend for large scale

## Security

- No secrets in code or version control
- Environment variable configuration
- API key validation
- Rate limiting on external APIs
- Input sanitization
- Structured error messages (no stack traces)

## Monitoring

- Structured logs (JSON in production)
- Request IDs for tracing
- Pipeline metrics (rows, latency, errors)
- Model performance tracking
- Data freshness alerts
- Feature store health checks

## Testing Strategy

1. **Unit Tests**: Individual functions and classes
2. **Integration Tests**: Component interactions
3. **Data Contract Tests**: Schema validation
4. **Smoke Tests**: End-to-end workflows
5. **Demo Mode**: Full system without external dependencies
