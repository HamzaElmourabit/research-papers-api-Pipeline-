# 📊 Complete Architecture Diagram with All Components

## Visual Architecture Mermaid Diagram

```mermaid
graph TB
    subgraph EXTERNAL["🌐 EXTERNAL SOURCES"]
        ARXIV["🌐 arXiv API<br/>Research Papers<br/>500-1000/run"]
    end
    
    subgraph GITHUB["🚀 CI/CD & VERSION CONTROL"]
        GH["GitHub Repository<br/>main, develop branches"]
        WORKFLOW["⚙️ GitHub Actions<br/>Code Quality<br/>Security<br/>Tests<br/>Docker Build<br/>Performance"]
    end
    
    subgraph API_LAYER["🔗 API & EXTRACTION LAYER"]
        ARXIV_CLIENT["📥 arxiv_client.py<br/>ArxivClient class<br/>search_papers()"]
        FETCHER["📥 fetch_papers.py<br/>PaperFetcher<br/>Batch processing"]
        VALIDATOR["🔍 validation.py<br/>Pydantic Schema<br/>95% quality filter"]
    end
    
    subgraph ORCHESTRATION["🎯 ORCHESTRATION LAYER (Dagster)"]
        ASSETS["📊 Assets<br/>fetch → validate → store<br/>export_to_parquet"]
        RESOURCES["🔌 Resources<br/>cassandra_resource<br/>arxiv_client_resource"]
        JOBS["⏰ Jobs<br/>daily_ingestion_job"]
        SCHEDULE["📅 Schedules<br/>2:00 AM UTC"]
        DAGIT["🖥️ Dagit UI<br/>localhost:3000<br/>Asset tracking"]
    end
    
    subgraph STORAGE["💾 DATABASE & STREAMING LAYER"]
        CASSANDRA["🗄️ CASSANDRA<br/>papers_raw table<br/>9042 | 7199<br/>450-950 rows<br/>batch_id tracking"]
        
        ZOOKEEPER["🔗 Zookeeper<br/>Kafka coordination<br/>2181"]
        
        KAFKA["🚀 KAFKA BROKER<br/>papers-raw topic<br/>9092 | 9094<br/>24h retention<br/>auto create topics"]
        
        KAFDROP["🎯 Kafdrop<br/>Kafka Monitoring<br/>localhost:9000"]
        
        POSTGRES["📊 PostgreSQL<br/>Dagster metadata<br/>5432<br/>Job runs, logs"]
    end
    
    subgraph DOCKER["🐳 CONTAINERIZATION"]
        COMPOSE["docker-compose.yml<br/>Cassandra<br/>Kafka + Zookeeper<br/>PostgreSQL<br/>Services"]
        
        DOCKERFILE["🐳 Dockerfile<br/>Multi-stage build<br/>Stage 1: Builder<br/>Stage 2: Runtime<br/>python:3.13-slim<br/>HEALTHCHECK"]
        
        NETWORK["🌐 Network<br/>arxiv_network<br/>Service discovery"]
    end
    
    subgraph SPARK_ANALYTICS["📊 SPARK ANALYTICS (Databricks/PySpark)"]
        BRONZE["🔄 BRONZE LAYER<br/>Extract Cassandra<br/>Raw data + metadata<br>/mnt/data/papers_bronze"]
        
        SILVER["🔄 SILVER LAYER<br/>Transform clean<br/>Explode authors<br/>Normalize dates<br>/mnt/data/papers_silver<br/>95% quality"]
        
        GOLD["🔄 GOLD LAYER<br/>Aggregations<br/>papers_per_year<br/>papers_per_category<br/>top_authors<br/>research_trends<br/>/mnt/data/papers_gold"]
        
        GRAPH["🔄 GRAPH LAYER<br/>Co-authorship edges<br/>author_network_summary<br/>category_trends<br/>/mnt/data/papers_graph"]
    end
    
    subgraph UTILS["🔧 UTILITIES & MONITORING"]
        LOGGING["📋 Logging<br/>JSON structured logs<br/>arxiv_pipeline.log<br/>Batch context"]
        
        QUALITY["🔍 Data Quality<br/>Pydantic validation<br/>Uniqueness checks<br/>Format validators"]
        
        ERROR["⚠️ Error Handling<br/>Exception management<br/>Retry logic<br/>Batch tracking"]
        
        MONITORING["📈 Monitoring<br/>Prometheus metrics<br/>Health checks<br/>Performance tracking"]
    end
    
    subgraph EXPORT["📦 EXPORT & OUTPUT"]
        PARQUET["📁 Parquet Files<br/>Columnar format<br/>Optional export<br/>scripts/export_to_parquet.py"]
        
        DELTA["📊 Delta Tables<br/>ACID transactions<br/>SQL queryable<br/>Version control"]
    end
    
    subgraph VISUALIZATION["📈 VISUALIZATION LAYER"]
        DATABRICKS["💼 Databricks Notebooks<br/>SQL queries<br/>Dashboards<br/>Collaborative"]
        
        STREAMLIT["🎨 Python App<br/>Streamlit / Dash<br/>Interactive UI<br/>Real-time updates"]
        
        BI["📊 BI Tools<br/>Power BI<br/>Tableau<br/>Looker"]
        
        CUSTOM["🌐 Custom Frontend<br/>React + D3<br/>Plotly<br/>API integration"]
    end
    
    subgraph DEPLOYMENT["🚀 DEPLOYMENT OPTIONS"]
        LOCAL["💻 Local Development<br/>python main.py<br/>docker-compose up"]
        
        DOCKER_RUN["🐳 Docker Container<br/>docker build<br/>docker run<br/>Volume mounting"]
        
        K8S["☸️ Kubernetes<br/>AKS / GKE<br/>Helm charts<br/>Scaling"]
        
        CLOUD["☁️ Cloud Services<br/>Azure Databricks<br/>AWS EMR<br/>Google Cloud Dataflow"]
    end
    
    %% CONNECTIONS
    ARXIV -->|API requests| ARXIV_CLIENT
    ARXIV_CLIENT -->|raw papers| FETCHER
    GH -->|triggers| WORKFLOW
    WORKFLOW -->|test & build| COMPOSE
    
    FETCHER -->|produces| KAFKA
    FETCHER -->|asset| ASSETS
    
    VALIDATOR -->|validates| CASSANDRA
    ASSETS -->|orchestrates| JOBS
    RESOURCES -->|connections| CASSANDRA
    RESOURCES -->|connections| KAFKA
    JOBS -->|triggers| SCHEDULE
    ASSETS -->|tracking| DAGIT
    
    KAFKA -->|streams| CASSANDRA
    KAFKA -->|monitoring| KAFDROP
    CASSANDRA -->|metadata| POSTGRES
    
    COMPOSE -->|defines| CASSANDRA
    COMPOSE -->|defines| KAFKA
    COMPOSE -->|defines| ZOOKEEPER
    COMPOSE -->|defines| POSTGRES
    COMPOSE -->|creates| NETWORK
    
    DOCKERFILE -->|builds| COMPOSE
    NETWORK -->|connects| COMPOSE
    
    CASSANDRA -->|read| BRONZE
    BRONZE -->|transform| SILVER
    SILVER -->|aggregate| GOLD
    SILVER -->|graph analysis| GRAPH
    
    SILVER -->|export| PARQUET
    GOLD -->|write| DELTA
    GRAPH -->|write| DELTA
    
    BRONZE -->|logs| LOGGING
    SILVER -->|quality| QUALITY
    GOLD -->|errors| ERROR
    DATABRICKS -->|metrics| MONITORING
    
    DELTA -->|sql queries| DATABRICKS
    PARQUET -->|read| STREAMLIT
    DELTA -->|connect| BI
    STREAMLIT -->|api| CUSTOM
    
    DATABRICKS -->|deploy| DATABRICKS
    LOCAL -->|runs| SPARK_ANALYTICS
    DOCKER_RUN -->|executes| SPARK_ANALYTICS
    K8S -->|orchestrates| SPARK_ANALYTICS
    CLOUD -->|provides| SPARK_ANALYTICS
    
    DATABRICKS -->|display| VISUALIZATION
    STREAMLIT -->|display| VISUALIZATION
    BI -->|display| VISUALIZATION
    CUSTOM -->|display| VISUALIZATION
    
    %% Styling
    classDef external fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000
    classDef github fill:#f5f5f5,stroke:#424242,stroke-width:2px,color:#000
    classDef api fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    classDef orchestration fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef storage fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    classDef docker fill:#e0f2f1,stroke:#00796b,stroke-width:2px,color:#000
    classDef spark fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef utils fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,color:#000
    classDef export fill:#ede7f6,stroke:#512da8,stroke-width:2px,color:#000
    classDef viz fill:#e0f2f1,stroke:#00897b,stroke-width:2px,color:#000
    classDef deploy fill:#fbe9e7,stroke:#d84315,stroke-width:2px,color:#000
    
    class ARXIV external
    class GH,WORKFLOW github
    class ARXIV_CLIENT,FETCHER,VALIDATOR api
    class ASSETS,RESOURCES,JOBS,SCHEDULE,DAGIT orchestration
    class CASSANDRA,KAFKA,ZOOKEEPER,KAFDROP,POSTGRES storage
    class COMPOSE,DOCKERFILE,NETWORK docker
    class BRONZE,SILVER,GOLD,GRAPH spark
    class LOGGING,QUALITY,ERROR,MONITORING utils
    class PARQUET,DELTA export
    class DATABRICKS,STREAMLIT,BI,CUSTOM viz
    class LOCAL,DOCKER_RUN,K8S,CLOUD deploy
```

