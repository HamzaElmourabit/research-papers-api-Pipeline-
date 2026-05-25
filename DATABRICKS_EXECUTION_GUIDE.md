# 🚀 GUIDE D'EXÉCUTION: DATABRICKS PIPELINE ELT

**Objectif:** Exécuter les 3 fichiers databricks/ en séquence
- ✅ bronze_layer.py → Charger depuis Cassandra
- ✅ silver_layer.py → Nettoyer et transformer
- ✅ gold_layer.py → Créer tables analytiques

---

## 📋 PRÉREQUIS

### 1. Cassandra doit être en cours d'exécution

```bash
# Vérifier Cassandra
docker-compose ps

# OUTPUT:
# NAME                COMMAND                  SERVICE             STATUS
# cassandra           "..."                    cassandra           Up 2 minutes

# Tester connexion
docker exec -it cassandra cqlsh
SELECT COUNT(*) FROM arxiv.papers_raw;
# ✅ Result: 18 rows
```

### 2. Databricks cluster/Spark local

**OPTION A: Databricks Cloud** (Recommandé)
- Créer cluster dans workspace Databricks
- Éditeur Notebooks

**OPTION B: Local Spark** (Développement)
```bash
# Installer PySpark localement
pip install pyspark==3.5.0

# Tester
python -c "import pyspark; print(pyspark.__version__)"
# Output: 3.5.0 ✅
```

### 3. Dépendances Python

```bash
# Depuis research_papers_api/
pip install -r requirements.txt

# OU installer manuellement
pip install pyspark==3.5.0
pip install cassandra-driver==3.29.0
pip install pandas==2.1.4
pip install numpy==1.24.3
```

---

## 🔧 STEP 1: BRONZE LAYER - CHARGER

### À exécuter: `databricks/bronze_layer.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, md5, concat_ws

# 1. Init Spark
spark = SparkSession.builder \
    .appName("arxiv_bronze") \
    .config("spark.cassandra.connection.host", "127.0.0.1") \
    .config("spark.cassandra.connection.port", "9042") \
    .getOrCreate()

# 2. Charger depuis Cassandra
df = spark.read \
    .format("org.apache.spark.sql.cassandra") \
    .options(keyspace="arxiv", table="papers_raw") \
    .load()

# 3. Vérifier schema
print("📊 BRONZE: Raw data from Cassandra")
df.printSchema()

# 4. Afficher 5 rows
print(f"\n📈 Total rows: {df.count()}")
df.show(5, truncate=False)

# 5. Ajouter metadata columns
bronze_df = df \
    .withColumn("_ingestion_timestamp", current_timestamp()) \
    .withColumn("_source_system", lit("cassandra_arxiv")) \
    .withColumn("_record_hash", md5(concat_ws("", df.arxiv_id, df.title)))

# 6. Sauvegarder Bronze
BRONZE_PATH = "/mnt/data/papers_bronze"
bronze_df.write.mode("overwrite") \
    .format("delta") \
    .save(BRONZE_PATH)

print(f"\n✅ BRONZE: {bronze_df.count()} rows saved to {BRONZE_PATH}")
```

### Expected Output

```
📊 BRONZE: Raw data from Cassandra
root
 |-- batch_id: string
 |-- arxiv_id: string
 |-- title: string
 |-- abstract: string
 |-- authors: array
 |-- categories: array
 |-- published_date: timestamp
 |-- updated_date: timestamp
 |-- pdf_url: string
 |-- json_metadata: string
 |-- ingestion_date: timestamp
 |-- processing_status: string
 |-- notes: string

📈 Total rows: 18
✅ BRONZE: 18 rows saved to /mnt/data/papers_bronze
```

### Troubleshooting

| Erreur | Solution |
|--------|----------|
| `No route to host 127.0.0.1:9042` | Cassandra pas en cours d'exécution → `docker-compose up -d` |
| `com.datastax.driver.core.exceptions.NoHostAvailableException` | Port 9042 fermé → `docker-compose up` |
| `org.apache.spark.sql.cassandra format not recognized` | Connector manquant → pip install pyspark[cassandra] |

---

## 🔧 STEP 2: SILVER LAYER - NETTOYER

### À exécuter: `databricks/silver_layer.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder.appName("arxiv_silver").getOrCreate()

# 1. Charger Bronze
BRONZE_PATH = "/mnt/data/papers_bronze"
df = spark.read.format("delta").load(BRONZE_PATH)

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
SILVER_PATH = "/mnt/data/papers_silver"
silver_df.write.mode("overwrite") \
    .format("delta") \
    .save(SILVER_PATH)

print(f"\n✅ SILVER: {silver_df.count()} rows saved")
```

### Expected Output

```
🧹 SILVER: Cleaning Bronze layer
✅ Dropped duplicates: 18 → 18

