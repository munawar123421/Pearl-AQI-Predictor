"""Streamlit dashboard for Pearls AQI Predictor."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.predict import generate_forecast
from pearls_aqi.modeling.registry import get_registry
from pearls_aqi.schemas import get_aqi_category
from pearls_aqi.settings import settings

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="Pearls AQI Predictor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .big-aqi {
        font-size: 72px;
        font-weight: bold;
        text-align: center;
        padding: 20px;
    }
    .metric-card {
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def get_aqi_color(aqi: float) -> str:
    """Get color for AQI value."""
    category = get_aqi_category(aqi)
    colors = {
        "green": "#00E400",
        "yellow": "#FFFF00",
        "orange": "#FF7E00",
        "red": "#FF0000",
        "purple": "#8F3F97",
        "maroon": "#7E0023",
    }
    return colors.get(category.color, "#808080")


def main():
    """Main dashboard function."""
    
    st.title("🌍 Pearls AQI Predictor")
    st.markdown("Air Quality Index Forecasting Dashboard")
    
    # Sidebar
    st.sidebar.header("Settings")
    
    location_id = st.sidebar.selectbox(
        "Select Location",
        ["karachi", "lahore", "beijing", "london", "new_york"],
        index=0,
    )
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    # Mode indicator
    if settings.demo_mode:
        st.sidebar.info("🎭 Demo Mode Active")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Model Status**")
    
    try:
        registry = get_registry()
        champion = registry.get_champion_metadata()
        
        if champion:
            st.sidebar.success(f"✓ {champion.get('model_name', 'Unknown')}")
            st.sidebar.caption(f"Version: {champion.get('version', 'Unknown')}")
        else:
            st.sidebar.warning("⚠ No champion model")
    except Exception as e:
        st.sidebar.error(f"✗ Registry error: {str(e)}")
    
    # Main content
    try:
        # Generate forecast
        with st.spinner("Generating forecast..."):
            forecast_response = generate_forecast(location_id, horizon_days=3)
        
        # Current Status Section
        st.header("📊 Current Air Quality")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Get current AQI from latest features
            feature_store = get_feature_store()
            latest = feature_store.get_latest_features(location_id)
            
            if latest is not None:
                current_aqi = latest.get("aqi_current", 100)
                category = get_aqi_category(current_aqi)
                
                st.markdown(
                    f'<div class="big-aqi" style="color: {get_aqi_color(current_aqi)};">'
                    f'{current_aqi:.0f}</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<p style="text-align: center; font-size: 24px;">{category.name}</p>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<p style="text-align: center;">{category.health_message}</p>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No current data available")
        
        with col2:
            st.metric("PM2.5", f"{latest.get('pm25', 0):.1f} μg/m³" if latest is not None else "N/A")
            st.metric("PM10", f"{latest.get('pm10', 0):.1f} μg/m³" if latest is not None else "N/A")
            st.metric("O3", f"{latest.get('o3', 0):.1f} μg/m³" if latest is not None else "N/A")
        
        with col3:
            st.metric("Temperature", f"{latest.get('temperature_c', 0):.1f} °C" if latest is not None else "N/A")
            st.metric("Humidity", f"{latest.get('humidity_pct', 0):.0f} %" if latest is not None else "N/A")
            st.metric("Wind Speed", f"{latest.get('wind_speed_ms', 0):.1f} m/s" if latest is not None else "N/A")
        
        # Alert Banner
        if forecast_response.alert:
            alert = forecast_response.alert
            if alert["level"] == "hazardous":
                st.error(f"🚨 {alert['message']}")
            else:
                st.warning(f"⚠️ {alert['message']}")
        
        # 3-Day Forecast
        st.header("📅 3-Day Forecast")
        
        forecast_cols = st.columns(3)
        
        for i, day_forecast in enumerate(forecast_response.forecast):
            with forecast_cols[i]:
                st.subheader(day_forecast.date)
                
                aqi_val = day_forecast.aqi
                aqi_color = get_aqi_color(aqi_val)
                
                st.markdown(
                    f'<div style="background-color: {aqi_color}; '
                    f'padding: 20px; border-radius: 10px; text-align: center;">'
                    f'<h1 style="color: white; margin: 0;">{aqi_val:.0f}</h1>'
                    f'<p style="color: white; margin: 5px 0 0 0;">{day_forecast.category}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                st.caption(f"Range: {day_forecast.lower:.0f} - {day_forecast.upper:.0f}")
                st.caption(day_forecast.health_message)
        
        # Historical Trends
        st.header("📈 Historical Trends")
        
        df = feature_store.read_features(location_id=location_id)
        
        if not df.empty and len(df) > 0:
            # Limit to recent data
            df = df.tail(168)  # Last week
            df["observed_at"] = pd.to_datetime(df["observed_at"])
            
            # AQI Trend
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["observed_at"],
                y=df["aqi_current"],
                mode="lines",
                name="AQI",
                line=dict(color="blue", width=2)
            ))
            
            fig.update_layout(
                title="AQI Over Time",
                xaxis_title="Time",
                yaxis_title="AQI",
                height=400,
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Pollutants
            col1, col2 = st.columns(2)
            
            with col1:
                fig_pm = go.Figure()
                fig_pm.add_trace(go.Scatter(
                    x=df["observed_at"],
                    y=df["pm25"],
                    mode="lines",
                    name="PM2.5",
                    line=dict(color="red")
                ))
                fig_pm.update_layout(
                    title="PM2.5 Concentration",
                    xaxis_title="Time",
                    yaxis_title="μg/m³",
                    height=300,
                )
                st.plotly_chart(fig_pm, use_container_width=True)
            
            with col2:
                fig_temp = go.Figure()
                fig_temp.add_trace(go.Scatter(
                    x=df["observed_at"],
                    y=df["temperature_c"],
                    mode="lines",
                    name="Temperature",
                    line=dict(color="orange")
                ))
                fig_temp.update_layout(
                    title="Temperature",
                    xaxis_title="Time",
                    yaxis_title="°C",
                    height=300,
                )
                st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("No historical data available")
        
        # Model Performance
        st.header("🤖 Model Performance")
        
        if champion:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Model Info")
                st.write(f"**Name:** {champion.get('model_name', 'Unknown')}")
                st.write(f"**Version:** {champion.get('version', 'Unknown')}")
                st.write(f"**Training Rows:** {champion.get('train_rows', 'N/A')}")
                st.write(f"**Validation Rows:** {champion.get('validation_rows', 'N/A')}")
            
            with col2:
                st.subheader("Metrics")
                val_metrics = champion.get("val_metrics", {})
                st.metric("MAE", f"{val_metrics.get('mae', 0):.2f}")
                st.metric("RMSE", f"{val_metrics.get('rmse', 0):.2f}")
                st.metric("R²", f"{val_metrics.get('r2', 0):.3f}")
        
        # Data Quality
        st.header("✅ Data Quality")
        
        dq = forecast_response.data_quality
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Last Observation", dq.get("latest_observation_at", "N/A")[:10])
        
        with col2:
            hours_since = dq.get("hours_since_observation", 999)
            is_stale = hours_since > 6
            st.metric(
                "Hours Since Update",
                f"{hours_since:.1f}",
                delta="Stale" if is_stale else "Fresh",
                delta_color="inverse" if is_stale else "normal"
            )
        
        with col3:
            missing = dq.get("missing_feature_count", 0)
            st.metric("Missing Fields", missing)
        
        # Disclaimer
        st.markdown("---")
        st.caption(
            "⚠️ **Disclaimer:** This is an engineering and forecasting project. "
            "Predictions are estimates and not medical or legal advice. "
            "Please compare with official environmental and public health sources."
        )
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        logger.error("Dashboard error", error=str(e))
        
        if settings.demo_mode:
            st.info("💡 Tip: Run the demo workflow first:\n```\npython scripts/run_demo.sh\n```")


if __name__ == "__main__":
    main()
