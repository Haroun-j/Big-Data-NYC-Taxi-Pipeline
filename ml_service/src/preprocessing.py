"""
Data preprocessing and cleaning module for NYC Taxi fare prediction.

This module handles:
- Loading raw data from MinIO
- Data validation
- Cleaning (removing outliers and invalid records)
- Feature engineering
- Saving cleaned data

Run this script BEFORE training to prepare the data.
"""
import pandas as pd
import logging
import os

from paths import CLEANED_DATA_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# CONNECTION SETTINGS
# ============================================================

def minio_storage_options() -> dict:
    """
    Credentials and endpoint for s3fs, read from the environment
    (MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_ENDPOINT).
    """
    return {
        "key": os.environ.get("MINIO_ROOT_USER", "minio"),
        "secret": os.environ.get("MINIO_ROOT_PASSWORD", ""),
        "client_kwargs": {
            "endpoint_url": os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
        },
    }


def validated_data_path() -> str:
    """S3 prefix of the validated trips written by the Spark job."""
    bucket = os.environ.get("VALIDATED_BUCKET", "nyc-validated")
    year = os.environ.get("YEAR", "2023")
    return f"s3://{bucket}/{year}/"


# ============================================================
# DATA LOADING
# ============================================================

def load_data(s3_path: str, storage_options: dict) -> pd.DataFrame:
    """
    Load parquet data from MinIO (S3-compatible storage).

    Parameters
    ----------
    s3_path : str
        The S3 path to read parquet files from.
        Example: "s3://nyc-validated/2023/"
    storage_options : dict
        Storage options including credentials and endpoint.

    Returns
    -------
    pd.DataFrame
        Loaded dataframe with raw data.

    Raises
    ------
    Exception
        If data loading fails.
    """
    logger.info(f"Loading data from {s3_path}...")
    try:
        df = pd.read_parquet(s3_path, storage_options=storage_options)
        logger.info(f"Data loaded successfully. Shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_input_data(df: pd.DataFrame) -> bool:
    """
    Validate that input data has required columns and correct types.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe to validate.

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    ValueError
        If required columns are missing.
    """
    required_columns = [
        'trip_distance',
        'passenger_count',
        'PULocationID',
        'DOLocationID',
        'total_amount'
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    logger.info("Input data validation passed.")
    return True


# ============================================================
# DATA CLEANING
# ============================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean data by removing outliers and invalid records.

    Parameters
    ----------
    df : pd.DataFrame
        Raw input dataframe.

    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with outliers removed.

    Notes
    -----
    Removes records where:
    - total_amount <= 0 or > 500 (outliers)
    - trip_distance <= 0 or > 100 (invalid or outliers)
    - passenger_count <= 0 (invalid)
    """
    logger.info("=" * 50)
    logger.info("CLEANING DATA")
    logger.info("=" * 50)

    initial_count = len(df)
    logger.info(f"Initial row count: {initial_count:,}")

    # Filter 1: Remove invalid total_amount
    df = df[df['total_amount'] > 0]
    logger.info(f"After removing total_amount <= 0: {len(df):,}")

    df = df[df['total_amount'] < 500]
    logger.info(f"After removing total_amount > 500 (outliers): {len(df):,}")

    # Filter 2: Remove invalid trip_distance
    df = df[df['trip_distance'] > 0]
    logger.info(f"After removing trip_distance <= 0: {len(df):,}")

    df = df[df['trip_distance'] < 100]
    logger.info(f"After removing trip_distance > 100 (outliers): {len(df):,}")

    # Filter 3: Remove invalid passenger_count
    df = df[df['passenger_count'] > 0]
    logger.info(f"After removing passenger_count <= 0: {len(df):,}")

    final_count = len(df)
    removed = initial_count - final_count

    if initial_count > 0:
        pct_removed = removed / initial_count * 100
    else:
        pct_removed = 0.0

    logger.info("=" * 50)
    logger.info("CLEANING SUMMARY:")
    logger.info(f"  - Rows removed: {removed:,} ({pct_removed:.2f}%)")
    logger.info(f"  - Rows remaining: {final_count:,}")
    logger.info("=" * 50)

    return df


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create additional features from existing data.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned dataframe.

    Returns
    -------
    pd.DataFrame
        Dataframe with additional engineered features.

    Notes
    -----
    Adds the following features:
    - hour: Hour of pickup (0-23)
    - day_of_week: Day of week (0=Monday, 6=Sunday)
    - is_weekend: Boolean flag for weekend (1=weekend, 0=weekday)
    """
    logger.info("Engineering features...")

    df = df.copy()

    # Extract datetime features if pickup datetime exists
    if 'tpep_pickup_datetime' in df.columns:
        df['tpep_pickup_datetime'] = pd.to_datetime(
            df['tpep_pickup_datetime']
        )
        df['hour'] = df['tpep_pickup_datetime'].dt.hour
        df['day_of_week'] = df['tpep_pickup_datetime'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        logger.info("  - Added 'hour' from pickup datetime")
        logger.info("  - Added 'day_of_week' from pickup datetime")
        logger.info("  - Added 'is_weekend' flag")
    else:
        # Default values if datetime not available
        df['hour'] = 12
        df['day_of_week'] = 2
        df['is_weekend'] = 0
        logger.warning("  - No datetime column found, using defaults")

    logger.info("Feature engineering complete.")
    return df


# ============================================================
# MAIN PREPROCESSING PIPELINE
# ============================================================

def run_preprocessing(save_path: str = None, sample_size: int = 200000) -> pd.DataFrame:
    """
    Run the complete preprocessing pipeline.

    Parameters
    ----------
    save_path : str, optional
        Path to save the cleaned data as parquet.
        If None, data is not saved.
    sample_size : int, optional
        Number of rows to sample for training (default: 200000).
        Set to None to use all data.

    Returns
    -------
    pd.DataFrame
        Cleaned and preprocessed dataframe.
    """
    # Step 1: Load data
    df = load_data(validated_data_path(), minio_storage_options())

    # Step 2: Validate
    validate_input_data(df)

    # Step 3: Clean
    df = clean_data(df)

    # Step 4: Engineer features
    df = engineer_features(df)

    # Step 5: Sample data (stratified by price range for variety)
    if sample_size and len(df) > sample_size:
        logger.info("=" * 50)
        logger.info(f"SAMPLING DATA (keeping {sample_size:,} rows)")
        logger.info("=" * 50)

        # Create price bins for stratified sampling
        df['price_bin'] = pd.cut(
            df['total_amount'],
            bins=[0, 15, 25, 40, 100, 500],
            labels=['0-15', '15-25', '25-40', '40-100', '100+']
        )

        # Sample proportionally from each bin
        sampled_dfs = []
        for bin_label in df['price_bin'].dropna().unique():
            bin_df = df[df['price_bin'] == bin_label]
            bin_ratio = len(bin_df) / len(df)
            bin_sample_size = int(sample_size * bin_ratio)

            if len(bin_df) > bin_sample_size:
                sampled_dfs.append(
                    bin_df.sample(n=bin_sample_size, random_state=42)
                )
            else:
                sampled_dfs.append(bin_df)

        df = pd.concat(sampled_dfs, ignore_index=True)

        # Shuffle the data
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        # Remove temporary column
        df = df.drop(columns=['price_bin'])

        logger.info(f"Sampled data shape: {df.shape}")
        logger.info("Sampling preserves price distribution variety")

    # Step 6: Save if path provided
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_parquet(save_path, index=False)
        logger.info(f"Cleaned data saved to {save_path}")

    return df


def main():
    """
    Main entry point for preprocessing script.

    Saves cleaned data to ml_service/data/cleaned_data.parquet
    (or CLEANED_DATA_PATH).
    """
    logger.info("=" * 60)
    logger.info("NYC TAXI DATA PREPROCESSING")
    logger.info("=" * 60)

    save_path = CLEANED_DATA_PATH
    df = run_preprocessing(save_path)

    logger.info("=" * 60)
    logger.info("PREPROCESSING COMPLETE")
    logger.info(f"Output: {save_path}")
    logger.info(f"Shape: {df.shape}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next step: python train.py")


if __name__ == "__main__":
    main()