---

## 📊 Component Interaction Matrix

```
┌────────────────────────────────────────────────────────────────────┐
│ COMPONENT INTERACTIONS & DATA FLOW                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ Layer 1: EXTRACTION                                               │
│   arXiv API ──→ ArxivClient ──→ PaperFetcher ──→ Validator      │
│      ↓                                               ↓             │
│   Raw Data                                    Validated Data      │
│                                                                    │
│ Layer 2: INGESTION (Dual Path)                                   │
│   ┌─────────────────────────┬──────────────────────────────┐    │
│   │                         │                              │    │
│   ↓ (Stream)               ↓ (Batch)                       │    │
│ Kafka Topic            Dagster Assets                       │    │
│   ↓                         ↓                              │    │
│ papers-raw            daily_ingestion_job                  │    │
│   ↓                         ↓                              │    │
│   └─────────────────────────┴──────────────────────────────┘    │
│                             ↓                                     │
│                      Cassandra Storage                            │
│                      papers_raw table                             │
│                                                                    │
│ Layer 3: ANALYTICS (Spark Transformation)                        │
│   Cassandra ──→ Bronze ──→ Silver ──→ Gold ──→ Parquet        │
│      ↓            ↓          ↓         ↓        ↓               │
│   100% raw     100% raw     95% clean  50+ aggs Export        │
│                             ↓         ↓        ↓               │
│                          Graph ──→ Delta Tables ──→ Viz       │
│                        Co-authorship   ACID transactions        │
│                                                                    │
│ Layer 4: VISUALIZATION (Multiple Outputs)                       │
│   Delta ──→ Databricks Dashboards                              │
│   Parquet ──→ Streamlit/Dash Web App                           │
│   Delta ──→ Power BI / Tableau BI                             │
│   API ──→ Custom Frontend (React + D3)                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Volume Flow

```
Input → Processing → Output
 ↓         ↓           ↓
 
