"""
Inference script for NYC Taxi fare prediction.

This script loads a trained model and makes predictions on new data.
"""
import argparse
import logging
import joblib
import pandas as pd

from paths import MODEL_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_inference_input(data: dict) -> bool:
    """
    Validate input data for inference.

    Parameters
    ----------
    data : dict
        Input data dictionary with feature values.

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    required_fields = ['trip_distance', 'passenger_count',
                       'PULocationID', 'DOLocationID']

    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if data['trip_distance'] <= 0:
        raise ValueError("trip_distance must be positive")

    if data['passenger_count'] <= 0:
        raise ValueError("passenger_count must be positive")

    return True


def predict(model, data: dict) -> float:
    """
    Make a fare prediction for a single trip.

    Parameters
    ----------
    model : sklearn.Pipeline
        Trained model pipeline.
    data : dict
        Dictionary containing trip features:
        - trip_distance: float
        - passenger_count: int
        - PULocationID: int
        - DOLocationID: int
        - hour: int (optional, default 12)
        - day_of_week: int (optional, default 2)
        - is_weekend: int (optional, default 0)

    Returns
    -------
    float
        Predicted fare amount in dollars.
    """
    # Validate input
    validate_inference_input(data)

    # Set defaults for optional features
    data.setdefault('hour', 12)
    data.setdefault('day_of_week', 2)
    data.setdefault('is_weekend', 0)

    # Create dataframe
    df = pd.DataFrame([data])

    # Predict
    prediction = model.predict(df)[0]

    return round(prediction, 2)


def main():
    """
    CLI interface for inference.

    Usage:
        python inference.py --distance 5.2 --passengers 2 \
            --pickup 132 --dropoff 161
    """
    parser = argparse.ArgumentParser(
        description='Predict NYC Taxi fare'
    )
    parser.add_argument('--distance', type=float, required=True,
                        help='Trip distance in miles')
    parser.add_argument('--passengers', type=int, required=True,
                        help='Number of passengers')
    parser.add_argument('--pickup', type=int, required=True,
                        help='Pickup location ID')
    parser.add_argument('--dropoff', type=int, required=True,
                        help='Dropoff location ID')
    parser.add_argument('--hour', type=int, default=12,
                        help='Hour of pickup (0-23)')
    parser.add_argument('--model', type=str,
                        default=MODEL_PATH,
                        help='Path to trained model')

    args = parser.parse_args()

    # Load model
    logger.info(f"Loading model from {args.model}...")
    model = joblib.load(args.model)

    # Prepare input
    data = {
        'trip_distance': args.distance,
        'passenger_count': args.passengers,
        'PULocationID': args.pickup,
        'DOLocationID': args.dropoff,
        'hour': args.hour,
        'day_of_week': 2,
        'is_weekend': 0
    }

    # Predict
    fare = predict(model, data)
    logger.info(f"Predicted fare: ${fare}")
    print(f"${fare}")

    return fare


if __name__ == "__main__":
    main()
