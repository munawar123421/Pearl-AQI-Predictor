# Operations Guide

## Installation

### Prerequisites

- Python 3.11 or later
- pip package manager
- Git (for version control)
- 4GB RAM minimum
- 10GB disk space for data storage

### Setup

```bash
# Clone repository
git clone <repository-url>
cd pearls-aqi-predictor

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Edit .env with your configuration
notepad .env
```

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Enable demo mode for testing
DEMO_MODE=true
DATA_PROVIDER=mock

# For production, set API keys
DEMO_MODE=false
DATA_PROVIDER=aqicn
AQICN_TOKEN=your_token_here
```

### Locations

Edit `configs/locations.yaml` to add/modify locations:

```yaml
locations:
  - location_id: "new_city"
    city: "New City"
    country: "Country"
    latitude: 0.0
    longitude: 0.0
    timezone: "UTC"
    aqicn_station: "@AXXXXX"
    enabled: true
```

## Daily Operations

### Starting Services

```bash
# Start FastAPI
uvicorn src.pearls_aqi.api.app:app --reload --host 0.0.0.0 --port 8000

# Start Dashboard
streamlit run dashboard/streamlit_app.py

# Or use Makefile
make api
make dashboard
```

### Running Pipelines

**Fetch Current Data:**
```bash
python scripts/fetch_current.py

# Specific city
python scripts/fetch_current.py --city Delhi

# Demo mode
python scripts/fetch_current.py --demo
```

**Backfill Historical Data:**
```bash
python scripts/backfill.py --city Delhi --start 2024-01-01 --end 2025-01-01

# Demo mode
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
```

**Train Models:**
```bash
python scripts/train.py

# Specific location
python scripts/train.py --location delhi

# Demo mode
python scripts/train.py --demo
```

**Generate Forecast:**
```bash
python scripts/predict.py --city delhi

# Save to file
python scripts/predict.py --city delhi --output forecast.json

# Demo mode
python scripts/predict.py --city delhi --demo
```

## Scheduled Automation

### GitHub Actions

Workflows are defined in `.github/workflows/`:

- `hourly-features.yml`: Runs every hour
- `daily-training.yml`: Runs daily at 2 AM UTC
- `tests.yml`: Runs on pull requests

**Triggering Manually:**
```bash
# Via GitHub UI: Actions > Select workflow > Run workflow

# Or using GitHub CLI
gh workflow run hourly-features.yml
```

### Apache Airflow (Optional)

Start Airflow:
```bash
# Using Docker Compose
docker-compose up -d

# Access UI
open http://localhost:8080
```

DAG Location: `dags/aqi_pipelines.py`

## Monitoring

### Logs

**Location:** Console output (stdout)

**Format:**
- Development: Colored console output
- Production: JSON structured logs

**Viewing Logs:**
```bash
# Follow API logs
uvicorn src.pearls_aqi.api.app:app --log-level info

# Dashboard logs
streamlit run dashboard/streamlit_app.py --logger.level=info
```

### Health Checks

**API Health:**
```bash
curl http://localhost:8000/health
```

**Feature Store Health:**
```python
from pearls_aqi.features.feature_store import get_feature_store
store = get_feature_store()
print(store.get_health_status())
```

**Model Registry:**
```python
from pearls_aqi.modeling.registry import get_registry
registry = get_registry()
print(registry.list_models())
```

### Metrics to Monitor

1. **Data Freshness**
   - Hours since last observation
   - Alert if >6 hours

2. **Feature Store**
   - Total rows per location
   - Missing value rate
   - Duplicate detection

3. **Model Performance**
   - Validation MAE
   - Training duration
   - Inference latency

4. **API**
   - Response time
   - Error rate
   - Request volume

## Troubleshooting

### Common Issues

**1. No training data**
```
Error: Need at least 168 rows, found 0
```
Solution: Run backfill first
```bash
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
```

**2. API key error**
```
ValueError: AQICN token is required
```
Solution: Set API keys in `.env` or enable demo mode

**3. Stale data warning**
```
Warning: Data is stale (10 hours old)
```
Solution: Run fetch_current.py or check data provider

**4. Model not found**
```
ValueError: No champion model found
```
Solution: Train models first
```bash
python scripts/train.py --demo
```

### Recovery Procedures

**Reset Feature Store:**
```bash
# Backup first
cp -r data/features data/features.backup

# Clean
rm -rf data/features/*

# Re-run backfill
python scripts/backfill.py --demo --start 2025-01-01 --end 2025-02-01
```

**Reset Model Registry:**
```bash
# Backup
cp -r data/models data/models.backup

# Clean
rm -rf data/models/*

# Retrain
python scripts/train.py --demo
```

**Full Reset:**
```bash
make clean-data
# Then re-run demo workflow
make demo
```

## Backup and Recovery

### What to Backup

1. **Configuration**
   - `.env` file
   - `configs/` directory

2. **Feature Store**
   - `data/features/` directory
   - Parquet files

3. **Model Registry**
   - `data/models/` directory
   - Model artifacts and metadata

4. **Raw Data** (optional)
   - `data/raw/` directory

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

cp .env $BACKUP_DIR/
cp -r configs/ $BACKUP_DIR/
cp -r data/features/ $BACKUP_DIR/
cp -r data/models/ $BACKUP_DIR/

echo "Backup created: $BACKUP_DIR"
```

### Restore

```bash
# Restore from backup
cp -r backups/20250101_120000/features/ data/
cp -r backups/20250101_120000/models/ data/
```

## Security

### Secrets Management

- Never commit `.env` file
- Use environment variables in production
- Rotate API keys regularly
- Use secret managers in cloud (AWS Secrets Manager, GCP Secret Manager)

### API Security

- Enable authentication in production
- Use HTTPS
- Rate limiting
- Input validation
- CORS configuration

### Data Privacy

- Do not log API keys
- Sanitize user inputs
- Encrypt data at rest (cloud)
- Access control for dashboards

## Scaling

### Horizontal Scaling

**API Layer:**
- Run multiple FastAPI instances behind load balancer
- Use Redis for shared cache
- Stateless design

**Training:**
- Parallelize by location
- Use distributed training libraries
- Schedule during off-peak hours

### Vertical Scaling

- Increase memory for large feature sets
- Use GPU for LSTM training
- SSD for faster I/O

### Cloud Migration

**Step 1:** Move feature store to cloud
- Google Cloud Storage + BigQuery
- AWS S3 + Athena
- Azure Blob + Synapse

**Step 2:** Containerize services
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "src.pearls_aqi.api.app:app", "--host", "0.0.0.0"]
```

**Step 3:** Deploy to managed platform
- Google Cloud Run
- AWS ECS/Fargate
- Azure Container Instances

## Maintenance

### Weekly Tasks

- Review model performance metrics
- Check data freshness
- Monitor error logs
- Review API usage

### Monthly Tasks

- Retrain models with latest data
- Update dependencies
- Review and prune old backups
- Performance optimization

### Quarterly Tasks

- Security audit
- Dependency updates
- Architecture review
- Capacity planning

## Support

### Getting Help

1. Check this documentation
2. Review logs for error details
3. Check GitHub issues
4. Review API documentation: http://localhost:8000/docs

### Reporting Issues

Include:
- Error message
- Steps to reproduce
- Environment (OS, Python version)
- Demo mode or production
- Relevant log excerpts
