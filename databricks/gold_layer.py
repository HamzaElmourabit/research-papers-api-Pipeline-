from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("arxiv_gold").getOrCreate()

# 1. Charger Silver
SILVER_PATH = "/mnt/data/papers_silver_parquet"
silver_df = spark.read.format("parquet").load(SILVER_PATH)

print("✨ GOLD: Creating analytics tables")

# ═════════════════════════════════════════════════
# 2. TABLE 1: Papers per Year
# ═════════════════════════════════════════════════
papers_per_year = silver_df \
    .select("arxiv_id", "publication_year") \
    .distinct() \
    .groupBy("publication_year") \
    .agg(count("*").alias("num_papers")) \
    .orderBy("publication_year")

print("\n📅 PAPERS PER YEAR:")
papers_per_year.show()

# ═════════════════════════════════════════════════
# 3. TABLE 2: Papers per Category
# ═════════════════════════════════════════════════
df_cat = silver_df.select("arxiv_id", explode("categories").alias("category")) \
    .distinct()

papers_per_category = df_cat \
    .groupBy("category") \
    .agg(count("*").alias("num_papers")) \
    .orderBy(desc("num_papers"))

print("\n📂 PAPERS PER CATEGORY:")
papers_per_category.show()

# ═════════════════════════════════════════════════
# 4. TABLE 3: Top Authors
# ═════════════════════════════════════════════════
top_authors = silver_df \
    .groupBy("author") \
    .agg(count("*").alias("num_papers")) \
    .filter(col("author").isNotNull()) \
    .orderBy(desc("num_papers")) \
    .limit(5)

print("\n👥 TOP 5 AUTHORS:")
top_authors.show()

# ═════════════════════════════════════════════════
# 5. TABLE 4: Research Trends
# ═════════════════════════════════════════════════
df_cat_year = silver_df.select("arxiv_id", "publication_year", explode("categories").alias("category")) \
    .distinct()

cat_growth = df_cat_year \
    .groupBy("category", "publication_year") \
    .agg(count("*").alias("num_papers")) \
    .orderBy("category", "publication_year")

window = Window.partitionBy("category").orderBy("publication_year")
cat_growth = cat_growth \
    .withColumn("prev_year_papers", lag("num_papers").over(window)) \
    .withColumn("growth_rate", \
                round((col("num_papers") - col("prev_year_papers")) / col("prev_year_papers") * 100, 2))

print("\n📈 RESEARCH TRENDS (Growth Rate by Category & Year):")
cat_growth.show()

# ═════════════════════════════════════════════════
# 6. Sauvegarder toutes les tables Gold
# ═════════════════════════════════════════════════
GOLD_PATH = "/mnt/data/papers_gold"

papers_per_year.write.mode("overwrite").parquet(f"{GOLD_PATH}/papers_per_year")
papers_per_category.write.mode("overwrite").parquet(f"{GOLD_PATH}/papers_per_category")
top_authors.write.mode("overwrite").parquet(f"{GOLD_PATH}/top_authors")
cat_growth.write.mode("overwrite").parquet(f"{GOLD_PATH}/research_trends")

print(f"\n✅ GOLD: 4 tables saved to {GOLD_PATH}")
