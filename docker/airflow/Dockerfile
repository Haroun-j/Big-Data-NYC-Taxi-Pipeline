FROM apache/airflow:2.8.1

USER airflow
# DockerOperator support, used by orchestration/dags/nyc_taxi_pipeline.py
RUN pip install --no-cache-dir apache-airflow-providers-docker