📊 SILVER Stats:
  • Total records: 50+ (après explode authors)
  • Unique papers: 18

+------------------+---------------------------+------------------+------------------+
|arxiv_id          |title                      |author            |publication_year  |
+------------------+---------------------------+------------------+------------------+
|2401.12345        |Deep Learning for Vision   |John Doe          |2024               |
|2401.12345        |Deep Learning for Vision   |Jane Smith        |2024               |
|2401.54321        |NLP Transformers           |Bob Johnson       |2024               |
...
```

---

## 🔧 STEP 3: GOLD LAYER - AGRÉGATIONS

### À exécuter: `databricks/gold_layer.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("arxiv_gold").getOrCreate()

# 1. Charger Silver
SILVER_PATH = "/mnt/data/papers_silver"
silver_df = spark.read.format("delta").load(SILVER_PATH)

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
    .withColumn("growth_rate", 
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
```

---

## 🔧 STEP 4: GRAPH ANALYTICS - RÉSEAUX D'AUTEURS

### À exécuter: `databricks/graph_layer.py`

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, countDistinct, sum as _sum, explode, desc

spark = SparkSession.builder.appName("arxiv_graph").getOrCreate()

SILVER_PATH = "/mnt/data/papers_silver_parquet"
GRAPH_PATH = "/mnt/data/papers_graph"

silver_df = spark.read.format("parquet").load(SILVER_PATH)

# 1. Co-authorship graph
coauthor_pairs = silver_df.select("arxiv_id", "author").distinct() \
    .alias("a") \
    .join(silver_df.select("arxiv_id", "author").distinct().alias("b"), on="arxiv_id") \
    .where(col("a.author") < col("b.author")) \
    .select(
        col("a.author").alias("author1"),
        col("b.author").alias("author2"),
        col("a.arxiv_id").alias("arxiv_id")
    )

author_coauthor_edges = coauthor_pairs.groupBy("author1", "author2") \
    .agg(countDistinct("arxiv_id").alias("shared_papers")) \
    .orderBy(desc("shared_papers"), "author1", "author2")

# 2. Author network summary

author_network = author_coauthor_edges.select(
    col("author1").alias("author"),
    col("author2").alias("neighbor"),
    col("shared_papers")
).union(
    author_coauthor_edges.select(
        col("author2").alias("author"),
        col("author1").alias("neighbor"),
        col("shared_papers")
    )
)

author_network_summary = author_network.groupBy("author") \
    .agg(
        countDistinct("neighbor").alias("num_collaborators"),
        _sum("shared_papers").alias("collaboration_weight")
    ) \
    .orderBy(desc("num_collaborators"), desc("collaboration_weight"))

# 3. Category trends for graphs
category_trends = silver_df \
    .select("arxiv_id", "publication_year", explode("categories").alias("category")) \
    .distinct() \
    .groupBy("category", "publication_year") \
    .agg(countDistinct("arxiv_id").alias("num_papers")) \
    .orderBy("category", "publication_year")

# 4. Save results
author_coauthor_edges.write.mode("overwrite").parquet(f"{GRAPH_PATH}/author_coauthor_edges")
author_network_summary.write.mode("overwrite").parquet(f"{GRAPH_PATH}/author_network_summary")
category_trends.write.mode("overwrite").parquet(f"{GRAPH_PATH}/category_trends")

print(f"✅ GRAPH: Saved graph analytics outputs to {GRAPH_PATH}")
```

### Expected Output

```
✨ GOLD: Creating analytics tables

📅 PAPERS PER YEAR:
+------------------+-----------+
|publication_year  |num_papers |
+------------------+-----------+
|2023              |2          |
|2024              |14         |
|2025              |2          |
+------------------+-----------+

📂 PAPERS PER CATEGORY:
+-----------+-----------+
|category   |num_papers |
+-----------+-----------+
|cs.LG      |8          |
|cs.AI      |6          |
|cs.CV      |5          |
|cs.CL      |3          |
|stat.ML    |2          |
+-----------+-----------+

👥 TOP 5 AUTHORS:
+------------------+-----------+
|author            |num_papers |
+------------------+-----------+
|John Doe          |3          |
|Jane Smith        |3          |
|Bob Johnson       |2          |
|Alice Williams    |2          |
|Charlie Brown     |1          |
+------------------+-----------+

📈 RESEARCH TRENDS:
+----------+------------------+-----------+------------------+
|category  |publication_year  |num_papers |growth_rate       |
+----------+------------------+-----------+------------------+
|cs.AI     |2023              |1          |null              |
|cs.AI     |2024              |5          |400.00            |
|cs.LG     |2023              |1          |null              |
|cs.LG     |2024              |7          |600.00            |
...

✅ GOLD: 4 tables saved
```

---

## 🎯 EXÉCUTION COMPLÈTE (Séquence)

### Option A: Local Spark (Python)

```bash
# Terminal 1: Vérifier Cassandra
docker-compose ps

# Terminal 2: Exécuter les 3 étapes
cd research_papers_api

# Step 1
python databricks/bronze_layer.py
# Expected: ✅ BRONZE: 18 rows saved

# Step 2
python databricks/silver_layer.py
# Expected: ✅ SILVER: 50+ rows saved

# Step 3
python databricks/gold_layer.py
# Expected: ✅ GOLD: 4 tables saved

# Step 4
python databricks/graph_layer.py
# Expected: ✅ GRAPH: Saved graph analytics outputs

### REMARQUE
Si votre machine locale ne dispose pas de Java ou si PySpark ne démarre pas, utilisez le wrapper Docker :

```bash
bash scripts/run_spark_pipeline.sh
```

Cela exécute Bronze → Silver → Gold → Graph dans un container Apache Spark sans dépendre de Java local.
```

### Option B: Databricks Notebooks

**1. Créer 3 notebooks Databricks:**
- `01_Bronze_Load`
- `02_Silver_Clean`
- `03_Gold_Analytics`

**2. Copier code dans chaque notebook**

**3. Exécuter en séquence**

**4. Ajouter jobs pour scheduling:**
```
Schedule: Quotidienne à 2AM
Timeout: 30 minutes
Notifications: Email sur erreur
```

---

## ✅ VALIDATION DES RÉSULTATS

### Après étape 1: BRONZE

```python
# Vérifier Bronze
df_bronze = spark.read.format("delta").load("/mnt/data/papers_bronze")
assert df_bronze.count() == 18, "Should have 18 rows"
assert "_ingestion_timestamp" in df_bronze.columns, "Should have metadata"
print("✅ BRONZE validation passed")
```

### Après étape 2: SILVER

```python
# Vérifier Silver
df_silver = spark.read.format("delta").load("/mnt/data/papers_silver")
assert df_silver.count() > 18, "Should have exploded authors"
assert "author" in df_silver.columns, "Should have author column"
assert "publication_year" in df_silver.columns, "Should have year"
print("✅ SILVER validation passed")
```

### Après étape 3: GOLD

```python
# Vérifier Gold tables
df_year = spark.read.parquet("/mnt/data/papers_gold/papers_per_year")
df_cat = spark.read.parquet("/mnt/data/papers_gold/papers_per_category")
df_auth = spark.read.parquet("/mnt/data/papers_gold/top_authors")
df_trend = spark.read.parquet("/mnt/data/papers_gold/research_trends")

assert df_year.count() > 0, "Year table empty"
assert df_cat.count() == 5, "Should have 5 categories"
assert df_auth.count() > 0, "Authors table empty"
print("✅ GOLD validation passed")
```

---

## 📊 RÉSUMÉ TEMPS D'EXÉCUTION

| Étape | Durée | Notes |
|-------|-------|-------|
| BRONZE | 2-3 min | Chargement Cassandra |
| SILVER | 3-5 min | Transformations (explode) |
| GOLD | 5-10 min | Agrégations complexes |
| **TOTAL** | **10-20 min** | Parallélisable en production |

---

## 🐛 TROUBLESHOOTING

### Erreur: `py4j.protocol.Py4JJavaError: An error occurred`

**Solution:** Cassandra pas connectée
```bash
docker-compose down
docker-compose up -d
# Attendre 30s que Cassandra démarre
```

### Erreur: `FileNotFoundError: [Errno 2] No such file or directory`

**Solution:** Vérifier le chemin /mnt/data/
```bash
# Créer répertoires s'il faut
mkdir -p /mnt/data/papers_{bronze,silver,gold}
```

### Erreur: `AnalysisException: Path already exists`

**Solution:** Utiliser mode="overwrite"
```python
df.write.mode("overwrite").format("delta").save(path)
```

---

## 🚀 NEXT STEPS

### Après GOLD tables ✅

**1. Créer Dashboards**
- Power BI / Tableau
- Connecter aux tables Gold
- Visualiser trends

**2. ML Features**
- Embeddings (sentence-transformers)
- Clustering papers
- Recommandation system

**3. API REST**
- FastAPI endpoints
- Query analytics tables
- Real-time dashboards

**4. Production Deployment**
- Cloud: AWS/GCP/Azure
- Scheduling: Airflow/Databricks Jobs
- Monitoring: Alertes 24/7

---

## 📞 SUPPORT

**Problèmes?**
1. Vérifier Cassandra: `docker-compose ps`
2. Logs Spark: Chercher erreurs dans output
3. Reconnexion Cassandra: `docker-compose restart cassandra`

**Succès = 3 étapes exécutées + 4 tables Gold créées ✅**
