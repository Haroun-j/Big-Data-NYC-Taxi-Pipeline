"""
Unit tests for inference module.
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from inference import validate_inference_input


class TestValidateInferenceInput:
    """Tests for the validate_inference_input function."""

    def test_valid_input_passes(self):
        """Test that valid input passes validation."""
        data = {
            'trip_distance': 5.0,
            'passenger_count': 2,
            'PULocationID': 132,
            'DOLocationID': 161
        }
        assert validate_inference_input(data) is True

    def test_missing_field_raises_error(self):
        """Test that missing required field raises ValueError."""
        data = {
            'trip_distance': 5.0,
            'passenger_count': 2
            # Missing PULocationID and DOLocationID
        }

        with pytest.raises(ValueError) as excinfo:
            validate_inference_input(data)

        assert "Missing required field" in str(excinfo.value)

    def test_negative_distance_raises_error(self):
        """Test that negative distance raises ValueError."""
        data = {
            'trip_distance': -1.0,
            'passenger_count': 2,
            'PULocationID': 132,
            'DOLocationID': 161
        }

        with pytest.raises(ValueError) as excinfo:
            validate_inference_input(data)

        assert "trip_distance must be positive" in str(excinfo.value)

    def test_zero_passengers_raises_error(self):
        """Test that zero passengers raises ValueError."""
        data = {
            'trip_distance': 5.0,
            'passenger_count': 0,
            'PULocationID': 132,
            'DOLocationID': 161
        }

        with pytest.raises(ValueError) as excinfo:
            validate_inference_input(data)

        assert "passenger_count must be positive" in str(excinfo.value)
