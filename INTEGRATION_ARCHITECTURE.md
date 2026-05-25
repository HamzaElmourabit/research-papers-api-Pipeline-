# Dagster → Databricks Integration Architecture

## 🏗️ Complete Data Pipeline Architecture

```
PHASE 1-4: DAGSTER (✅ COMPLETE - Your Part)
═════════════════════════════════════════════════════════════

                    ArXiv API
                        ↓
              ┌─────────────────────┐
              │  FETCH PAPERS       │  Asset: fetch_arxiv_papers
              │  5 Categories       │  • CS.AI, CS.LG, CS.CV, CS.CL, stat.ML
              │  ~2 per category    │  • JSON format from API
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │ VALIDATE PAPERS     │  Asset: validate_papers
              │ Pydantic Rules      │  • Required: title, abstract, authors
              │ 100% Pass Rate      │  • Validates: categories, urls
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │ STORE IN CASSANDRA  │  Asset: store_in_cassandra
              │ Docker cqlsh        │  • Inserts via subprocess
              │ Batch Tracking      │  • Deduplication by batch_id+arxiv_id
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │  CASSANDRA DATABASE │  Table: papers_raw
              │  Keyspace: arxiv    │  • 13 columns
              │  18 papers (ready)  │  • 1 table
              └─────────┬───────────┘
                         ↓
                    (HANDOFF POINT)
                         ↓

PHASE 5-6: DATABRICKS (🚀 NEXT - Your Classmate's Part)
═════════════════════════════════════════════════════════════

              ┌─────────────────────┐
              │  DATABRICKS CLUSTER │  Connect & Ingest
              │  Spark Cassandra    │  • Read papers_raw
              │  Connector          │  • Export to Delta Lake
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │  DELTA LAKE         │  Bronze Layer
              │  /mnt/data/papers   │  • Raw papers_raw copy
              │  (Immutable)        │  • Batch partitioning
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │  DATA CLEANING      │  Silver Layer
              │  • Explode lists    │  • Normalize text
              │  • Add embeddings   │  • Feature engineering
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │  ANALYTICS TABLES   │  Gold Layer
              │  • Paper metrics    │  • Author networks
              │  • Category trends  │  • Topic models
              └──────────┬──────────┘
                         ↓
              ┌─────────────────────┐
              │  ML MODELS          │
              │  • Recommendations  │  Serve to users
              │  • Classifications  │
              └─────────────────────┘
```

---

## 📊 Data Flow Details

### **What Dagster Produces**
```
Input:  ArXiv API (JSON)
         ↓ (5 categories × 2 papers/day)
         ↓
Process: Fetch → Validate → Transform to SQL records
         ↓
Output: Cassandra Table
        ┌─────────────────────────────────────┐
        │ papers_raw (13 columns)             │
        ├─────────────────────────────────────┤
        │ • batch_id (UUID) - Run identifier  │
        │ • arxiv_id (TEXT) - Paper ID        │
        │ • title, abstract (TEXT)            │
        │ • authors, categories (LIST)        │
        │ • dates, pdf_url, json (TEXT)       │
        └─────────────────────────────────────┘
```

### **What Databricks Consumes**
```
Input:  papers_raw (Cassandra)
        ↓
Process: 
  1. Read via Spark Cassandra Connector
  2. Export to Delta Lake (immutable)
  3. Transform (clean, enrich, feature engineer)
  4. Analyze (aggregations, ML)
  5. Serve (dashboards, APIs)
        ↓
Output: Insights, Models, Dashboards
```

---

## 🔌 Connection Points

### Connection 1: Cassandra → Spark
```python
# In Databricks notebook
papers = spark.read \
    .format("org.apache.spark.sql.cassandra") \
    .options(
        keyspace="arxiv", 
        table="papers_raw",
        spark.cassandra.connection.host="cassandra_arxiv"
    ) \
    .load()
```

### Connection 2: Spark → Delta
```python
papers.write.format("delta") \
    .mode("overwrite") \
    .path("/mnt/data/papers_raw") \
    .save()
```

