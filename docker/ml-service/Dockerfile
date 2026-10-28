FROM python:3.11-slim

WORKDIR /app

# The service code is bind-mounted at /app by docker-compose; the image only
# carries the dependencies. The same image runs preprocessing and training
# from the Airflow DAG, so the model is always loaded with the scikit-learn
# version that produced it.
RUN pip install --no-cache-dir \
    "pandas>=2.0.0" \
    "scikit-learn>=1.3.0" \
    "pyarrow>=14.0.0" \
    "s3fs>=2023.10.0" \
    "joblib>=1.3.0" \
    "streamlit>=1.30.0"

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
