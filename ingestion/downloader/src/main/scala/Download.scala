import io.minio.{BucketExistsArgs, MakeBucketArgs, MinioClient, PutObjectArgs}
import java.net.URL

/**
 * Streams the monthly NYC TLC yellow-taxi Parquet files straight from the
 * TLC CDN into a MinIO bucket. Nothing is written to the local disk: the HTTP
 * stream is handed to the MinIO client, which uploads it in 10 MB parts.
 *
 * Configuration comes from the environment (see .env.example):
 *   MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, RAW_BUCKET, YEARS
 */
object Download extends App {

  val endpoint  = sys.env.getOrElse("MINIO_ENDPOINT", "http://localhost:9000")
  val accessKey = sys.env.getOrElse("MINIO_ROOT_USER", "minio")
  val secretKey = sys.env.getOrElse("MINIO_ROOT_PASSWORD", "")
  val bucket    = sys.env.getOrElse("RAW_BUCKET", "nyc-raw")
  val validated = sys.env.getOrElse("VALIDATED_BUCKET", "nyc-validated")
  val years     = sys.env.getOrElse("YEARS", "2023").split(",").map(_.trim.toInt)

  val baseUrl = "https://d37ci6vzurychx.cloudfront.net/trip-data"

  val client = MinioClient.builder()
    .endpoint(endpoint)
    .credentials(accessKey, secretKey)
    .build()

  // Spark's s3a connector does not create buckets, so both are created here.
  Seq(bucket, validated).foreach { name =>
    if (!client.bucketExists(BucketExistsArgs.builder().bucket(name).build())) {
      client.makeBucket(MakeBucketArgs.builder().bucket(name).build())
      println(s"Created bucket $name")
    }
  }

  def uploadYear(year: Int): Unit = {
    for (month <- 1 to 12) {
      val monthStr   = f"$month%02d"
      val objectName = s"$year/yellow_tripdata_$year-$monthStr.parquet"
      val url        = s"$baseUrl/yellow_tripdata_$year-$monthStr.parquet"

      println(s"$url -> s3a://$bucket/$objectName")

      val in = new URL(url).openStream()
      try {
        client.putObject(
          PutObjectArgs.builder()
            .bucket(bucket)
            .`object`(objectName)
            .stream(in, -1, 10 * 1024 * 1024)
            .contentType("application/octet-stream")
            .build()
        )
      } finally {
        in.close()
      }
    }
  }

  years.foreach { year =>
    println(s"Downloading $year (12 files)")
    uploadYear(year)
  }

  println("Done.")
}
