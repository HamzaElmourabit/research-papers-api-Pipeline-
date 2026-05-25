# Databricks Architecture & Implementation Plan

**Project**: Research Papers Big Data Pipeline - S8 Course  
**Phase**: Phase 5-6: Databricks ELT (Transform, Load, Analytics)  
**Based On**: 18 papers from Cassandra `papers_raw` table  
**Date**: March 26, 2026

---

## 🏗️ Complete Databricks Architecture

```
CASSANDRA (Input)
    │
    └─→ papers_raw table (18 papers, growing daily)
        │
        │ [Read via Spark Cassandra Connector]
        │
        ↓
════════════════════════════════════════════════════════════════
        DATABRICKS LAKEHOUSE
════════════════════════════════════════════════════════════════

BRONZE LAYER (Raw Data)
├─ papers_raw_bronze
│  └─ Direct copy from Cassandra
│     • 18 columns as-is
│     • No transformation
│     • Immutable snapshot

SILVER LAYER (Cleaned & Enriched)
├─ papers_clean
│  ├─ Exploded lists (authors, categories)
│  ├─ Text normalization
│  ├─ Removed duplicates
│  ├─ Added computed columns
│  └─ Quality validated

GOLD LAYER (Analytics & ML-Ready)
├─ papers_analytics
│  ├─ Category statistics
│  ├─ Author network analysis
│  ├─ Paper metadata enriched
│  └─ Ready for visualization

├─ embeddings_table
│  ├─ Abstract embeddings
│  ├─ Title embeddings
│  └─ For similarity search

├─ recommendations_table
│  ├─ Author co-authorship
│  ├─ Category correlation
│  └─ Similar papers
```

---

## 📊 Implementation Plan

| Phase | Task | Deliverable | Duration |
|-------|------|-------------|----------|
| **1** | Setup & Connection | Databricks environment, Cassandra connector | 1 hour |
| **2** | Load Bronze Layer | Raw data from Cassandra to Delta Lake | 1 hour |
| **3** | Transform to Silver | Clean, normalize, enrich data | 2 hours |
| **4** | Create Gold Layer | Analytics tables & features | 2 hours |
| **5** | Analytics Queries | SQL for dashboards & insights | 2 hours |
| **6** | ML Features | Prepare data for ML models | 1 hour |

**Total**: ~9 hours implementation

---

## 📁 Databricks Notebook Structure

```
/Workspace/research_papers_api/
│
├─ 01_setup_and_config.py
│  ├─ Cassandra connection config
│  ├─ Cluster setup
│  └─ Dependencies
│
├─ 02_load_bronze_layer.py
│  ├─ Read papers_raw from Cassandra
│  ├─ Create bronze delta table
│  └─ Verify 18+ records
│
├─ 03_transform_silver_layer.py
│  ├─ Explode lists (authors, categories)
│  ├─ Normalize text
│  ├─ Add computed columns
│  └─ Remove duplicates
│
├─ 04_create_gold_layer.py
│  ├─ Aggregate analytics table
│  ├─ Create embeddings table
│  ├─ Build recommendations
│  └─ Feature engineering
│
├─ 05_analytics_queries.sql
│  ├─ Category analysis
│  ├─ Author statistics
│  ├─ Trending topics
│  └─ Dashboard queries
│
├─ 06_ml_features.py
│  ├─ Text vectorization
│  ├─ Abstract embeddings
│  ├─ Feature matrix creation
│  └─ Model-ready dataset
│
└─ README.md
   └─ Execution guide & documentation
```

---

## 🚀 Quick Start Commands

```python
# Notebook 01: Setup
# Run this first to configure everything

# Notebook 02: Load Bronze
# Creates papers_raw_bronze table with 18 records

# Notebook 03: Transform Silver
# Cleans and enriches data
# Output: papers_clean table

# Notebook 04: Create Gold
# Aggregations and ML features
# Output: papers_analytics, embeddings_table

# Notebook 05: SQL Analytics
# Run queries for dashboards

# Notebook 06: ML Features
# Prepare for model training
```

