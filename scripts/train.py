"""Model training script."""

import argparse
from datetime import datetime

from pearls_aqi.features.feature_store import get_feature_store
from pearls_aqi.features.transform import get_feature_columns, get_target_columns
from pearls_aqi.logging_config import get_logger
from pearls_aqi.modeling.registry import get_registry
from pearls_aqi.modeling.train import select_champion, train_models
from pearls_aqi.modeling.dataset import prepare_train_test_split
from pearls_aqi.settings import settings

logger = get_logger(__name__)


def run_training(location_id: str = "delhi", min_rows: int = None):
    """Run model training pipeline.
    
    Args:
        location_id: Location to train for
        min_rows: Minimum rows required for training
    """
    logger.info("Starting model training", location=location_id)
    
    min_rows = min_rows or settings.min_training_rows
    
    # Load training data
    logger.info("Loading training data from feature store")
    feature_store = get_feature_store()
    df = feature_store.read_training_dataset(location_id=location_id, min_rows=min_rows)
    
    if len(df) < min_rows:
        logger.error(
            "Insufficient training data",
            rows=len(df),
            required=min_rows,
        )
        print(f"✗ Error: Need at least {min_rows} rows, found {len(df)}")
        return
    
    logger.info(f"Loaded {len(df)} rows")
    
    # Drop rows without targets
    feature_cols = get_feature_columns()
    target_cols = get_target_columns()
    
    df_valid = df.dropna(subset=target_cols)
    logger.info(f"Valid training rows: {len(df_valid)}")
    
    if len(df_valid) < min_rows:
        logger.error("Insufficient rows with valid targets")
        print(f"✗ Error: Need at least {min_rows} rows with targets, found {len(df_valid)}")
        return
    
    # Create train/val/test split
    train_df, val_df, test_df = prepare_train_test_split(
        df_valid,
        test_size=settings.test_split,
        validation_size=settings.validation_split,
    )
    
    # Train models
    logger.info("Training models")
    results = train_models(train_df, val_df, test_df, feature_cols, target_cols)
    
    if not results:
        logger.error("No models were trained successfully")
        print("✗ Error: Training failed")
        return
    
    # Select champion
    champion_name = select_champion(results, metric="mae")
    
    # Register models
    logger.info("Registering models")
    registry = get_registry()
    
    data_start = df["observed_at"].min().date().isoformat()
    data_end = df["observed_at"].max().date().isoformat()
    
    for model_name, result in results.items():
        metadata = {
            "data_start_date": data_start,
            "data_end_date": data_end,
            "train_rows": len(train_df),
            "validation_rows": len(val_df),
            "test_rows": len(test_df),
            "feature_cols": feature_cols,
            "target_cols": target_cols,
            "train_metrics": result["train_metrics"],
            "val_metrics": result["val_metrics"],
            "test_metrics": result["test_metrics"],
            "training_time": result["training_time"],
            "hyperparameters": {},
        }
        
        version = registry.register_model(
            model=result["model"],
            scaler=result["scaler"],
            metadata=metadata,
            model_name=model_name,
        )
        
        logger.info(f"Registered {model_name} as version {version}")
    
    # Set champion
    champion_result = results[champion_name]
    champion_version = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    registry.register_model(
        model=champion_result["model"],
        scaler=champion_result["scaler"],
        metadata={
            **champion_result,
            "data_start_date": data_start,
            "data_end_date": data_end,
            "is_champion": True,
        },
        model_name=champion_name,
        version=champion_version,
    )
    
    registry.set_champion(f"{champion_name}_{champion_version}")
    
    # Print summary
    print(f"\n✓ Training complete!")
    print(f"\n📊 Model Performance:")
    print(f"{'Model':<20} {'Val MAE':<12} {'Val RMSE':<12} {'Val R²':<10}")
    print("-" * 60)
    
    for model_name, result in results.items():
        val_metrics = result["val_metrics"]
        is_champion = "🏆" if model_name == champion_name else "  "
        print(
            f"{is_champion} {model_name:<18} "
            f"{val_metrics['mae']:<12.2f} "
            f"{val_metrics['rmse']:<12.2f} "
            f"{val_metrics['r2']:<10.3f}"
        )
    
    print(f"\n🏆 Champion: {champion_name}")
    print(f"   Version: {champion_version}")
    
    champion_metrics = results[champion_name]["test_metrics"]
    print(f"\n📈 Test Set Performance:")
    print(f"   MAE:  {champion_metrics['mae']:.2f}")
    print(f"   RMSE: {champion_metrics['rmse']:.2f}")
    print(f"   R²:   {champion_metrics['r2']:.3f}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Train AQI prediction models")
    parser.add_argument("--location", type=str, default="delhi", help="Location ID")
    parser.add_argument("--min-rows", type=int, default=None, help="Minimum training rows")
    parser.add_argument("--demo", action="store_true", help="Use demo mode")
    
    args = parser.parse_args()
    
    if args.demo:
        settings.demo_mode = True
        settings.data_provider = "mock"
    
    run_training(location_id=args.location, min_rows=args.min_rows)


if __name__ == "__main__":
    main()
