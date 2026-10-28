"""
NYC taxi pipeline: validate and load the TLC data with Spark, check the
warehouse, then rebuild the fare model.

Every heavy step runs in its own container through the DockerOperator, on the
same Docker network as the compose stack. The repository is bind-mounted at
/app in those containers, so the Spark fat jar, the ML scripts and the model
folder are the ones from this checkout.

Required environment (set in .env, passed through docker-compose):
  PROJECT_DIR           host path of this repository
  DOCKER_NETWORK        network created by docker-compose (nyc-taxi-net)
  MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
  POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

PROJECT_DIR = os.environ.get("PROJECT_DIR")
if not PROJECT_DIR:
    raise RuntimeError("PROJECT_DIR is not set: put the host path of the repository in .env")

NETWORK = os.environ.get("DOCKER_NETWORK", "nyc-taxi-net")
DOCKER_URL = "unix://var/run/docker.sock"
SPARK_DRIVER_MEMORY = os.environ.get("SPARK_DRIVER_MEMORY", "16g")

POSTGRES_DB = os.environ.get("POSTGRES_DB", "taxi")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

# Connection settings seen from inside the compose network.
SERVICE_ENV = {
    "MINIO_ENDPOINT": "http://minio:9000",
    "MINIO_ROOT_USER": os.environ.get("MINIO_ROOT_USER", ""),
    "MINIO_ROOT_PASSWORD": os.environ.get("MINIO_ROOT_PASSWORD", ""),
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": POSTGRES_DB,
    "POSTGRES_USER": POSTGRES_USER,
    "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    "ZONE_LOOKUP_CSV": "/app/data/external/taxi_zone_lookup.csv",
    "PYTHONUNBUFFERED": "1",
}

PROJECT_MOUNT = Mount(source=PROJECT_DIR, target="/app", type="bind")

default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="nyc_taxi_pipeline",
    description="Validate and load NYC taxi trips, then retrain the fare model",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,        # the 2023 data is static: trigger by hand
    catchup=False,
    tags=["nyc-taxi", "spark", "ml"],
) as dag:

    # The ingestion job runs in local mode with a large driver heap, which is
    # how it was run for the real load (the 2 GB workers of the standalone
    # cluster cannot hold the broadcast of the datetime dimension).
    validate_and_load = DockerOperator(
        task_id="validate_and_load",
        image="bitnami/spark:3.5",
        api_version="auto",
        auto_remove=True,
        command=(
            "spark-submit "
            "--master local[*] "
            f"--driver-memory {SPARK_DRIVER_MEMORY} "
            "--packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 "
            "/app/ingestion/spark/target/scala-2.13/ingestion-assembly.jar"
        ),
        environment=SERVICE_ENV,
        docker_url=DOCKER_URL,
        network_mode=NETWORK,
        mounts=[PROJECT_MOUNT],
    )

    check_warehouse = DockerOperator(
        task_id="check_warehouse",
        image="postgres:16",
        api_version="auto",
        auto_remove=True,
        command=(
            f'psql -h postgres -U {POSTGRES_USER} -d {POSTGRES_DB} '
            '-c "SELECT COUNT(*) AS trips FROM fact_trip;"'
        ),
        environment={"PGPASSWORD": POSTGRES_PASSWORD},
        docker_url=DOCKER_URL,
        network_mode=NETWORK,
    )

    # Same image as the Streamlit service, so training and serving use the
    # same library versions.
    ml_preprocessing = DockerOperator(
        task_id="ml_preprocessing",
        image="nyc-taxi/ml-service",
        api_version="auto",
        auto_remove=True,
        command="python /app/ml_service/src/preprocessing.py",
        environment=SERVICE_ENV,
        docker_url=DOCKER_URL,
        network_mode=NETWORK,
        mounts=[PROJECT_MOUNT],
    )

    ml_training = DockerOperator(
        task_id="ml_training",
        image="nyc-taxi/ml-service",
        api_version="auto",
        auto_remove=True,
        command="python /app/ml_service/src/train.py",
        environment=SERVICE_ENV,
        docker_url=DOCKER_URL,
        network_mode=NETWORK,
        mounts=[PROJECT_MOUNT],
    )

    validate_and_load >> check_warehouse >> ml_preprocessing >> ml_training
