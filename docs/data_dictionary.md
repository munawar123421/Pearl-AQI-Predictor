# Data Dictionary

## Observation Schema

Raw air quality and weather observations from external APIs.

| Field | Type | Unit | Range | Description | Source |
|-------|------|------|-------|-------------|--------|
| `location_id` | string | - | - | Unique location identifier | Config |
| `city` | string | - | - | City name | Config |
| `country` | string | - | - | Country name | Config |
| `latitude` | float | degrees | -90 to 90 | Location latitude | Config |
| `longitude` | float | degrees | -180 to 180 | Location longitude | Config |
| `source` | string | - | - | Data provider (aqicn, openweather, mock) | Provider |
| `observed_at` | datetime | UTC | - | Time of observation | Provider |
| `retrieved_at` | datetime | UTC | - | Time data was fetched | System |
| `timezone` | string | - | - | Location timezone (IANA format) | Config |
| `aqi` | float | index | 0-500 | Air Quality Index (US EPA scale) | Provider |
| `pm25` | float | μg/m³ | ≥0 | Particulate matter <2.5μm | Provider |
| `pm10` | float | μg/m³ | ≥0 | Particulate matter <10μm | Provider |
| `o3` | float | μg/m³ | ≥0 | Ozone concentration | Provider |
| `no2` | float | μg/m³ | ≥0 | Nitrogen dioxide concentration | Provider |
| `so2` | float | μg/m³ | ≥0 | Sulfur dioxide concentration | Provider |
| `co` | float | mg/m³ | ≥0 | Carbon monoxide concentration | Provider |
| `temperature_c` | float | °C | - | Air temperature | Provider |
| `humidity_pct` | float | % | 0-100 | Relative humidity | Provider |
| `pressure_hpa` | float | hPa | ≥0 | Atmospheric pressure | Provider |
| `wind_speed_ms` | float | m/s | ≥0 | Wind speed | Provider |
| `wind_direction_deg` | float | degrees | 0-360 | Wind direction (0=North) | Provider |
| `precipitation_mm` | float | mm | ≥0 | Precipitation amount | Provider |
| `cloud_pct` | float | % | 0-100 | Cloud coverage | Provider |
| `is_observed` | bool | - | - | True if historical/current data | System |
| `is_forecast` | bool | - | - | True if forecast data | System |
| `missing_field_count` | int | count | ≥0 | Number of null optional fields | System |
| `data_quality_flag` | string | - | - | Quality indicator (excellent, good, fair, poor) | System |
| `raw_payload_hash` | string | - | - | MD5 hash of source response | System |

## Feature Schema

Engineered features for model training and inference.

### Time Features

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| `hour` | int | 0-23 | Hour of day |
| `day_of_week` | int | 0-6 | Day (0=Monday) |
| `day_of_month` | int | 1-31 | Day of month |
| `month` | int | 1-12 | Month |
| `week_of_year` | int | 1-53 | ISO week number |
| `is_weekend` | bool | - | True if Saturday/Sunday |
| `hour_sin` | float | -1 to 1 | Cyclical hour encoding |
| `hour_cos` | float | -1 to 1 | Cyclical hour encoding |
| `month_sin` | float | -1 to 1 | Cyclical month encoding |
| `month_cos` | float | -1 to 1 | Cyclical month encoding |

### Current Measurements

| Feature | Type | Unit | Description |
|---------|------|------|-------------|
| `aqi_current` | float | index | Current AQI value |
| `pm25` | float | μg/m³ | PM2.5 concentration |
| `pm10` | float | μg/m³ | PM10 concentration |
| `o3` | float | μg/m³ | Ozone |
| `no2` | float | μg/m³ | Nitrogen dioxide |
| `so2` | float | μg/m³ | Sulfur dioxide |
| `co` | float | mg/m³ | Carbon monoxide |

### Weather Features

| Feature | Type | Unit | Description |
|---------|------|------|-------------|
| `temperature_c` | float | °C | Temperature |
| `humidity_pct` | float | % | Humidity |
| `pressure_hpa` | float | hPa | Pressure |
| `wind_speed_ms` | float | m/s | Wind speed |
| `wind_direction_sin` | float | -1 to 1 | Wind direction (sin) |
| `wind_direction_cos` | float | -1 to 1 | Wind direction (cos) |
| `cloud_pct` | float | % | Cloud cover |
| `precipitation_mm` | float | mm | Precipitation |

### Lag Features

