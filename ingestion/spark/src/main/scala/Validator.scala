import org.apache.spark.sql.{DataFrame, SparkSession, functions => F}
import org.apache.spark.sql.types._

/**
 * Reads the twelve monthly files of one year from the raw bucket, normalises
 * them to a single schema and keeps only the rows that pass the business
 * rules. Each month is written to its own folder with overwrite, so the step
 * can be re-run without duplicating data.
 */
object Validator {

  val vendorIds         = Seq(1, 2, 6, 7)
  val rateCodes         = Seq(1, 2, 3, 4, 5, 6, 99)
  val storeAndFwdFlags  = Seq("Y", "N")
  val paymentTypes      = Seq(0, 1, 2, 3, 4, 5, 6)

  val targetSchema: StructType = StructType(Seq(
    StructField("VendorID", IntegerType, nullable = true),
    StructField("tpep_pickup_datetime", TimestampType, nullable = true),
    StructField("tpep_dropoff_datetime", TimestampType, nullable = true),
    StructField("passenger_count", IntegerType, nullable = true),
    StructField("trip_distance", DoubleType, nullable = true),
    StructField("RatecodeID", IntegerType, nullable = true),
    StructField("store_and_fwd_flag", StringType, nullable = true),
    StructField("PULocationID", LongType, nullable = true),
    StructField("DOLocationID", LongType, nullable = true),
    StructField("payment_type", IntegerType, nullable = true),
    StructField("fare_amount", DoubleType, nullable = true),
    StructField("extra", DoubleType, nullable = true),
    StructField("mta_tax", DoubleType, nullable = true),
    StructField("tip_amount", DoubleType, nullable = true),
    StructField("tolls_amount", DoubleType, nullable = true),
    StructField("improvement_surcharge", DoubleType, nullable = true),
    StructField("total_amount", DoubleType, nullable = true),
    StructField("congestion_surcharge", DoubleType, nullable = true),
    StructField("airport_fee", DoubleType, nullable = true)
  ))

  /**
   * The monthly files do not all share the same schema: some months spell the
   * airport fee column "Airport_fee", and the integer columns alternate between
   * int and long. Rename, cast and add missing columns as null.
   */
  def normalizeSchema(df: DataFrame): DataFrame = {
    var normalized = df

    if (df.columns.contains("Airport_fee") && !df.columns.contains("airport_fee")) {
      normalized = normalized.withColumnRenamed("Airport_fee", "airport_fee")
    }

    targetSchema.fields.foreach { field =>
      if (normalized.columns.contains(field.name)) {
        normalized = normalized.withColumn(field.name, F.col(field.name).cast(field.dataType))
      } else {
        normalized = normalized.withColumn(field.name, F.lit(null).cast(field.dataType))
      }
    }

    normalized.select(targetSchema.fieldNames.map(F.col): _*)
  }

  def applyRules(df: DataFrame): DataFrame = {
    df
      .filter(F.col("passenger_count") >= 0)
      .filter(F.col("trip_distance") >= 0)
      .filter(F.col("fare_amount") >= 0)
      .filter(F.col("extra") >= 0)
      .filter(F.col("mta_tax") >= 0)
      .filter(F.col("tip_amount") >= 0)
      .filter(F.col("tolls_amount") >= 0)
      .filter(F.col("improvement_surcharge") >= 0)
      .filter(F.col("total_amount") >= 0)
      .filter(F.col("congestion_surcharge") >= 0)
      .filter(F.col("airport_fee") >= 0)
      .filter(F.col("VendorID").isin(vendorIds: _*))
      .filter(F.col("RatecodeID").isin(rateCodes: _*))
      .filter(F.col("store_and_fwd_flag").isin(storeAndFwdFlags: _*))
      .filter(F.col("payment_type").isin(paymentTypes: _*))
      .filter(F.col("tpep_dropoff_datetime") >= F.col("tpep_pickup_datetime"))
  }

  def validate(spark: SparkSession): Unit = {
    val rawBucket       = sys.env.getOrElse("RAW_BUCKET", "nyc-raw")
    val validatedBucket = sys.env.getOrElse("VALIDATED_BUCKET", "nyc-validated")
    val year            = sys.env.getOrElse("YEAR", "2023").toInt

    (1 to 12).foreach { month =>
      val monthStr = f"$month%02d"
      val input    = s"s3a://$rawBucket/$year/yellow_tripdata_$year-$monthStr.parquet"
      val output   = s"s3a://$validatedBucket/$year/month=$monthStr/"

      println(s"Reading $input")
      val raw   = spark.read.parquet(input)
      val clean = applyRules(normalizeSchema(raw))

      val rawCount   = raw.count()
      val cleanCount = clean.count()
      println(f"  $rawCount%,d rows read, $cleanCount%,d kept (${100.0 * cleanCount / rawCount}%.1f%%)")

      clean.write.mode("overwrite").parquet(output)
      println(s"  written to $output")
    }
  }
}
