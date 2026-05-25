from pyspark.sql import SparkSession
from pyspark.sql.functions import col, countDistinct, sum as _sum, explode, desc

spark = SparkSession.builder.appName("arxiv_graph").getOrCreate()

SILVER_PATH = "/mnt/data/papers_silver_parquet"
GRAPH_PATH = "/mnt/data/papers_graph"

print("🔗 GRAPH: Loading Silver layer for graph analytics")
silver_df = spark.read.format("parquet").load(SILVER_PATH)

print(f"✔ Loaded Silver layer from {SILVER_PATH}")
print("   Columns:", silver_df.columns)

# ----------------------------------------
# Author co-authorship graph
# ----------------------------------------
print("\n🔗 GRAPH: Building co-authorship edges")
authors_by_paper = silver_df.select("arxiv_id", "author").distinct()

coauthor_pairs = authors_by_paper.alias("a") \
    .join(authors_by_paper.alias("b"), on="arxiv_id") \
    .where(col("a.author") < col("b.author")) \
    .select(
        col("a.author").alias("author1"),
        col("b.author").alias("author2"),
        col("a.arxiv_id").alias("arxiv_id")
    )

author_coauthor_edges = coauthor_pairs \
    .groupBy("author1", "author2") \
    .agg(countDistinct("arxiv_id").alias("shared_papers")) \
    .orderBy(desc("shared_papers"), "author1", "author2")

print("✅ Co-authorship edges computed")
author_coauthor_edges.show(10, truncate=False)

# Save co-authorship graph edges
author_coauthor_edges.write.mode("overwrite").parquet(f"{GRAPH_PATH}/author_coauthor_edges")
print(f"✅ Saved author co-authorship edges to {GRAPH_PATH}/author_coauthor_edges")

# ----------------------------------------
# Author network summary
# ----------------------------------------
print("\n🔗 GRAPH: Computing author network summary")

author_edges_a = author_coauthor_edges.select(
    col("author1").alias("author"),
    col("author2").alias("neighbor"),
    col("shared_papers")
)
author_edges_b = author_coauthor_edges.select(
    col("author2").alias("author"),
    col("author1").alias("neighbor"),
    col("shared_papers")
)

author_network = author_edges_a.union(author_edges_b)

author_network_summary = author_network.groupBy("author") \
    .agg(
        countDistinct("neighbor").alias("num_collaborators"),
        _sum("shared_papers").alias("collaboration_weight")
    ) \
    .orderBy(desc("num_collaborators"), desc("collaboration_weight"))

print("✅ Author network summary computed")
author_network_summary.show(10, truncate=False)

author_network_summary.write.mode("overwrite").parquet(f"{GRAPH_PATH}/author_network_summary")
print(f"✅ Saved author network summary to {GRAPH_PATH}/author_network_summary")

# ----------------------------------------
# Category trends for graph analytics
# ----------------------------------------
print("\n🔗 GRAPH: Building category trends")

category_trends = silver_df \
    .select("arxiv_id", "publication_year", explode("categories").alias("category")) \
    .distinct() \
    .groupBy("category", "publication_year") \
    .agg(countDistinct("arxiv_id").alias("num_papers")) \
    .orderBy("category", "publication_year")

print("✅ Category trends computed")
category_trends.show(10, truncate=False)

category_trends.write.mode("overwrite").parquet(f"{GRAPH_PATH}/category_trends")
print(f"✅ Saved category trends to {GRAPH_PATH}/category_trends")

print("\n✅ GRAPH: Graph analytics stage complete")
print(f"   • author_coauthor_edges → {GRAPH_PATH}/author_coauthor_edges")
print(f"   • author_network_summary → {GRAPH_PATH}/author_network_summary")
print(f"   • category_trends → {GRAPH_PATH}/category_trends")
