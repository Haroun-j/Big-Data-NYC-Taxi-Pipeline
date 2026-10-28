ThisBuild / version := "0.1.0"

ThisBuild / scalaVersion := "2.13.17"

lazy val root = (project in file("."))
  .settings(
    name := "downloader"
  )

// The downloader only talks to MinIO; Spark is not needed here.
libraryDependencies += "io.minio" % "minio" % "8.5.7"