| Feature | Type | Description |
|---------|------|-------------|
| `aqi_lag_1h` | float | AQI 1 hour ago |
| `aqi_lag_3h` | float | AQI 3 hours ago |
| `aqi_lag_6h` | float | AQI 6 hours ago |
| `aqi_lag_12h` | float | AQI 12 hours ago |
| `aqi_lag_24h` | float | AQI 24 hours ago |
| `pm25_lag_1h` | float | PM2.5 1 hour ago |
| `pm25_lag_3h` | float | PM2.5 3 hours ago |
| `pm25_lag_6h` | float | PM2.5 6 hours ago |

### Rolling Statistics

| Feature | Type | Window | Description |
|---------|------|--------|-------------|
| `aqi_rolling_mean_3h` | float | 3h | 3-hour mean AQI |
| `aqi_rolling_mean_6h` | float | 6h | 6-hour mean AQI |
| `aqi_rolling_mean_12h` | float | 12h | 12-hour mean AQI |
| `aqi_rolling_mean_24h` | float | 24h | 24-hour mean AQI |
| `aqi_rolling_std_3h` | float | 3h | 3-hour std dev |
| `aqi_rolling_std_12h` | float | 12h | 12-hour std dev |
| `aqi_rolling_min_12h` | float | 12h | 12-hour minimum |
| `aqi_rolling_max_12h` | float | 12h | 12-hour maximum |

### Change Features

| Feature | Type | Description |
|---------|------|-------------|
| `aqi_change_1h` | float | Change from 1 hour ago |
| `aqi_change_3h` | float | Change from 3 hours ago |
| `aqi_change_rate_1h` | float | Rate of change per hour |
| `pm25_change_1h` | float | PM2.5 change from 1 hour ago |

### Data Quality Features

| Feature | Type | Description |
|---------|------|-------------|
| `missing_field_count` | int | Number of missing values |
| `imputation_flag` | bool | True if values were imputed |
| `source_reliability_flag` | string | Source quality indicator |
| `hours_since_observation` | float | Data staleness |

## Target Schema

Supervised learning targets for multi-horizon forecasting.

| Target | Type | Unit | Description |
|--------|------|------|-------------|
| `target_aqi_day_1` | float | index | Mean AQI for next day |
| `target_aqi_day_2` | float | index | Mean AQI for day after next |
| `target_aqi_day_3` | float | index | Mean AQI for third day |

**Aggregation:** Hourly observations aggregated to daily mean by calendar date.

**Null Handling:** Rows without sufficient future observations have null targets and are excluded from training.

## AQI Categories

Based on US EPA Air Quality Index scale.

| AQI Range | Category | Color | Health Implications |
|-----------|----------|-------|---------------------|
| 0-50 | Good | Green | Air quality is satisfactory |
| 51-100 | Moderate | Yellow | Acceptable for most people |
| 101-150 | Unhealthy for Sensitive Groups | Orange | Sensitive groups may be affected |
| 151-200 | Unhealthy | Red | Everyone may experience effects |
| 201-300 | Very Unhealthy | Purple | Health alert conditions |
| 301-500 | Hazardous | Maroon | Emergency conditions |

## Data Quality Flags

| Flag | Description |
|------|-------------|
| `excellent` | All fields present, recent observation |
| `good` | <3 missing fields, recent observation |
| `fair` | 3-5 missing fields or slightly stale |
| `poor` | >5 missing fields or very stale |

## Missing Value Handling

- **Observation Level**: Null pollutants/weather preserved, counted in `missing_field_count`
- **Feature Level**: Simple mean imputation during preprocessing
- **Target Level**: Rows with missing targets excluded from training
- **Inference**: Use latest available features, flag missing values

## Data Sources

### AQICN (waqi.info)

- **Coverage**: Global, 12,000+ stations
- **Update Frequency**: Hourly
- **AQI Scale**: US EPA or local (documented in response)
- **Free Tier**: 1,000 requests/day
- **Limitations**: Limited historical data access

### OpenWeather

- **Coverage**: Global, weather-focused
- **Update Frequency**: Hourly
- **AQI Scale**: European (1-5), converted to US EPA
- **Free Tier**: 1,000 requests/day
- **Limitations**: Limited air quality coverage

### Mock Provider

- **Purpose**: Demo and testing
- **Generation**: Deterministic synthetic data
- **Patterns**: Daily and seasonal variations
- **Range**: Realistic AQI values (10-300)