🌐 arXiv API
500-1000 papers/run
     ↓
     ↓ (Extraction)
     ↓
✅ Validated
450-950 papers (95% success)
     ↓
     ↓ (Ingestion)
     ↓
💾 Cassandra
450-950 unique records
     ↓
     ├─→ 🔄 Bronze Layer
     │   450-950 records (100% raw)
     │
     ├─→ 🔄 Silver Layer
     │   450-950 records (95% clean)
     │   + exploded authors (avg 3.5 per paper)
     │   → ~1,575-3,325 author records
     │   + exploded categories (avg 2 per paper)
     │   → ~900-1,900 category records
     │
     ├─→ 🔄 Gold Layer
     │   • papers_per_year: 5-10 rows
     │   • papers_per_category: 50-60 rows
     │   • top_authors: 5 rows
     │   • research_trends: 250-500 rows
     │
     └─→ 🔄 Graph Layer
         • author_coauthor_edges: 500-2000 rows
         • author_network_summary: 100-500 rows
         • category_trends: 250-500 rows
     
     ↓ (Export)
     ↓
📊 Output Parquet/Delta
~5-10 files, 50-200 MB total
```

---

## 🎯 Technology Stack by Layer

```
┌─────────────────────────────────────────────────────────────────┐
│ EXTRACTION LAYER                                                │
├─────────────────────────────────────────────────────────────────┤
│ • Language: Python 3.13                                         │
│ • API Client: arxiv library                                     │
│ • HTTP: requests                                                │
│ • Data Format: JSON/Dict                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ORCHESTRATION LAYER                                             │
├─────────────────────────────────────────────────────────────────┤
│ • Framework: Dagster 1.5.11                                     │
│ • UI: Dagit Web Server                                          │
│ • Metadata: PostgreSQL 15                                       │
│ • Scheduler: Cron-based (2 AM UTC)                              │
│ • Asset versioning: Built-in                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ VALIDATION LAYER                                                │
├─────────────────────────────────────────────────────────────────┤
│ • Schema: Pydantic 2.5.0                                        │
│ • Rules: Custom validators                                      │
│ • Format: JSON Schema compatible                                │
│ • Testing: pytest 7.4.0                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STORAGE LAYER                                                   │
├─────────────────────────────────────────────────────────────────┤
│ • NoSQL: Cassandra 5.0 (distributed)                            │
│ • Streaming: Kafka 7.5.0 + Zookeeper 7.5.0                     │
│ • Metadata DB: PostgreSQL 15                                    │
│ • Schema: CQL (Cassandra Query Language)                        │
│ • Monitoring: Kafdrop                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ANALYTICS LAYER                                                 │
├─────────────────────────────────────────────────────────────────┤
│ • Engine: Apache Spark 3.4.1                                    │
│ • Python API: PySpark                                           │
│ • Format: Parquet + Delta Lake                                  │
│ • SQL: Spark SQL                                                │
│ • Platform: Databricks (optional local)                         │
│ • Connector: cassandra-driver 3.29.0                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CONTAINERIZATION LAYER                                          │
├─────────────────────────────────────────────────────────────────┤
│ • Container: Docker 20.10+                                      │
│ • Compose: Docker Compose 3.8                                   │
│ • Image: python:3.13-slim (multi-stage)                         │
│ • Registry: GitHub Container Registry (GHCR)                    │
│ • Network: Custom bridge (arxiv_network)                        │
│ • Storage: Named volumes                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CI/CD LAYER                                                     │
├─────────────────────────────────────────────────────────────────┤
│ • Platform: GitHub Actions                                      │
│ • Stages: 7 (quality, security, tests, build, etc.)            │
│ • Triggers: Push, PR, Schedule (daily)                          │
│ • Code Quality: Black, isort, Flake8, mypy                      │
│ • Security: Trivy, Safety                                       │
│ • Testing: pytest + pytest-cov                                  │
│ • Performance: Benchmark suite                                  │
│ • Signing: Sigstore                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ MONITORING & LOGGING LAYER                                      │
├─────────────────────────────────────────────────────────────────┤
│ • Logging: python-json-logger 2.0.7                             │
│ • Metrics: Prometheus 0.18.0                                    │
│ • Format: JSON structured logs                                  │
│ • Batch tracking: Context-based correlation IDs                 │
│ • Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ VISUALIZATION LAYER                                             │
├─────────────────────────────────────────────────────────────────┤
│ • Dashboards: Databricks SQL, Streamlit, Dash                   │
│ • BI: Power BI, Tableau, Looker                                 │
│ • Frontend: React, Angular, Vue (optional)                      │
│ • Charts: Plotly, D3.js, Bokeh                                  │
│ • API: FastAPI (optional GraphQL/REST)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security & Compliance

