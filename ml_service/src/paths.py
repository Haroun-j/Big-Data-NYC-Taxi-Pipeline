"""
Default file locations for the service, relative to the ml_service folder so
the scripts work from any working directory (host, Docker, Airflow task).
Each one can be overridden with an environment variable.
"""
import os

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLEANED_DATA_PATH = os.environ.get(
    "CLEANED_DATA_PATH", os.path.join(MODULE_DIR, "data", "cleaned_data.parquet")
)
MODEL_PATH = os.environ.get(
    "MODEL_PATH", os.path.join(MODULE_DIR, "models", "taxi_fare_model.joblib")
)
