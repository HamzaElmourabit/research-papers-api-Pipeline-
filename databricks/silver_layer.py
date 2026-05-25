from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder.appName("arxiv_silver").getOrCreate()

# 1. Charger Bronze
BRONZE_PATH = "/mnt/data/papers_bronze_parquet"
df = spark.read.format("parquet").load(BRONZE_PATH)

print("🧹 SILVER: Cleaning Bronze layer")

# 2. Dropduplicates
silver_df = df.dropDuplicates(["arxiv_id"])
print(f"✅ Dropped duplicates: {df.count()} → {silver_df.count()}")

# 3. Trim text columns
silver_df = silver_df \
    .withColumn("title", trim(col("title"))) \
    .withColumn("abstract", trim(col("abstract")))

# 4. Convert dates to TIMESTAMP
silver_df = silver_df \
    .withColumn("published_date", to_timestamp(col("published_date"))) \
    .withColumn("updated_date", to_timestamp(col("updated_date")))

# 5. Extract year from published_date
silver_df = silver_df \
    .withColumn("publication_year", year(col("published_date")))

# 6. Calculate metrics
silver_df = silver_df \
    .withColumn("title_length", length(col("title"))) \
    .withColumn("abstract_length", length(col("abstract"))) \
    .withColumn("authors_count", size(col("authors"))) \
    .withColumn("categories_count", size(col("categories")))

# 7. Explode authors (one row per author)
silver_df = silver_df.withColumn("author", explode(col("authors")))

# 8. Afficher stats
print(f"\n📊 SILVER Stats:")
print(f"  • Total records: {silver_df.count()}")
print(f"  • Unique papers: {silver_df.select('arxiv_id').distinct().count()}")
silver_df.select("arxiv_id", "title", "author", "publication_year").show(10)

# 9. Sauvegarder Silver
SILVER_PATH = "/mnt/data/papers_silver_parquet"
silver_df.write.mode("overwrite") \
    .format("parquet") \
    .save(SILVER_PATH)

print(f"\n✅ SILVER: {silver_df.count()} rows saved")
