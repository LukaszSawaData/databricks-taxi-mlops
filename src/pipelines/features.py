"""Lakeflow Spark Declarative Pipeline: raw trips -> tested clean trips -> train/score splits + feature table.

Expectations are the data tests: bad rows are dropped (and counted in the pipeline UI),
and a broken feature table fails the update before any model is trained on it.
"""

from pyspark import pipelines as dp
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.active()

MAX_ROWS = int(spark.conf.get("taxi.max_rows", "3000"))  # 0 = all rows
SPLIT_DATE = spark.conf.get("taxi.split_date", "2016-02-15")


@dp.materialized_view(comment="Deterministic sample of samples.nyctaxi.trips (small in dev).")
def trips_raw():
    df = spark.read.table("samples.nyctaxi.trips").withColumn(
        "trip_id",
        F.xxhash64("tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance", "fare_amount"),
    )
    if MAX_ROWS > 0:
        df = df.orderBy("trip_id").limit(MAX_ROWS)
    return df


@dp.materialized_view(comment="Validated trips with request-time features.")
@dp.expect_or_drop("valid_fare", "fare_amount BETWEEN 2.5 AND 200")
@dp.expect_or_drop("valid_distance", "trip_distance BETWEEN 0.1 AND 100")
@dp.expect_or_drop("has_zip", "pickup_zip IS NOT NULL")
@dp.expect("dropoff_after_pickup", "tpep_dropoff_datetime > tpep_pickup_datetime")
def trips_clean():
    return spark.read.table("trips_raw").select(
        "trip_id",
        F.col("tpep_pickup_datetime").alias("pickup_ts"),
        "tpep_dropoff_datetime",
        F.col("trip_distance").cast("double").alias("trip_distance"),
        F.hour("tpep_pickup_datetime").cast("double").alias("pickup_hour"),
        F.dayofweek("tpep_pickup_datetime").cast("double").alias("pickup_dow"),
        F.col("pickup_zip").cast("int").alias("pickup_zip"),
        F.col("fare_amount").cast("double").alias("fare_amount"),
    )


@dp.materialized_view(comment="Training period (before split_date).")
def trips_train():
    return spark.read.table("trips_clean").where(F.col("pickup_ts") < F.lit(SPLIT_DATE))


@dp.materialized_view(comment="'New' trips for batch scoring and monitoring (from split_date).")
def trips_scoring():
    return spark.read.table("trips_clean").where(F.col("pickup_ts") >= F.lit(SPLIT_DATE))


# Feature table = UC table with a primary key. Computed only from the training period (no leakage).
@dp.materialized_view(
    comment="Feature Store table: pickup zip aggregates. Lookup key: pickup_zip.",
    schema="""
        pickup_zip INT NOT NULL,
        zip_trip_count BIGINT,
        zip_avg_fare DOUBLE,
        zip_avg_fare_per_mile DOUBLE,
        CONSTRAINT pickup_zip_features_pk PRIMARY KEY (pickup_zip)
    """,
)
@dp.expect_or_fail("positive_count", "zip_trip_count > 0")
@dp.expect_or_fail("sane_avg_fare", "zip_avg_fare BETWEEN 2.5 AND 200")
def pickup_zip_features():
    return (
        spark.read.table("trips_train")
        .groupBy("pickup_zip")
        .agg(
            F.count("*").alias("zip_trip_count"),
            F.avg("fare_amount").alias("zip_avg_fare"),
            F.avg(F.col("fare_amount") / F.col("trip_distance")).alias("zip_avg_fare_per_mile"),
        )
    )
