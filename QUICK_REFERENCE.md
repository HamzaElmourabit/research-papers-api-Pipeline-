# Quick Reference for Databricks Team

## 🎯 TL;DR - What You Need to Know

**Data Source**: Cassandra `arxiv.papers_raw` table  
**Connection**: `localhost:9042` (or `cassandra_arxiv:9042` if Docker)  
**Current Records**: 18 papers (growing ~5-10 daily)  
**Update Frequency**: Daily at 2 AM UTC  
**Export**: Parquet files available via `scripts/export_to_parquet.py`  
**Your Job**: Transform, clean, analyze, and build ML models  

---

## 📥 Quick Export to Parquet

Need to export data for offline analysis? Use the export script:

```bash
# One-liner: Export all papers to Parquet files
python scripts/export_to_parquet.py

# Custom output
python scripts/export_to_parquet.py --output-dir "./my_data" --chunk-size 500

# Then load in Python:
import pandas as pd
df = pd.read_parquet("./data/parquet/papers_raw_part_*.parquet")
```

See [EXPORT_TO_PARQUET.md](EXPORT_TO_PARQUET.md) for full details.

---

## 📌 Critical Information

### Connection String (Databricks)
```python
spark.read \
    .format("org.apache.spark.sql.cassandra") \
    .options(keyspace="arxiv", table="papers_raw") \
    .option("spark.cassandra.connection.host", "cassandra_arxiv") \
    .load()
```

### Table Structure (13 Columns)
```
batch_id (UUID)         → Ingestion run identifier
arxiv_id (TEXT)         → Paper ID (e.g., 2603.18325v1)
title (TEXT)            → Paper title
abstract (TEXT)         → Paper abstract
authors (LIST<TEXT>)    → Author names
categories (LIST<TEXT>) → ArXiv categories (cs.LG, cs.AI, etc.)
primary_category (TEXT) → Main category
published_date (TEXT)   → YYYY-MM-DD
updated_date (TEXT)     → YYYY-MM-DD
pdf_url (TEXT)          → Direct PDF link
raw_json (TEXT)         → Original API response
ingestion_date (DATE)   → When paper was fetched
ingested_at (TEXT)      → ISO timestamp
```

### Data Quality
- ✅ 100% validation pass rate
- ✅ No nulls (all fields required)
- ✅ No duplicates (PRIMARY KEY enforced)
- ✅ Growing ~5-10 papers daily

---

## 🚀 First Steps

### Step 1: Connect to Cassandra
```python
# Test connection
df = spark.read \
    .format("org.apache.spark.sql.cassandra") \
    .options(keyspace="arxiv", table="papers_raw") \
    .load()

df.count()  # Should return 18
```

### Step 2: Save to Delta Lake
```python
df.write.mode("overwrite") \
    .format("delta") \
    .path("/mnt/data/papers") \
    .save()
```

### Step 3: Create Table
```sql
CREATE TABLE papers
USING DELTA
LOCATION '/mnt/data/papers'
```

### Step 4: Explore Data
```sql
SELECT arxiv_id, title, primary_category 
FROM papers 
LIMIT 10
```

---

## 📊 Sample Queries

### Papers by Category
```sql
SELECT primary_category, COUNT(*) as count
FROM papers
GROUP BY primary_category
ORDER BY count DESC
```

### Recent Papers (Last 7 Days)
```sql
SELECT arxiv_id, title, published_date
FROM papers
WHERE published_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY published_date DESC
```

### Papers with Multiple Authors
```sql
SELECT arxiv_id, title, SIZE(authors) as author_count
FROM papers
WHERE SIZE(authors) > 3
ORDER BY author_count DESC
```

---

## 🛠️ Recommended Transformations

### Explode Lists to Rows
```python
from pyspark.sql.functions import explode

papers_clean = df \
    .withColumn("author", explode("authors")) \
    .withColumn("category", explode("categories")) \
    .drop("authors", "categories")
```

### Add Text Features
```python
from pyspark.ml.feature import Tokenizer, CountVectorizer

tokenizer = Tokenizer(inputCol="abstract", outputCol="words")
papers_clean = tokenizer.transform(papers_clean)
```

### Deduplication Check
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

df.dropDuplicates(["arxiv_id"])  # Should change nothing
```

---

## ⚙️ Infrastructure Setup

### Databricks Cluster Init Script
```bash
#!/bin/bash
# Install dependencies
pip install cassandra-driver

# Configure Spark Cassandra Connector
pip install pyspark-cassandra==3.2.0
```

### Environment Variables
```
CASSANDRA_HOST=cassandra_arxiv
CASSANDRA_PORT=9042
CASSANDRA_KEYSPACE=arxiv
CASSANDRA_TABLE=papers_raw
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure Docker/Cassandra is running. Test: `docker ps \| grep cassandra` |
| No data returned | Check if pipeline has run. Verify: `docker exec cassandra_arxiv cqlsh -e "USE arxiv; SELECT COUNT(*) FROM papers_raw;"` |
| Slow queries | Add indexes on frequently queried columns (arxiv_id, primary_category) |
| Out of memory | Reduce batch size or use Delta format for better partitioning |

---

## 📞 Contact Dagster Team If

- [ ] Connection is failing after setup
- [ ] Data count is 0 (should be ≥18)
- [ ] Need to modify pipeline settings
- [ ] Want to add new data sources
- [ ] Questions about validation rules

---

## 📚 Full Documentation

See `DATABRICKS_HANDOFF.md` for:
- Complete schema definition
- All 13 column specifications
- Recommended analytics
- Full task checklist
- Infrastructure requirements

---

**Generated**: March 24, 2026  
**Status**: ✅ Ready to hand off to Databricks team