---

## 💾 Database Tables Created

### **Bronze Layer**
```
papers_raw_bronze
├─ Columns: 13 (same as Cassandra papers_raw)
├─ Records: 18
├─ Purpose: Immutable raw data copy
└─ Partitioned by: ingestion_date
```

### **Silver Layer**
```
papers_clean
├─ Columns: 20 (13 original + 7 computed)
├─ Rows: 50-60 (exploded from 18)
├─ Purpose: Clean, deduplicated, enriched
└─ Partitioned by: primary_category
```

### **Gold Layer**
```
papers_analytics
├─ Columns: 15 (aggregated metrics)
├─ Rows: 5 (one per category)
├─ Purpose: Reporting and dashboards
└─ Key: category, paper_count, avg_authors

embeddings_table
├─ Columns: 5 (arxiv_id, abstract_embedding, title_embedding, etc.)
├─ Rows: 18
├─ Purpose: ML features & similarity search
└─ Embedding dim: 384 (sentence-transformers)
```

---

## 📈 Analytics Queries Included

1. **Papers by Category**
   ```sql
   SELECT category, COUNT(*) as count
   FROM papers_clean
   GROUP BY category
   ORDER BY count DESC
   ```

2. **Top Authors**
   ```sql
   SELECT author, COUNT(*) as papers, 
          COLLECT_LIST(arxiv_id) as paper_ids
   FROM papers_clean
   GROUP BY author
   ORDER BY papers DESC
   LIMIT 20
   ```

3. **Category Trends**
   ```sql
   SELECT primary_category, published_date, COUNT(*) as daily_count
   FROM papers_clean
   GROUP BY primary_category, published_date
   ORDER BY primary_category, published_date DESC
   ```

4. **Similar Papers** (using embeddings)
   ```sql
   SELECT p1.arxiv_id, p2.arxiv_id, 
          cosine_similarity(p1.abstract_embedding, p2.abstract_embedding) as similarity
   FROM embeddings_table p1, embeddings_table p2
   WHERE cosine_similarity(...) > 0.8
   LIMIT 100
   ```

---

## 🔧 Infrastructure Requirements

### **Databricks Cluster**
```
Name: research-papers-cluster
Runtime: Databricks 14.0 (Spark 3.5+)
Driver: 8GB (i3.xlarge or similar)
Workers: 2x 8GB (i3.xlarge or similar)
Auto-terminate: 30 minutes
```

### **Init Script**
```bash
#!/bin/bash
pip install cassandra-driver
pip install sentence-transformers
pip install scikit-learn
pip install pyspark-cassandra==3.2.0
```

### **Cluster Configuration**
```
spark.cassandra.connection.host cassandra_arxiv
spark.cassandra.connection.port 9042
spark.cassandra.input.split.size_in_mb 100
```

---

## 📊 Expected Outputs

After running all notebooks:

| Table | Records | Purpose |
|-------|---------|---------|
| papers_raw_bronze | 18 | Raw copy |
| papers_clean | 60 | Cleaned data |
| papers_analytics | 5 | Category stats |
| embeddings_table | 18 | ML features |

---

## 🎯 Success Criteria

After implementation, you can:

✅ Query: `SELECT COUNT(*) FROM papers_clean` → returns ~60  
✅ Query: `SELECT DISTINCT category FROM papers_clean` → returns 4-5 categories  
✅ View: Embeddings for similarity search  
✅ Build: Recommendations based on co-authorship  
✅ Create: Dashboards with category trends  

---

## 📁 Deliverables

You will receive:

1. **6 Databricks Notebooks** (ready to import)
2. **SQL Analytics Queries** (pre-built)
3. **Python transformation code** (cleaning & ML)
4. **Configuration guide** (how to set up)
5. **Data dictionary** (all columns explained)
6. **Execution roadmap** (step-by-step)

---

**Status**: 🚀 Ready to implement

*Next: Generate all notebooks and SQL queries*