### Connection 3: Delta → Analytics
```sql
SELECT arxiv_id, title, primary_category, SIZE(authors) as author_count
FROM papers_raw
WHERE primary_category = 'cs.LG'
ORDER BY published_date DESC
LIMIT 100
```

---

## 📦 Delivery Checklist

### **Files Your Classmate Receives**

```
research papers api/
│
├── 📄 DATABRICKS_HANDOFF.md ⭐      # Complete integration guide
├── 📄 QUICK_REFERENCE.md ⭐         # Quick start (this file summary)
├── 📄 PROJECT_STATUS.md             # Overall project status
├── 📄 README.md                     # Setup instructions
├── 📄 requirements.txt              # All dependencies
│
├── 📂 pipelines/ (reference)
│   ├── dagster_pipeline.py          # To understand the ETL
│   └── assets/
│       ├── fetch.py                 # How data is fetched
│       ├── validate.py              # Validation rules
│       └── store.py                 # Data insertion
│
├── 📂 ingestion/ (reference)
│   ├── validation.py                # Validation rules
│   └── arxiv_client.py              # API integration
│
├── 🐳 docker-compose.yml            # Cassandra setup
├── 🗄️ casandra/schema.cql           # Table definition
│
└── 📊 Live Cassandra Database
    └── 18 papers ready to analyze
```

### **What They Need to Do**

1. **Access the Database**
   - Verify Cassandra is accessible on port 9042
   - Test connection with sample query

2. **Set up Databricks Cluster**
   - Create cluster with Spark 3.4+
   - Install Cassandra connector

3. **Ingest Data**
   - Read from papers_raw table
   - Export to Delta Lake

4. **Transform**
   - Clean and normalize data
   - Add ML features

5. **Analyze**
   - Create dashboards
   - Train ML models

---

## 🎯 Handoff Success Criteria

✅ **They can pass:**
- [ ] Connect to Cassandra and read papers_raw
- [ ] Query count: `SELECT COUNT(*) FROM papers` returns ≥ 18
- [ ] View sample papers with SQL query
- [ ] Save data to Delta Lake
- [ ] Create Databricks table from Delta

✅ **You have provided:**
- [ ] DATABRICKS_HANDOFF.md (complete guide)
- [ ] QUICK_REFERENCE.md (quick start)
- [ ] Live Cassandra database with 18 papers
- [ ] Full schema and column definitions
- [ ] Connection instructions
- [ ] Sample queries
- [ ] Recommended transformations
- [ ] Troubleshooting guide

---

## 📈 Timeline for Databricks Phase

**Week 1**: Infrastructure Setup
- Databricks workspace creation
- Cluster configuration
- Connection testing

**Week 2**: Data Ingestion
- Load papers_raw from Cassandra
- Create Delta tables
- Data quality checks

**Week 3**: Transformation & Analytics
- Data cleaning
- Feature engineering
- Exploratory analysis

**Week 4**: ML & Insights
- Model training
- Dashboard creation
- API deployment

---

## 🚀 Future Enhancements (Not Included)

These are suggestions for your classmate:

1. **Real-time Ingestion**
   - Implement Kafka/Event Hubs
   - Stream papers as they arrive

2. **Advanced ML**
   - Recommendation engine
   - Citation prediction
   - Topic clustering

3. **Multi-source Integration**
   - Add IEEE, ACM papers
   - Cross-reference citations

4. **Production Deployment**
   - Enterprise Cassandra cluster
   - Databricks SQL warehouse
   - Power BI/Tableau integration

---

## ❓ FAQ

**Q: Can I modify the Dagster pipeline?**  
A: Yes! But coordinate with Dagster team. Changes to schema would require Databricks to adapt too.

**Q: How often does Cassandra get updated?**  
A: Daily at 2 AM UTC with ~5-10 new papers per category.

**Q: What if the connection fails?**  
A: Ensure Docker is running: `docker ps | grep cassandra_arxiv`

**Q: Can I add more data sources?**  
A: Yes, but that's in Dagster phase. Coordinate first.

**Q: What's the expected data volume?**  
A: Currently 18 papers, growing ~7 papers/day. Expect ~200 papers/month.

---

**Delivery Status: ✅ COMPLETE**

*All Dagster components are ready for Databricks integration*
