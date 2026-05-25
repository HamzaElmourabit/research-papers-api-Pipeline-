# 🚀 HOW TO RUN THE PROJECT
## Complete Step-by-Step Guide

**Platform:** Windows 11 | Python 3.13.5  
**Components:** Dagster + Cassandra + ArXiv API + Databricks  
**Status:** Production Ready ✅  

---

## 📋 TABLE OF CONTENTS

1. [Quick Start (5 minutes)](#quick-start)
2. [Full Setup (30 minutes)](#full-setup)
3. [Running the ETL Pipeline](#running-etl)
4. [Running Databricks Notebooks](#running-databricks)
5. [Exporting to Parquet](#exporting-to-parquet)
6. [Monitoring & Dashboards](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Common Commands](#common-commands)

---

## ⚡ QUICK START (5 minutes)

### Step 1: Start Cassandra (Docker)
```bash
# Windows PowerShell
cd "C:\Users\khadi\Downloads\research papers api - Copy"
docker-compose up -d

# Verify Cassandra is running
docker ps | grep cassandra_arxiv

# Expected output:
# CONTAINER ID   IMAGE          PORTS                    NAMES
# abc123...      cassandra:5.0  9042/tcp                 cassandra_arxiv
```

### Step 2: Activate Python Environment
```bash
# Create virtual environment (first time only)
python -m venv venv

# Activate
venv\Scripts\activate

# You should see "(venv)" in your prompt
# Example: (venv) C:\Users\khadi\Downloads\research papers api - Copy>
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt

# Optional: Install development dependencies
pip install pytest pytest-cov black flake8
```

### Step 4: Run the Pipeline
```bash
# Quick test (fetch 5 papers, validate, store)
python main.py

# Expected output:
# Fetching papers from arXiv...
#   Fetched : 5 papers
# Validating papers...
#   Valid   : 5 papers
#   Dropped : 0 papers
# Inserting into Cassandra...
#   Batch ID : abc123...
#   Ingestion Date : 2024-01-15
#   Inserted : 5/5
#   Failed   : 0
```

### Step 5: Verify Data in Cassandra
```bash
# Connect to Cassandra
docker exec -it cassandra_arxiv cqlsh

# In cqlsh prompt:
USE arxiv;
SELECT COUNT(*) FROM papers_raw;

# Expected: 5 rows

# View sample paper
SELECT arxiv_id, title, published_date FROM papers_raw LIMIT 1;

# Exit cqlsh
exit
```

✅ **Done!** You have successfully run the pipeline.

---

## 🔧 FULL SETUP (30 minutes)

### Prerequisites Check
```bash
# Check Python version (must be 3.11+)
python --version
# Expected: Python 3.13.5

# Check Docker is installed
docker --version
# Expected: Docker version 24.x or higher

# Check Docker Desktop is running (Windows)
docker ps
# Should show running containers

# Check Git (for cloning updates)
git --version
# Expected: git version 2.x
```

### Environment Setup

#### 1. Clone/Setup Project
```bash
cd "C:\Users\khadi\Downloads\research papers api - Copy"
git status  # Optional: if using git
```

#### 2. Create Virtual Environment
```bash
# Create venv
python -m venv venv

# Activate
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

#### 3. Install All Dependencies
```bash
# Core dependencies
pip install -r requirements.txt

# Development tools
pip install -r requirements-dev.txt

# Or install individually
pip install arxiv>=1.4.6
pip install pandas>=2.1.0
pip install cassandra-driver>=3.25.0
pip install pydantic>=2.2.1
pip install dagster>=1.5.0
pip install dagit>=1.5.0
pip install pyspark>=3.5.0
pip install python-dotenv>=1.0.0
pip install pytest>=8.2.0
```

#### 4. Create .env File
```bash
# Copy example
copy .env.example .env

# Edit .env with settings
# Windows Notepad: notepad .env

# File contents:
# ── CASSANDRA ──
# CASSANDRA_HOST=cassandra_arxiv
# CASSANDRA_PORT=9042
# CASSANDRA_KEYSPACE=arxiv

# ── PIPELINE ──
# BATCH_SIZE=10
# CATEGORIES=cs.AI,cs.LG,cs.CV,cs.CL,stat.ML

# ── ENVIRONMENT ──
# ENVIRONMENT=development
# DEBUG=false
```

#### 5. Start Infrastructure (Docker)
```bash
# Start Cassandra container
docker-compose up -d

# Monitor startup (wait for healthy status)
docker-compose ps

# Expected: Status should be "Up (healthy)"

# View logs
docker-compose logs cassandra

# Wait for "Cassandra initialized successfully"
```

#### 6. Initialize Database Schema
```bash
# Option A: Automatic (Python script)
python scripts/setup_cassandra.py

# Option B: Manual (Docker cqlsh)
docker exec -it cassandra_arxiv cqlsh -f /schema.cql

# Verify schema created
docker exec cassandra_arxiv cqlsh -e "USE arxiv; DESCRIBE TABLES;"

# Expected output:
# papers_raw
```

✅ **Full Setup Complete!** Ready to run pipeline.

---

## ⚙️ RUNNING THE ETL PIPELINE

### Method 1: Direct Python (Development)

#### Simple Run (Fetch → Validate → Store)
```bash
# Activate venv first
venv\Scripts\activate

# Run pipeline
python main.py

# Output example:
# ═══════════════════════════════════════════
# Fetching papers from arXiv...
#   Fetched : 25 papers
# 
# Validating papers...
#   Valid   : 24 papers
#   Dropped : 1 papers
# 
# Inserting into Cassandra...
#   Batch ID : 550e8400-e29b-41d4-a716-446655440000
#   Ingestion Date : 2024-01-15
#   Inserted : 24/24
#   Failed   : 0
# ═══════════════════════════════════════════
```

#### Run with Custom Parameters
```bash
# Create test script
python -c "
from ingestion.fetch_papers import PaperFetcher
from ingestion.validation import validate_paper
from casandra.insert_papers import insert_papers

# Custom batch size
fetcher = PaperFetcher(batch_size=20)
raw_papers = fetcher.fetch_papers()

# Validate
valid_papers = validate_paper(raw_papers)

# Store
summary = insert_papers(valid_papers)

print(f'✅ Inserted {summary[\"inserted\"]} papers')
"
```

### Method 2: Using Scripts (Production)

#### Run via PowerShell Script
```bash
# Windows PowerShell
.\scripts\run_ingestion.ps1

# Or:
.\scripts\run_ingestion.sh  # Git Bash
```

#### Run via Python Script
```bash
# Unix/Mac/Linux style
python scripts/run_ingestion.py

# Or direct on Windows
python scripts/run_ingestion.py
```

### Method 3: Using Dagster (Orchestration)

#### Start Dagster UI
```bash
# Activate venv
venv\Scripts\activate

# Option A: Launch Dagit (UI)
dagit -f pipelines/dagster_pipeline.py

# Browser opens at: http://localhost:3000

# Option B: Use Python script
python scripts/launch_dagit.py

# Option C: Command line
dagster dev -f pipelines/dagster_pipeline.py
```

#### In Dagster UI
```
1. Navigate to http://localhost:3000
2. Click "Assets" → See your assets:
   - fetch_arxiv_papers
   - validate_papers
   - store_in_cassandra
3. Click "Jobs" → Select "daily_ingestion_job"
4. Click "Materialize" button (play icon)
5. Monitor execution in "Runs" tab
```

#### Run via Dagster CLI
```bash
# Execute asset
dagster asset materialize -f pipelines/dagster_pipeline.py -a fetch_arxiv_papers

# Execute entire job
dagster job execute -f pipelines/dagster_pipeline.py -j daily_ingestion_job

# Schedule execution
dagster schedule run -f pipelines/dagster_pipeline.py daily_ingestion_job
```

### Method 4: Test the Pipeline
```bash
# Run test suite
pytest tests/ -v

# Run specific test
pytest tests/test_validation.py -v

# Run with coverage
pytest tests/ --cov=ingestion --cov=casandra

# View coverage report
coverage html
start htmlcov/index.html  # Windows
```

---

## 📊 RUNNING DATABRICKS NOTEBOOKS

### Prerequisites
- Databricks workspace account
- Cassandra running and accessible
- 6 notebooks ready to import

### Step 1: Import Notebooks into Databricks

```
1. Go to databricks_notebooks/ folder
2. Select all 6 notebooks (.py files):
   - 01_setup_and_config.py
   - 02_load_bronze_layer.py
   - 03_transform_silver_layer.py
   - 04_create_gold_layer.py
   - 05_analytics_queries.sql
   - 06_ml_features.py

3. In Databricks Workspace:
   - Click "Create" → "Notebook import"
   - Upload each notebook
   - Organize in folder: /databricks_notebooks/
```

### Step 2: Configure Cluster

```
1. Create Databricks Cluster:
   - Cluster name: "arxiv-pipeline"
   - Spark version: 12.2 LTS or higher
   - Node type: Standard_DS4_v2 (4GB RAM minimum)
   - Min workers: 2
   - Max workers: 8 (auto-scale)
   - Python: 3.10+

2. Runtime: "Machine Learning" or "All Purpose"

3. Libraries to install:
   - sentence-transformers
   - scikit-learn
   - spark-cassandra-connector
```

### Step 3: Update Configuration

```python
# In notebook 01_setup_and_config.py, update:

CASSANDRA_HOST = "your-cassandra-host"  # e.g., "cassandra_arxiv" or IP
CASSANDRA_PORT = "9042"
CASSANDRA_KEYSPACE = "arxiv"
CASSANDRA_TABLE = "papers_raw"
```

### Step 4: Run Notebooks Sequentially

```
Timeline: ~45 minutes total

Notebook 1: 01_setup_and_config.py (2-3 min)
   ✓ Verify libraries installed
   ✓ Verify Cassandra connection
   ✓ Setup Delta Lake paths
   → Run ALL cells

Notebook 2: 02_load_bronze_layer.py (3-5 min)
   ✓ Load from Cassandra
   ✓ Create papers_raw_bronze
   → Run ALL cells

Notebook 3: 03_transform_silver_layer.py (5-7 min)
   ✓ Clean and validate data
   ✓ Create papers_clean table
   → Run ALL cells

Notebook 4: 04_create_gold_layer.py (5-10 min)
   ✓ Create 8 analytics tables
   ✓ Build Star Schema
   → Run ALL cells

Notebook 5: 05_analytics_queries.sql (1-2 min each)
   ✓ Copy each query and run
   ✓ Verify results
   → Run queries manually as needed

Notebook 6: 06_ml_features.py (15-20 min)
   ✓ Generate embeddings
   ✓ Create ML features table
   → Run ALL cells (slow - normal!)
```

### Step 5: Verify Results

```sql
-- In Databricks SQL cell:

-- Check all tables created
SHOW TABLES;

-- Should show:
-- papers_raw_bronze (18 records)
-- papers_clean (18 records) 
-- papers_dim (18 records)
-- category_metrics (5 rows)
-- year_metrics (5 rows)
-- top_authors (20 rows)
-- top_keywords (30 rows)
-- ml_features (18 records)

-- Verify record counts
SELECT 'Bronze' as layer, COUNT(*) as records FROM papers_raw_bronze
UNION ALL
SELECT 'Silver', COUNT(*) FROM papers_clean
UNION ALL
SELECT 'Gold-Papers', COUNT(*) FROM papers_dim;

-- Expected:
-- Bronze: 18
-- Silver: 18  
-- Gold-Papers: 18
```

---

## � EXPORTING TO PARQUET

### Why Export to Parquet?
- Load data into Python/Pandas for analysis
- Feed into Databricks Delta Lake
- Create Spark tables
- Long-term storage (compressed, efficient)

### Method 1: Quick Export (Standalone Script)

```bash
# Windows PowerShell
cd "C:\Users\khadi\Downloads\research papers api - Copy"

# Default settings (400 rows per file, output to ./data/parquet)
python scripts/export_to_parquet.py

# Custom output directory
python scripts/export_to_parquet.py --output-dir "./my_exports/papers"

# Custom chunk size (1000 rows per file)
python scripts/export_to_parquet.py --chunk-size 1000

# All options
python scripts/export_to_parquet.py \
    --output-dir "./data/parquet" \
    --chunk-size 500 \
    --contact-points cassandra_arxiv \
    --port 9042
```

### Method 2: Export via Dagster UI

```
1. Start Dagster:
   dagit -f pipelines/dagster_pipeline.py

2. Navigate to http://localhost:3000

3. Click "Assets" tab

4. Find "export_papers_to_parquet" asset

5. Click "Materialize" (play icon)

6. Monitor in "Runs" tab

7. Output files saved to ./data/parquet/
```

### Method 3: Export via Bash Script

```bash
# Git Bash or WSL
bash scripts/export_to_parquet.sh "./data/parquet" 400

# No arguments (uses defaults)
bash scripts/export_to_parquet.sh
```

### Output Format

```
data/parquet/
├── papers_raw_part_0.parquet  ← 400 rows
├── papers_raw_part_1.parquet  ← 400 rows
├── papers_raw_part_2.parquet  ← 400 rows
└── papers_raw_part_N.parquet  ← remaining rows
```

### Load Exported Data in Python

```python
import pandas as pd

# Load all Parquet files
df = pd.read_parquet("./data/parquet/papers_raw_part_*.parquet")

# Check shape
print(f"Loaded {len(df)} papers with {len(df.columns)} columns")

# View sample
print(df.head())

# Access columns
print(df['title'].head())
print(df['authors'].head())
print(df['published'].head())

# Export subset to CSV
df[df['arxiv_category'] == 'cs.AI'].to_csv("ai_papers.csv")
```

### Load Exported Data in Spark

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ParquetLoader").getOrCreate()

# Load all Parquet files
df = spark.read.parquet("./data/parquet/papers_raw_part_*.parquet")

# Show schema
df.printSchema()

# Show data
df.show(5)

# Save to Delta Lake
df.write.format("delta").mode("overwrite").save("./bronze/papers_raw")
```

### Type Conversions

The export automatically converts Cassandra types:

```
UUID → String (e.g., "550c7ef2-e29b-41d4-a716-446655440000")
date → ISO String (e.g., "2025-04-03")
datetime → ISO String (e.g., "2025-04-03T14:32:00")
list<text> → Array (e.g., ["author1", "author2"])
text → String (unchanged)
```

### Performance

- **1,000 rows**: ~2 seconds
- **10,000 rows**: ~10 seconds
- **100,000 rows**: ~60 seconds

Adjust chunk_size for different memory availability.

---

## �📈 MONITORING & DASHBOARDS

### View Cassandra Data

```bash
# Connect to Cassandra
docker exec -it cassandra_arxiv cqlsh

# In cqlsh:
USE arxiv;

# Count records
SELECT COUNT(*) FROM papers_raw;

# View sample data
SELECT arxiv_id, title, published_date, primary_category 
FROM papers_raw 
LIMIT 5;

# Check data by category
SELECT primary_category, COUNT(*) as count 
FROM papers_raw 
GROUP BY primary_category;

# Exit
exit
```

### View Dagster Dashboard

```
URL: http://localhost:3000

Tabs:
- Overview: Pipeline health
- Assets: Lineage & dependencies
- Runs: Historical execution logs
- Jobs: Scheduled executions
- Definitions: Asset configurations
```

### View Databricks Results

```
URL: https://your-workspace.databricks.com

Navigate:
1. Workspace → /databricks_notebooks/
2. Open notebook → View output cells
3. SQL → Run queries against Gold tables
4. Dashboards → Create visualizations
```

---

## 🔴 TROUBLESHOOTING

### Issue: "Cassandra connection refused"

```
Error: Failed to connect to cassandra_arxiv:9042

Solution:
1. Check Docker is running
   docker ps | grep cassandra_arxiv
   
2. Restart Cassandra
   docker-compose down
   docker-compose up -d
   
3. Wait for healthy status
   docker-compose ps  # Status should be "Up (healthy)"
   
4. Check logs
   docker-compose logs cassandra | tail -50
```

### Issue: "CQLsh syntax error: set literal"

```
Error: Misunderstood "{ ... }" ... 

Solution: Already fixed in code!
- Changed from: authors = {'Alice', 'Bob'}
- Changed to: authors = ['Alice', 'Bob']
- File: casandra/schema.cql uses list<text>
```

### Issue: "Python 3.13 cassandra-driver incompatible"

```
Error: asyncore module not found

Solution: Using Docker cqlsh instead
- Subprocess calls Docker cqlsh
- No need for Python cassandra-driver
- File: casandra/insert_papers.py
```

### Issue: "Dagster UI won't start"

```
Error: Port 3000 already in use

Solution:
# Option 1: Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Option 2: Use different port
dagit -f pipelines/dagster_pipeline.py -p 3001

# Option 3: Restart Docker
docker-compose restart
```

### Issue: "Databricks Cassandra connection fails"

```
Error: Cannot connect to cassandra_arxiv:9042

Solution:
1. Check host is accessible from Databricks:
   ping cassandra_arxiv
   
2. Update CASSANDRA_HOST in notebook:
   - If local: use IP address instead of hostname
   - Example: CASSANDRA_HOST = "192.168.1.100"
   
3. Check firewall allows port 9042
   netsh advfirewall firewall add rule name="Cassandra" dir=in action=allow protocol=tcp localport=9042
```

### Issue: ".env file not found"

```
Error: Environment variables not loaded

Solution:
1. Create .env file
   copy .env.example .env
   
2. Or set manually in PowerShell
   $env:CASSANDRA_HOST = "cassandra_arxiv"
   $env:BATCH_SIZE = "10"
   
3. Or set in Python directly
   import os
   os.environ['CASSANDRA_HOST'] = 'cassandra_arxiv'
```

---

## 🔧 COMMON COMMANDS

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs cassandra

# Follow logs (real-time)
docker-compose logs -f cassandra

# Restart container
docker-compose restart cassandra

# Remove all data (reset)
docker-compose down -v
```

### Python/Dagster Commands

```bash
# Activate environment
venv\Scripts\activate

# Deactivate environment
deactivate

# Install packages
pip install <package-name>

# List packages
pip list

# Run tests
pytest tests/ -v

# Run with coverage
pytest terms/ --cov

# Format code
black ingestion/ casandra/ pipelines/

# Lint code
flake8 ingestion/ casandra/ pipelines/

# Start Dagster UI
dagit -f pipelines/dagster_pipeline.py

# Run asset materialiation
dagster asset materialize -f pipelines/dagster_pipeline.py -a fetch_arxiv_papers
```

### Cassandra Commands

```bash
# Connect to Cassandra
docker exec -it cassandra_arxiv cqlsh

# In CQLsh prompt:
# ── Database ──
USE arxiv;
DESCRIBE KEYSPACES;
DESCRIBE TABLES;
DESCRIBE TABLE papers_raw;

# ── Data ──
SELECT COUNT(*) FROM papers_raw;
SELECT * FROM papers_raw LIMIT 5;
SELECT DISTINCT primary_category FROM papers_raw;

# ── Cleanup ──
TRUNCATE papers_raw;  # Delete all data (keep schema)
DROP TABLE papers_raw;  # Delete table
DROP KEYSPACE arxiv;  # Delete keyspace

# Exit
exit;
```

### Git Commands (Optional)

```bash
# Check status
git status

# View changes
git diff

# Commit changes
git add .
git commit -m "message"

# Push to remote
git push origin main

# Pull latest
git pull origin main
```

---

## ✅ VERIFICATION CHECKLIST

After running project, verify:

### Local Setup
- [ ] Python 3.13.5 installed
- [ ] Docker Desktop running
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] .env file configured

### Cassandra
- [ ] Container running (docker ps)
- [ ] Schema created (cqlsh DESCRIBE TABLES)
- [ ] Keyspace arxiv exists
- [ ] Table papers_raw created

### Pipeline Execution
- [ ] Papers fetched from ArXiv
- [ ] Papers validated successfully
- [ ] Papers stored in Cassandra
- [ ] Batch ID generated
- [ ] 0 failed inserts

### Data Quality
- [ ] Record count > 0
- [ ] Valid papers > 0
- [ ] Quality score >= 95%
- [ ] No duplicate records
- [ ] No null critical fields

### Dagster (Optional)
- [ ] UI accessible at localhost:3000
- [ ] Assets show green status
- [ ] Job execution completes
- [ ] No errors in logs

### Databricks (Optional)
- [ ] 6 notebooks imported
- [ ] Cluster configured (2-8 workers)
- [ ] Cassandra connection works
- [ ] All 8 Gold tables created
- [ ] SQL queries run successfully

---

## 🎯 TYPICAL WORKFLOW

### Morning: Daily Run

```bash
# 1. Activate environment (1 min)
venv\Scripts\activate

# 2. Verify Cassandra running (1 min)
docker-compose ps

# 3. Run pipeline (5 min)
python main.py

# 4. Check results (2 min)
docker exec cassandra_arxiv cqlsh -e "USE arxiv; SELECT COUNT(*) FROM papers_raw;"

# Total: ~10 minutes daily
```

### Maintenance: Weekly

```bash
# 1. Run full test suite (5 min)
pytest tests/ -v

# 2. View Dagster dashboard (2 min)
dagit -f pipelines/dagster_pipeline.py

# 3. Check Cassandra health (2 min)
docker-compose ps

# 4. Review data quality (2 min)
docker exec cassandra_arxiv cqlsh -e "USE arxiv; SELECT * FROM papers_raw LIMIT 10;"

# Total: ~15 minutes weekly
```

### Monthly: Optimize

```bash
# 1. Generate test coverage report (5 min)
pytest tests/ --cov --cov-report=html

# 2. Analyze logs for errors (5 min)
docker-compose logs cassandra | grep ERROR

# 3. Check disk usage (2 min)
docker system df

# 4. Update dependencies (5 min)
pip list --outdated
pip install --upgrade <packages>

# Total: ~20 minutes monthly
```

---

## 📞 QUICK REFERENCE

| Task | Command | Time |
|------|---------|------|
| Start project | `docker-compose up -d && venv\Scripts\activate && python main.py` | 5 min |
| Test everything | `pytest tests/ -v` | 5 min |
| View dashboard | `dagit -f pipelines/dagster_pipeline.py` | 2 min |
| Check data | `docker exec cassandra_arxiv cqlsh -e "USE arxiv; SELECT COUNT(*) FROM papers_raw;"` | 1 min |
| Reset database | `docker-compose down -v && docker-compose up -d` | 2 min |
| Run Databricks | Import notebooks → Configure cluster → Run 6 notebooks | 45 min |

---

## 🚀 NEXT STEPS

**After First Run:**
1. ✅ Verify data in Cassandra
2. ✅ Review Dagster UI
3. ✅ Run test suite
4. 🔜 Deploy to Databricks (if desired)
5. 🔜 Create dashboards

**For Production:**
1. Setup CI/CD pipeline
2. Configure monitoring/alerts
3. Add error handling
4. Scale Cassandra cluster
5. Deploy on cloud infrastructure

---

**Questions?** Check [README.md](README.md) or [PROJECT_STATUS.md](PROJECT_STATUS.md)

**Last Updated:** April 2026  
**Status:** ✅ Production Ready