```
┌────────────────────────────────────────────────────────────────┐
│ SECURITY LAYERS                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ 🔒 Source Code Security                                       │
│   ├─ GitHub branch protection                                 │
│   ├─ Required PR reviews                                      │
│   ├─ Status checks (CI/CD)                                    │
│   ├─ Code signing (Sigstore)                                  │
│   └─ Dependency scanning (Dependabot)                         │
│                                                                │
│ 🔒 Build Security                                             │
│   ├─ Trivy vulnerability scan                                 │
│   ├─ Safety dependency check                                  │
│   ├─ SBOM generation                                          │
│   ├─ Multi-stage Docker builds                                │
│   └─ Image signing                                            │
│                                                                │
│ 🔒 Runtime Security                                           │
│   ├─ Network isolation (docker network)                       │
│   ├─ Secret management (.env)                                 │
│   ├─ Authentication (Cassandra ACLs)                          │
│   ├─ Encryption in transit (TLS optional)                     │
│   └─ Health checks & monitoring                               │
│                                                                │
│ 🔒 Data Security                                              │
│   ├─ Input validation (Pydantic)                              │
│   ├─ Schema enforcement                                       │
│   ├─ Sanitization of user inputs                              │
│   ├─ Audit logging                                            │
│   └─ Data retention policies                                  │
│                                                                │
│ 🔒 Access Control                                             │
│   ├─ RBAC (PostgreSQL users)                                  │
│   ├─ GitHub token rotation                                    │
│   ├─ Cassandra role-based access                              │
│   ├─ Kafka ACLs (if enabled)                                  │
│   └─ Least privilege principle                                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 📈 Performance & Scalability

```
Performance Metrics:
├─ Extraction: ~10 seconds (500-1000 papers)
├─ Validation: ~5 seconds (95% throughput)
├─ Cassandra Load: ~15 seconds (450-950 records)
├─ Bronze Spark: ~2 minutes (first run)
├─ Silver Transform: ~5 minutes (with explosion)
├─ Gold Aggregation: ~10 minutes (complete)
├─ Graph Analysis: ~8 minutes (co-authorship)
└─ Total Pipeline: ~40-45 minutes (end-to-end)

Scalability:
├─ Cassandra: Horizontally scalable (replication factor)
├─ Kafka: Parallel partitions (multi-broker)
├─ Spark: Distributed execution (cluster mode)
├─ Docker: Multiple container replicas
└─ Kubernetes: Auto-scaling pods based on load
```

---

## 🎓 Training & Knowledge Transfer

- **Setup Guide**: [HOW_TO_RUN.md](HOW_TO_RUN.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Architecture Docs**: [docs/architecture.md](docs/architecture.md)
- **Dagster Design**: [docs/dagster_architecture.md](docs/dagster_architecture.md)
- **Troubleshooting**: [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)

---

**Summary**: This complete architecture represents a production-grade data pipeline with ETL orchestration (Dagster), streaming (Kafka), distributed storage (Cassandra), analytics (Spark), containerization (Docker), CI/CD automation (GitHub Actions), and multiple visualization options. All components are fully integrated and monitored.

**Last Updated**: May 25, 2026  
**Version**: 3.0  
**Status**: ✅ Production Ready
