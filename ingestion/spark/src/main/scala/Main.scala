import org.apache.spark.sql.SparkSession

/**
 * Validates the raw 2023 trips stored in MinIO and loads the result into the
 * PostgreSQL star schema. Two steps:
 *
 *   1. Validator: read each monthly Parquet file, normalise the schema, drop
 *      rows that fail the business rules, write the clean rows back to MinIO.
 *   2. Ingestor: build the dimension tables, then join the clean rows with the
 *      dimensions and write the fact table.
 *
 * Connection settings come from the environment (see .env.example). When
 * started with `sbt run` the job runs in local mode; spark-submit sets the
 * master itself.
 */
object Main extends App {

  val minioEndpoint = sys.env.getOrElse("MINIO_ENDPOINT", "http://localhost:9000")
  val minioUser     = sys.env.getOrElse("MINIO_ROOT_USER", "minio")
  val minioPassword = sys.env.getOrElse("MINIO_ROOT_PASSWORD", "")

  val pgHost     = sys.env.getOrElse("POSTGRES_HOST", "localhost")
  val pgPort     = sys.env.getOrElse("POSTGRES_PORT", "5432")
  val pgDb       = sys.env.getOrElse("POSTGRES_DB", "taxi")
  val pgUser     = sys.env.getOrElse("POSTGRES_USER", "postgres")
  val pgPassword = sys.env.getOrElse("POSTGRES_PASSWORD", "")

  val builder = SparkSession.builder()
    .appName("NYC Taxi validation and ingestion")
    .config("fs.s3a.access.key", minioUser)
    .config("fs.s3a.secret.key", minioPassword)
    .config("fs.s3a.endpoint", minioEndpoint)
    .config("fs.s3a.path.style.access", "true")
    .config("fs.s3a.connection.ssl.enable", "false")
    .config("fs.s3a.attempts.maximum", "1")
    .config("fs.s3a.connection.establish.timeout", "6000")
    .config("fs.s3a.connection.timeout", "5000")

  if (!sys.props.contains("spark.master")) {
    builder.master(sys.env.getOrElse("SPARK_MASTER_URL", "local[*]"))
  }

  val spark = builder.getOrCreate()
  spark.sparkContext.setLogLevel("WARN")

  val jdbcUrl   = s"jdbc:postgresql://$pgHost:$pgPort/$pgDb"
  val jdbcProps = new java.util.Properties()
  jdbcProps.setProperty("user", pgUser)
  jdbcProps.setProperty("password", pgPassword)
  jdbcProps.setProperty("driver", "org.postgresql.Driver")

  println("[1/3] Validating raw data")
  Validator.validate(spark)

  println("[2/3] Loading the taxi zone lookup into dim_zone")
  Ingestor.loadZones(spark, jdbcUrl, jdbcProps)

  println("[3/3] Building dim_datetime and fact_trip")
  Ingestor.ingest(spark, jdbcUrl, jdbcProps)

  println("Ingestion finished.")
  spark.stop()
}
