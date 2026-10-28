ThisBuild / version := "0.1.0"

ThisBuild / scalaVersion := "2.13.17"

lazy val root = (project in file("."))
  .settings(
    name := "ingestion",
    fork := true,
    javaOptions ++= Seq(
      // Spark 3.5 on a Java 17 JVM needs these module opens.
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
      "--add-opens=java.base/java.io=ALL-UNNAMED",
      "--add-opens=java.base/java.net=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED",
      "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
      "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED",
      // The first run with the default 4g heap died while joining the 24M-row
      // datetime dimension. 16g (on a 30 GB server) with G1 was stable.
      "-Xmx16g",
      "-Xms8g",
      "-XX:+UseG1GC",
      "-XX:MaxGCPauseMillis=200"
    ),
    // Fat jar for spark-submit (used by the Airflow DAG).
    assembly / assemblyJarName := "ingestion-assembly.jar",
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", "services", _*) => MergeStrategy.filterDistinctLines
      case PathList("META-INF", _*)             => MergeStrategy.discard
      case "module-info.class"                  => MergeStrategy.discard
      case _                                    => MergeStrategy.first
    }
  )

libraryDependencies += "org.apache.spark" %% "spark-core" % "3.5.5"
libraryDependencies += "org.apache.spark" %% "spark-sql" % "3.5.5"
libraryDependencies += "org.postgresql" % "postgresql" % "42.7.1"
libraryDependencies += "org.apache.hadoop" % "hadoop-aws" % "3.3.4"
libraryDependencies += "com.amazonaws" % "aws-java-sdk-bundle" % "1.12.262"
