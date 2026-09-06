@echo off
REM Demo workflow script for Pearls AQI Predictor (Windows)

echo ======================================
echo Pearls AQI Predictor - Demo Workflow
echo ======================================
echo.

echo Step 1: Backfilling historical data...
python scripts\backfill.py --demo --start 2025-01-01 --end 2025-02-01
if errorlevel 1 (
    echo Error in backfill step
    exit /b 1
)
echo.

echo Step 2: Training models...
python scripts\train.py --demo
if errorlevel 1 (
    echo Error in training step
    exit /b 1
)
echo.

echo Step 3: Generating forecast...
python scripts\predict.py --city delhi --demo
if errorlevel 1 (
    echo Error in prediction step
    exit /b 1
)
echo.

echo ======================================
echo Demo workflow complete!
echo ======================================
echo.
echo Next steps:
echo   - Start API:       python -m uvicorn src.pearls_aqi.api.app:app --reload
echo   - Start Dashboard: streamlit run dashboard\streamlit_app.py
echo.

pause
