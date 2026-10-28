# NYC Taxi Pipeline

One year of New York yellow-taxi trips (2023) from the TLC open data, validated with Spark,
loaded into a PostgreSQL star schema, explored in Metabase and used to train a fare
prediction model served by a Streamlit app; an Airflow DAG chains the steps and everything
runs in Docker Compose. Big Data module project, CY Tech, ING3, 2025-2026, team of three:
Haroun Joudi, Amine Filali, Mouad Ouad. I ran the stack on our server, wrote the Spark
validation and ingestion job and the warehouse schema, tuned the load until it held in
memory, built the Metabase dashboard and wired the fare-prediction service and the Airflow
DAG into the stack; Amine and Mouad worked on the fare-prediction model and the DAG.

```
TLC CDN (12 monthly Parquet files, 2023)
  -> ingestion/downloader   Scala + MinIO SDK, streamed into MinIO nyc-raw/2023/
  -> ingestion/spark        Spark 3.5 (Scala): Validator -> MinIO nyc-validated/2023/ (36.6M rows)
                            then Ingestor -> PostgreSQL star schema (warehouse/*.sql)
  -> Metabase (:3000)       four charts, SQL in dashboard/queries.sql
  -> ml_service/            200k stratified sample -> Random Forest -> Streamlit app (:8501)
  orchestration/dags/  Airflow: validate_and_load -> check_warehouse -> ml_preprocessing -> ml_training
```

## Validation and warehouse

The monthly files do not share one schema (`Airport_fee` vs `airport_fee`, int vs long
columns), so the validator first casts every month to one schema, then keeps a row only if
all amounts, the passenger count and the distance are >= 0, vendor, rate code, payment type
and store-and-forward flag are in the TLC code lists, and dropoff is not before pickup. For
2023 that is 38,407,504 rows read and 36.6M kept (95 %), 3 % to 7 % rejected per month.

PostgreSQL 16 holds `fact_trip` (36,623,337 rows, one per trip with all the amounts) and
five dimensions: `dim_datetime` (24,296,188 distinct pickup and dropoff timestamps),
`dim_zone` (265), `dim_vendor` (4), `dim_ratecode` (7), `dim_payment_type` (7); foreign
keys everywhere, indexes on the fact keys, about 11 GB on disk. The expensive part of the
load is the join of the trips with `dim_datetime`, almost as large as the facts: with a
4 GB heap it died after about 7M rows. It holds with a 16 GB G1 heap (`javaOptions` in
`ingestion/spark/build.sbt`), an explicit `broadcast` of the dimension and the fact table
written through 8 partitions (8 parallel JDBC connections): about 37 minutes for the full
load on a 30 GB server, roughly 1.5M rows per minute.

![Metabase dashboard](docs/screenshots/metabase_dashboard.png)

Four Metabase questions: trips per day (around 100k, weekly rhythm clearly visible), trips
per pickup borough (about 32M of the 36.6M in Manhattan, Queens second because of the two
airports), average fare per hour (a peak around 5 am at about $28, airport runs, then $17
to $21 the rest of the day) and payment type (81.5 % card, 17.2 % cash).

## Fare prediction

`ml_service/` predicts `total_amount` from seven features: distance, passenger count,
pickup and dropoff zone ids, hour, day of week, weekend flag. It reads the validated
Parquet from MinIO, drops the obvious garbage (amount <= 0 or >= 500, distance <= 0 or
>= 100, no passengers), takes a 200k-row sample stratified by price band (the ML container
has 4 GB), splits 80/20 and fits a `RandomForestRegressor` in a scikit-learn pipeline. On
the 20 % held-out part of the sample: RMSE 6.56, MAE 3.50, R² 0.91, train RMSE 5.89 (the
target set by the subject was RMSE < 10). Those numbers come from 100 trees with depth 15;
`train.py` now uses 250 trees, depth 12 and at least 5 samples per leaf, so expect a figure
in the same range. The 5-fold cross-validation in `train.py` runs on the training split only.

![Streamlit app](docs/screenshots/streamlit_app.png)

## Running it

Docker with about 20 GB free, plus a JDK 17 and sbt for the Scala jobs. The Spark job runs
in local mode with a 16 GB heap; lower `-Xmx` in `ingestion/spark/build.sbt` on a smaller machine.

```bash
cp .env.example .env             # set the passwords and PROJECT_DIR
docker compose up -d --build     # Spark, MinIO, PostgreSQL (schema created at start), Metabase, ML service, Airflow
set -a; source .env; set +a
(cd ingestion/downloader && sbt run)     # 1. 2023 files into MinIO (about 1 GB)
(cd ingestion/spark && sbt run)          # 2. validate + load the warehouse (37 min on a 30 GB server)
docker compose run --rm ml-service python src/preprocessing.py   # 3. sample + clean
docker compose run --rm ml-service python src/train.py           #    train, then open http://localhost:8501
(cd ingestion/spark && sbt assembly)     # 4. optional: fat jar for the DAG, then trigger it at http://localhost:8080
```

Metabase (http://localhost:3000) needs a one-time setup: create the admin account, add the
`taxi` database on host `postgres`, then paste the queries from `dashboard/queries.sql`.
Spark UI on 8081, MinIO console on 9001. ML unit tests: `pytest ml_service/tests`.

## Known limitations

- The DAG (four `DockerOperator` tasks, no schedule, triggered by hand) parses and starts
  but has not been run end to end; the warehouse and the model come from the manual runs.
- `dim_datetime` at second granularity is a design mistake: 24M rows for 36M facts and a
  heavy join. A date dimension plus an hour column, with timestamps in the fact table, would do.
- The daily chart has two gaps (first days of January, early October) that the per-month
  validation counts do not show, so the rows went missing in the warehouse load.
- The model treats zone ids as numbers and predicts `total_amount` (tips included) on a
  random split; target-encoded zones, `fare_amount` and a time-based split would be fairer.
