import java.util.Properties

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.{broadcast, col, dayofmonth, dayofweek, hour, month, year}

/**
 * Loads the validated trips into the PostgreSQL star schema.
 *
 * dim_zone comes from the TLC zone lookup CSV. dim_datetime holds every
 * distinct pickup and dropoff timestamp (24.3M rows for 2023). fact_trip is
 * built by joining the trips with dim_datetime to get the surrogate keys.
 *
 * Both dimension writes skip timestamps/zones that already exist, so the job
 * can be restarted after a failure. fact_trip is append-only: to reload from
 * scratch, recreate the database (docker compose down -v).
 */
object Ingestor {

  private def readTable(spark: SparkSession, jdbcUrl: String, props: Properties, table: String): DataFrame =
    spark.read.format("jdbc")
      .option("url", jdbcUrl)
      .option("dbtable", table)
      .option("user", props.getProperty("user"))
      .option("password", props.getProperty("password"))
      .option("driver", "org.postgresql.Driver")
      .load()

  def loadZones(spark: SparkSession, jdbcUrl: String, props: Properties): Unit = {
    val csvPath = sys.env.getOrElse("ZONE_LOOKUP_CSV", "../../data/external/taxi_zone_lookup.csv")

    val zones = spark.read
      .option("header", "true")
      .option("inferSchema", "true")
      .csv(csvPath)
      .select(
        col("LocationID").as("zone_id"),
        col("Borough").as("borough"),
        col("Zone").as("zone_name")
      )

    val existing = readTable(spark, jdbcUrl, props, "dim_zone").select("zone_id")
    val newZones = zones.join(existing, Seq("zone_id"), "left_anti")

    newZones.write.mode("append").jdbc(jdbcUrl, "dim_zone", props)
    println(s"  dim_zone: ${newZones.count()} new zones")
  }

  def ingest(spark: SparkSession, jdbcUrl: String, props: Properties): Unit = {
    val validatedBucket = sys.env.getOrElse("VALIDATED_BUCKET", "nyc-validated")
    val yearValue       = sys.env.getOrElse("YEAR", "2023")

    val basePath = s"s3a://$validatedBucket/$yearValue/"
    println(s"  reading $basePath")
    val trips = spark.read.parquet(basePath)
    println(f"  ${trips.count()}%,d validated trips")

    // Every distinct pickup or dropoff timestamp becomes a dim_datetime row.
    val timestamps = trips
      .select(col("tpep_pickup_datetime").as("full_timestamp"))
      .union(trips.select(col("tpep_dropoff_datetime").as("full_timestamp")))
      .filter(col("full_timestamp").isNotNull)
      .distinct()

    val existingTimestamps = readTable(spark, jdbcUrl, props, "dim_datetime").select("full_timestamp")
    val newTimestamps      = timestamps.join(existingTimestamps, Seq("full_timestamp"), "left_anti")

    val dimDatetime = newTimestamps
      .withColumn("year", year(col("full_timestamp")))
      .withColumn("month", month(col("full_timestamp")))
      .withColumn("day", dayofmonth(col("full_timestamp")))
      .withColumn("hour", hour(col("full_timestamp")))
      .withColumn("day_of_week", dayofweek(col("full_timestamp")))
      .withColumn("is_weekend", col("day_of_week").isin(1, 7))

    println("  writing dim_datetime")
    dimDatetime.write.mode("append").jdbc(jdbcUrl, "dim_datetime", props)

    // Read the dimension back to get the generated surrogate keys. The table is
    // large (24M rows) but it fits in the 16g heap, and broadcasting it is much
    // cheaper than shuffling the 36M trips twice.
    val dimDatetimePg = readTable(spark, jdbcUrl, props, "dim_datetime")
      .select("datetime_id", "full_timestamp")
    println(f"  ${dimDatetimePg.count()}%,d rows in dim_datetime")

    val dimPickup = broadcast(dimDatetimePg
      .withColumnRenamed("datetime_id", "pickup_datetime_id")
      .alias("pickup"))

    val dimDropoff = broadcast(dimDatetimePg
      .withColumnRenamed("datetime_id", "dropoff_datetime_id")
      .alias("dropoff"))

    val normalized = trips
      .withColumn("VendorID", col("VendorID").cast("long").cast("int"))
      .withColumn("RatecodeID", col("RatecodeID").cast("long").cast("int"))
      .withColumn("payment_type", col("payment_type").cast("long").cast("int"))
      .withColumn("tpep_pickup_datetime", col("tpep_pickup_datetime").cast("timestamp"))
      .withColumn("tpep_dropoff_datetime", col("tpep_dropoff_datetime").cast("timestamp"))

    val fact = normalized
      .join(dimPickup, normalized("tpep_pickup_datetime") === dimPickup("full_timestamp"), "left")
      .join(dimDropoff, normalized("tpep_dropoff_datetime") === dimDropoff("full_timestamp"), "left")
      .select(
        col("pickup.pickup_datetime_id"),
        col("dropoff.dropoff_datetime_id"),
        col("PULocationID").as("pickup_zone_id"),
        col("DOLocationID").as("dropoff_zone_id"),
        col("VendorID").as("vendor_id"),
        col("RatecodeID").as("ratecode_id"),
        col("payment_type").as("payment_type_id"),
        col("passenger_count"),
        col("trip_distance"),
        col("fare_amount"),
        col("extra"),
        col("mta_tax"),
        col("tip_amount"),
        col("tolls_amount"),
        col("improvement_surcharge"),
        col("congestion_surcharge"),
        col("airport_fee"),
        col("total_amount")
      )

    // 8 partitions = 8 parallel JDBC connections, which was the sweet spot on
    // our server (about 1.5M rows per minute).
    println("  writing fact_trip")
    fact.repartition(8).write.mode("append").jdbc(jdbcUrl, "fact_trip", props)
    println("  fact_trip written")
  }
}
