"""
Training script for NYC Taxi fare prediction model.

This script:
1. Loads preprocessed data (from preprocessing.py output)
2. Splits into train/test sets
3. Trains a Random Forest Regressor model
4. Evaluates the model and displays metrics
5. Saves the trained model

Run preprocessing.py BEFORE this script.
"""
import os
import logging
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

from preprocessing import run_preprocessing
from paths import CLEANED_DATA_PATH, MODEL_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# FEATURE CONFIGURATION
# ============================================================

FEATURE_COLUMNS = [
    'trip_distance',
    'passenger_count',
    'PULocationID',
    'DOLocationID',
    'hour',
    'day_of_week',
    'is_weekend'
]

TARGET_COLUMN = 'total_amount'


# ============================================================
# MODEL CREATION
# ============================================================

def create_model_pipeline() -> Pipeline:
    """
    Create the ML pipeline with preprocessing and Random Forest model.

    Returns
    -------
    Pipeline
        Scikit-learn pipeline with:
        - Numeric preprocessing (imputation + scaling)
        - Random Forest Regressor

    Notes
    -----
    Random Forest Hyperparameters:
    - n_estimators: 100 (number of trees)
    - max_depth: 15 (prevents overfitting)
    - min_samples_split: 10 (regularization)
    - n_jobs: -1 (use all CPU cores)
    - random_state: 42 (reproducibility)
    """
    logger.info("Creating Random Forest pipeline...")

    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, FEATURE_COLUMNS)
        ]
    )

    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(
            n_estimators=250,
            max_depth=12,
            min_samples_split=15,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        ))
    ])

    logger.info("  - Algorithm: Random Forest Regressor")
    logger.info("  - n_estimators: 250")
    logger.info("  - max_depth: 12")
    logger.info("  - min_samples_split: 15")
    logger.info("  - min_samples_leaf: 5")
    logger.info("  - Features: " + ", ".join(FEATURE_COLUMNS))

    return model


# ============================================================
# MODEL EVALUATION
# ============================================================

def evaluate_model(y_true, y_pred) -> dict:
    """
    Evaluate model performance using multiple metrics.

    Parameters
    ----------
    y_true : array-like
        True target values.
    y_pred : array-like
        Predicted values.

    Returns
    -------
    dict
        Dictionary containing:
        - rmse: Root Mean Squared Error
        - mae: Mean Absolute Error
        - r2: R-squared score
    """
    mse = mean_squared_error(y_true, y_pred)
    rmse = mse ** 0.5
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    metrics = {
        'rmse': rmse,
        'mae': mae,
        'r2': r2
    }

    return metrics


def display_metrics(metrics: dict) -> None:
    """
    Display evaluation metrics in a formatted way.

    Parameters
    ----------
    metrics : dict
        Dictionary with rmse, mae, r2 keys.
    """
    logger.info("=" * 60)
    logger.info("MODEL EVALUATION METRICS")
    logger.info("=" * 60)
    logger.info(f"  RMSE (Root Mean Squared Error): {metrics['rmse']:.4f}")
    logger.info(f"  MAE (Mean Absolute Error):      {metrics['mae']:.4f}")
    logger.info(f"  R2 Score:                       {metrics['r2']:.4f}")
    logger.info("=" * 60)

    # The course target was RMSE < 10 on the held-out set.
    if metrics['rmse'] < 10:
        logger.info("RMSE below 10: target reached")
    else:
        logger.warning("RMSE above 10: model needs work")


# ============================================================
# MAIN TRAINING PIPELINE
# ============================================================

def train_model(df: pd.DataFrame) -> tuple:
    """
    Train the Random Forest model with overfitting detection.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed dataframe with features and target.

    Returns
    -------
    tuple
        (trained_model, metrics_dict)
    """
    logger.info("=" * 60)
    logger.info("PREPARING DATA FOR TRAINING")
    logger.info("=" * 60)

    # Prepare features and target
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    logger.info(f"Features shape: {X.shape}")
    logger.info(f"Target shape: {y.shape}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    logger.info(f"Training set size: {len(X_train):,}")
    logger.info(f"Test set size: {len(X_test):,}")

    # Create and train model
    logger.info("=" * 60)
    logger.info("TRAINING MODEL")
    logger.info("=" * 60)

    model = create_model_pipeline()

    logger.info("Training in progress... (this may take a few minutes)")
    model.fit(X_train, y_train)
    logger.info("Training complete!")

    # ============================================================
    # OVERFITTING DETECTION
    # ============================================================
    logger.info("=" * 60)
    logger.info("OVERFITTING DETECTION")
    logger.info("=" * 60)

    # Calculate RMSE on training set
    y_train_pred = model.predict(X_train)
    train_rmse = mean_squared_error(y_train, y_train_pred) ** 0.5

    # Calculate RMSE on test set
    y_pred = model.predict(X_test)
    test_rmse = mean_squared_error(y_test, y_pred) ** 0.5

    logger.info(f"  RMSE on TRAIN set: {train_rmse:.4f}")
    logger.info(f"  RMSE on TEST set:  {test_rmse:.4f}")

    # Calculate overfitting ratio
    overfit_ratio = (test_rmse - train_rmse) / train_rmse * 100

    if abs(overfit_ratio) < 15:
        logger.info(f"  Difference: {overfit_ratio:+.1f}% (no significant overfitting)")
    elif overfit_ratio > 0:
        logger.warning(f"  Difference: {overfit_ratio:+.1f}% (possible overfitting)")
    else:
        logger.info(f"  Difference: {overfit_ratio:+.1f}% (model generalizes well)")

    # Cross-validation on the training split only, so the test set stays
    # untouched until the final evaluation.
    logger.info("")
    logger.info("Running 5-fold Cross-Validation...")
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=5,
        scoring='neg_mean_squared_error',
        n_jobs=-1
    )
    cv_rmse = (-cv_scores) ** 0.5
    logger.info(f"  CV RMSE scores: {cv_rmse}")
    logger.info(f"  CV RMSE mean: {cv_rmse.mean():.4f} (+/- {cv_rmse.std():.4f})")

    # Evaluate final metrics
    metrics = evaluate_model(y_test, y_pred)
    metrics['train_rmse'] = train_rmse
    metrics['cv_rmse_mean'] = cv_rmse.mean()
    display_metrics(metrics)

    return model, metrics


def main():
    """
    Main entry point for training script.
    """
    logger.info("=" * 60)
    logger.info("NYC TAXI FARE PREDICTION - MODEL TRAINING")
    logger.info("=" * 60)

    # Check for preprocessed data
    data_path = CLEANED_DATA_PATH

    if os.path.exists(data_path):
        logger.info(f"Loading preprocessed data from {data_path}...")
        df = pd.read_parquet(data_path)
        logger.info(f"Data loaded. Shape: {df.shape}")
    else:
        logger.info("No preprocessed data found. Running preprocessing...")
        df = run_preprocessing(data_path)

    # Train model
    model, metrics = train_model(df)

    # Save model
    model_path = MODEL_PATH
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    joblib.dump(model, model_path)
    logger.info(f"Model saved to {model_path}")

    # Summary
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Model saved: {model_path}")
    logger.info(f"Final RMSE: {metrics['rmse']:.4f}")
    logger.info("")
    logger.info("Next step: python inference.py --help")

    return model, metrics


if __name__ == "__main__":
    main()
