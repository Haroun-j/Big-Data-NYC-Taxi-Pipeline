"""
Unit tests for preprocessing module.
"""
import pytest
import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from preprocessing import clean_data, validate_input_data, engineer_features


class TestCleanData:
    """Tests for the clean_data function."""

    def test_removes_negative_amounts(self):
        """Test that negative total_amount values are removed."""
        data = {
            'total_amount': [10.0, -5.0, 20.0],
            'trip_distance': [2.0, 1.0, 3.0],
            'passenger_count': [1, 1, 2]
        }
        df = pd.DataFrame(data)
        result = clean_data(df)

        assert len(result) == 2
        assert (result['total_amount'] > 0).all()

    def test_removes_zero_distance(self):
        """Test that zero or negative distances are removed."""
        data = {
            'total_amount': [10.0, 15.0, 20.0],
            'trip_distance': [2.0, 0.0, -1.0],
            'passenger_count': [1, 1, 2]
        }
        df = pd.DataFrame(data)
        result = clean_data(df)

        assert len(result) == 1
        assert (result['trip_distance'] > 0).all()

    def test_removes_outliers(self):
        """Test that extreme outliers are removed."""
        data = {
            'total_amount': [10.0, 600.0, 20.0],
            'trip_distance': [2.0, 5.0, 150.0],
            'passenger_count': [1, 1, 2]
        }
        df = pd.DataFrame(data)
        result = clean_data(df)

        assert len(result) == 1
        assert result.iloc[0]['total_amount'] == 10.0

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame(columns=[
            'total_amount', 'trip_distance', 'passenger_count'
        ])
        result = clean_data(df)
        assert len(result) == 0


class TestValidateInputData:
    """Tests for the validate_input_data function."""

    def test_valid_data_passes(self):
        """Test that valid data passes validation."""
        data = {
            'trip_distance': [2.0],
            'passenger_count': [1],
            'PULocationID': [132],
            'DOLocationID': [161],
            'total_amount': [15.0]
        }
        df = pd.DataFrame(data)
        assert validate_input_data(df) is True

    def test_missing_column_raises_error(self):
        """Test that missing required column raises ValueError."""
        data = {
            'trip_distance': [2.0],
            'passenger_count': [1]
            # Missing PULocationID, DOLocationID, total_amount
        }
        df = pd.DataFrame(data)

        with pytest.raises(ValueError) as excinfo:
            validate_input_data(df)

        assert "Missing required columns" in str(excinfo.value)


class TestEngineerFeatures:
    """Tests for the engineer_features function."""

    def test_adds_hour_feature(self):
        """Test that hour feature is added from datetime."""
        data = {
            'tpep_pickup_datetime': ['2023-06-15 14:30:00'],
            'total_amount': [20.0]
        }
        df = pd.DataFrame(data)
        result = engineer_features(df)

        assert 'hour' in result.columns
        assert result.iloc[0]['hour'] == 14

    def test_adds_day_of_week(self):
        """Test that day_of_week feature is added."""
        data = {
            'tpep_pickup_datetime': ['2023-06-15 14:30:00'],  # Thursday
            'total_amount': [20.0]
        }
        df = pd.DataFrame(data)
        result = engineer_features(df)

        assert 'day_of_week' in result.columns
        assert result.iloc[0]['day_of_week'] == 3  # Thursday = 3

    def test_weekend_flag(self):
        """Test that is_weekend flag is correctly set."""
        data = {
            'tpep_pickup_datetime': [
                '2023-06-17 14:30:00',  # Saturday
                '2023-06-15 14:30:00'   # Thursday
            ],
            'total_amount': [20.0, 15.0]
        }
        df = pd.DataFrame(data)
        result = engineer_features(df)

        assert result.iloc[0]['is_weekend'] == 1  # Saturday
        assert result.iloc[1]['is_weekend'] == 0  # Thursday
