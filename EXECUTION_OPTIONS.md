# 🚀 EXECUTION GUIDE - Research Papers API Pipeline

**Status:** May 24, 2026  
**Infrastructure:** Kafka ✓, Cassandra ✓, Databricks Scripts ✓  
**Current Blocker:** Docker Desktop unresponsive, Local Spark JVM incompatible

---

## 📊 What You Have Ready

### ✅ Data Pipeline Infrastructure
- **Kafka Topic:** `arxiv-papers-raw` (1,036 messages ready)
- **Cassandra Table:** `papers_raw` (operational)
- **Producer:** `scripts/kafka_producer.py` (tested ✓)
- **Consumer:** `scripts/kafka_consumer.py` (ready)
- **Export:** `scripts/export_to_parquet.py` (ready)

### ✅ Databricks Transformation Scripts
```
databricks/
├── bronze_layer.py       # Load from Cassandra → Spark DataFrame
├── silver_layer.py       # Clean & normalize data
└── gold_layer.py         # Create aggregations for analytics
```

---

## 🎯 3 Execution Options (Ranked by Feasibility)

### **OPTION 1: Databricks Cloud (RECOMMENDED - NO LOCAL SETUP) ⭐**

**Why?** 
- No local JVM issues
- Production-ready infrastructure
- Cloud-integrated storage
- Automatic scaling
- Best for enterprise use

**Steps:**

#### 1a. Create Free Databricks Community Account
```
Visit: https://databricks.com/try-databricks
- Select "Community Edition" (free tier)
- Choose cloud provider (AWS/Azure)
- Create workspace
```

#### 1b. Upload Notebooks
```
In Databricks UI:
1. Create folder: /Workspace/research-papers
2. Import notebook: Databricks → Import → File Upload
   - Upload databricks/bronze_layer.py
   - Upload databricks/silver_layer.py
   - Upload databricks/gold_layer.py
3. Attach to cluster (create if needed: 1 worker, DBR 13.0+)
```

#### 1c. Execute Pipeline
```python
# In first notebook cell, set connection parameters:
cassandra_host = "YOUR_CASSANDRA_IP"  # Or use SSH tunnel if on local machine
cassandra_port = 9042

# Run each layer sequentially:
# 1. %run ./bronze_layer.py
# 2. %run ./silver_layer.py
# 3. %run ./gold_layer.py

# Results saved to cloud storage (automatically)
```

**Estimated Time:** 30 minutes  
**Cost:** Free (Community Edition)

---

### **OPTION 2: Docker Spark Container (If Docker Desktop recovers)**

**Prerequisites:**
```bash
# 1. Fix Docker Desktop connection
# Try:
- Restart Docker Desktop application
- Check: docker ps  # Should return empty list
```

**Steps:**
```bash
# 1. Start all services
docker compose up -d

# 2. Verify services running
docker compose ps

# 3. Run Spark in container (against local services)
docker run --it --network researchpapersapi-copy_arxiv_network \
  --mount type=bind,source=$(pwd),target=/workspace \
  --mount type=bind,source=$(pwd)/data,target=/mnt/data \
  apache/spark:3.4.1 \
  /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  /workspace/databricks/bronze_layer.py

# 4. Run remaining layers
docker run --it --network researchpapersapi-copy_arxiv_network \
  --mount type=bind,source=$(pwd),target=/workspace \
  --mount type=bind,source=$(pwd)/data,target=/mnt/data \
  apache/spark:3.4.1 \
  /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  /workspace/databricks/silver_layer.py

docker run --it --network researchpapersapi-copy_arxiv_network \
  --mount type=bind,source=$(pwd),target=/workspace \
  --mount type=bind,source=$(pwd)/data,target=/mnt/data \
  apache/spark:3.4.1 \
  /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  /workspace/databricks/gold_layer.py
```

**Estimated Time:** 45 minutes (including Docker restart)

---

### **OPTION 3: Validate Kafka→Cassandra Locally (No Spark)**

**Advantage:** Works immediately without Docker/Spark JVM issues

**Steps:**

```bash
# 1. Start Docker services (if Docker recovers)
docker compose up -d kafka cassandra

# 2. Verify Kafka has messages
# Open: http://localhost:9000 (Kafdrop UI)

# 3. Consume Kafka → Insert into Cassandra
cd venv/Scripts && Activate
python ../scripts/kafka_consumer.py \
  --kafka-server localhost:9092 \
  --topic arxiv-papers-raw \
  --batch-size 100

# 4. Verify data in Cassandra
docker exec cassandra_arxiv cqlsh -e \
  "USE arxiv; SELECT COUNT(*) FROM papers_raw;"

# 5. Export to Parquet
python ../scripts/export_to_parquet.py \
  --output-dir ./data/parquet \
  --chunk-size 400

# 6. Verify Parquet files created
ls -lah ./data/parquet/
```

**Estimated Time:** 15 minutes  
**Output:** Parquet files ready for analysis

---

## 🔧 Troubleshooting

### Docker Desktop Not Responding
```
1. Check if Docker service is running:
   Services → Look for "Docker Desktop Service"
   
2. Restart Docker:
   - Right-click Docker icon → Quit
   - Wait 30 seconds
   - Reopen Docker Desktop
   - Wait for "Docker is running" message
   
3. Verify:
   docker ps
   # Should return empty container list (not error)
```

### Cassandra Connection Error
```bash
# Verify Cassandra is running
docker compose ps cassandra

# Check logs if down
docker compose logs cassandra

# Restart if needed
docker compose restart cassandra
```

### Kafka Topic Empty
```bash
# Verify messages exist
docker exec kafka_broker kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group my-group

# Or check via Kafdrop: http://localhost:9000
```

---

## 📋 Decision Matrix

| Criteria | Option 1 (Cloud) | Option 2 (Docker) | Option 3 (Local) |
|----------|------------------|-------------------|------------------|
| **Setup Time** | 30 min | 45 min | 15 min |
| **Local Issues** | None | Requires Docker | None |
| **Production Ready** | ✅ Yes | ⚠️ Dev only | ✓ Partial |
| **Scaling** | ✅ Automatic | Manual | Not applicable |
| **Cost** | Free | Free | Free |
| **Recommended For** | Production ELT | Development | Quick validation |

---

## 📌 Quick Reference

### Databricks Cloud Execution (Best)
```
https://databricks.com/try-databricks
→ Create workspace
→ Upload scripts
→ Run sequentially
```

### Docker Spark (If Docker works)
```bash
docker compose up -d
docker run --it --network researchpapersapi-copy_arxiv_network \
  -v $(pwd):/workspace \
  -v $(pwd)/data:/mnt/data \
  apache/spark:3.4.1 \
  /opt/spark/bin/spark-submit --master local[2] --conf spark.jars.ivy=/tmp/.ivy2 \
  --packages com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 /workspace/databricks/bronze_layer.py
```

### Local Kafka→Cassandra→Parquet (Fastest)
```bash
python scripts/kafka_consumer.py --kafka-server localhost:9092
python scripts/export_to_parquet.py --output-dir ./data/parquet
```

---

## ✅ Next Steps (Choose One)

1. **RECOMMENDED:** Sign up for Databricks → Upload → Execute
2. **If Docker works:** Run docker compose + Spark container
3. **Immediate validation:** Run Kafka consumer + export to Parquet

---

**Questions?** All scripts support `--help` flag  
Example: `python scripts/kafka_consumer.py --help`
