"""Prediction script for generating forecasts."""

import argparse
import json

from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.predict import generate_forecast
from pearls_aqi.settings import settings

logger = get_logger(__name__)


def run_prediction(location_id: str, horizon_days: int = 3, output_file: str = None):
    """Run prediction for a location.
    
    Args:
        location_id: Location identifier
        horizon_days: Number of days to forecast
        output_file: Optional file to save prediction
    """
    logger.info("Generating forecast", location=location_id, horizon=horizon_days)
    
    try:
        # Generate forecast
        forecast = generate_forecast(location_id, horizon_days=horizon_days)
        
        # Print results
        print(f"\n✓ Forecast Generated!")
        print(f"\n📍 Location: {forecast.location['city']}")
        print(f"🕐 Generated: {forecast.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🤖 Model: {forecast.model['name']} v{forecast.model['version']}")
        
        print(f"\n📅 {horizon_days}-Day Forecast:")
        print("-" * 70)
        
        for day_forecast in forecast.forecast:
            print(f"  {day_forecast.date}: AQI {day_forecast.aqi:.0f} ({day_forecast.category})")
            print(f"     Range: {day_forecast.lower:.0f} - {day_forecast.upper:.0f}")
            print(f"     {day_forecast.health_message}")
        
        # Alert
        if forecast.alert:
            alert_icon = "⚠️" if forecast.alert["level"] == "warning" else "🚨"
            print(f"\n{alert_icon} Alert: {forecast.alert['message']}")
        
        # Data quality
        print(f"\n📊 Data Quality:")
        print(f"   Last observation: {forecast.data_quality['latest_observation_at']}")
        print(f"   Hours since: {forecast.data_quality['hours_since_observation']:.1f}")
        print(f"   Missing fields: {forecast.data_quality['missing_feature_count']}")
        
        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(forecast.model_dump(mode="json"), f, indent=2, default=str)
            print(f"\n💾 Saved to: {output_file}")
        
    except Exception as e:
        logger.error("Prediction failed", error=str(e), location=location_id)
        print(f"\n✗ Error: {str(e)}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate AQI forecast")
    parser.add_argument("--city", type=str, default="karachi", help="City name (lowercase)")
    parser.add_argument("--horizon", type=int, default=3, help="Forecast horizon (days)")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    parser.add_argument("--demo", action="store_true", help="Use demo mode")
    
    args = parser.parse_args()
    
    if args.demo:
        settings.demo_mode = True
        settings.data_provider = "mock"
    
    run_prediction(
        location_id=args.city.lower(),
        horizon_days=args.horizon,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
