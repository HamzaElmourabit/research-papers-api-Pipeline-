import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, md5, concat_ws, lit

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "cassandra")
CASSANDRA_PORT = os.getenv("CASSANDRA_PORT", "9042")

spark = SparkSession.builder \
    .appName("arxiv_bronze") \
    .config("spark.cassandra.connection.host", CASSANDRA_HOST) \
    .config("spark.cassandra.connection.port", CASSANDRA_PORT) \
    .getOrCreate()

# 1. Charger depuis Cassandra
BRONZE_PATH = "/mnt/data/papers_bronze_parquet"
df = spark.read \
    .format("org.apache.spark.sql.cassandra") \
    .options(keyspace="arxiv", table="papers_raw") \
    .load()

print("📊 BRONZE: Raw data from Cassandra")
df.printSchema()

print(f"\n📈 Total rows: {df.count()}")
df.show(5, truncate=False)

# 2. Ajouter metadata columns
bronze_df = df \
    .withColumn("_ingestion_timestamp", current_timestamp()) \
    .withColumn("_source_system", lit("cassandra_arxiv")) \
    .withColumn("_record_hash", md5(concat_ws("", df.arxiv_id, df.title)))

# 3. Sauvegarder Bronze
bronze_df.write.mode("overwrite") \
    .format("parquet") \
    .save(BRONZE_PATH)

print(f"\n✅ BRONZE: {bronze_df.count()} rows saved to {BRONZE_PATH}")
