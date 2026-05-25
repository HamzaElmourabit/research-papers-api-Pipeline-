"""
FastAPI REST Server for ArXiv Papers Pipeline

Endpoints:
  GET  /api/papers             - Get all papers with pagination
  GET  /api/papers/{arxiv_id}  - Get paper by arXiv ID
  GET  /api/papers/search      - Search papers by title/abstract
  GET  /api/papers/category/{category} - Get papers by category
  GET  /api/stats              - Get pipeline statistics
  POST /api/export             - Trigger export to Parquet
  GET  /api/health             - Health check

Usage:
    python scripts/api_server.py

API Documentation:
    http://localhost:8000/docs          (Swagger UI)
    http://localhost:8000/redoc         (ReDoc)
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import json

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_logger

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# MODELS
# ============================================================================

class Paper(BaseModel):
    """Paper response model"""
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    primary_category: str
    published_date: str
    updated_date: str
    pdf_url: str
    ingestion_date: str


class PaperDetail(Paper):
    """Extended paper model with metadata"""
    batch_id: str
    ingested_at: str


class SearchQuery(BaseModel):
    """Search query model"""
    query: str
    limit: int = 10
    offset: int = 0


class PipelineStats(BaseModel):
    """Pipeline statistics model"""
    total_papers: int
    unique_categories: List[str]
    latest_ingestion_date: Optional[str]
    ingestion_count: int
    papers_per_category: dict


class ExportRequest(BaseModel):
    """Export request model"""
    output_dir: str = "/app/data/parquet"
    chunk_size: int = 400


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    cassandra_connected: bool
    timestamp: str


# ============================================================================
# CASSANDRA CONNECTION (WITH GRACEFUL FALLBACK)
# ============================================================================

class CassandraClient:
    """Cassandra connection manager with fallback to mock data"""
    
    def __init__(self):
        self.session = None
        self.cluster = None
        self.connected = False
        self.mock_data = self._load_mock_data()
    
    def _load_mock_data(self):
        """Load mock data for demo"""
        return {
            "papers": [
                {
                    "arxiv_id": "2605.21489v1",
                    "title": "Deep Learning for Natural Language Processing",
                    "abstract": "A comprehensive review of deep learning techniques in NLP",
                    "authors": ["John Doe", "Jane Smith"],
                    "categories": ["cs.CL", "cs.LG"],
                    "primary_category": "cs.CL",
                    "published_date": "2025-05-20",
                    "updated_date": "2025-05-20",
                    "pdf_url": "https://arxiv.org/pdf/2605.21489v1.pdf",
                    "ingestion_date": "2026-05-21",
                    "batch_id": "BATCH-20260521-103058-eb4a72f8",
                    "ingested_at": "2026-05-21T10:30:58.464236+00:00"
                },
                {
                    "arxiv_id": "2605.21486v1",
                    "title": "Transformer Models: State of the Art",
                    "abstract": "Analysis of modern transformer architectures",
                    "authors": ["Alice Johnson", "Bob Williams"],
                    "categories": ["cs.LG", "cs.AI"],
                    "primary_category": "cs.LG",
                    "published_date": "2025-05-19",
                    "updated_date": "2025-05-19",
                    "pdf_url": "https://arxiv.org/pdf/2605.21486v1.pdf",
                    "ingestion_date": "2026-05-21",
                    "batch_id": "BATCH-20260521-103058-eb4a72f8",
                    "ingested_at": "2026-05-21T10:30:58.464236+00:00"
                }
            ]
        }
    
    def connect(self):
        """Connect to Cassandra (with fallback to mock)"""
        try:
            from cassandra.cluster import Cluster
            
            host = os.getenv("CASSANDRA_HOST", "localhost")
            port = int(os.getenv("CASSANDRA_PORT", 9042))
            keyspace = os.getenv("CASSANDRA_KEYSPACE", "arxiv")
            
            logger.info(f"Attempting to connect to Cassandra at {host}:{port}")
            
            self.cluster = Cluster([host], port=port, connect_timeout=5)
            self.session = self.cluster.connect(keyspace)
            
            logger.info("✅ Connected to Cassandra successfully")
            self.connected = True
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Cassandra: {e}")
            logger.info("📦 Using mock data for demo purposes")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Cassandra"""
        if self.session:
            self.session.shutdown()
        if self.cluster:
            self.cluster.shutdown()
        logger.info("Disconnected from Cassandra")
    
    def get_papers(self, limit=10, category=None):
        """Get papers (real or mock)"""
        if self.connected:
            try:
                if category:
                    query = f"SELECT * FROM papers_raw WHERE primary_category = %s LIMIT {limit} ALLOW FILTERING"
                    return self.session.execute(query, [category])
                else:
                    query = f"SELECT * FROM papers_raw LIMIT {limit} ALLOW FILTERING"
                    return self.session.execute(query)
            except Exception as e:
                logger.error(f"Error querying Cassandra: {e}")
                return []
        else:
            # Return mock data
            papers = self.mock_data["papers"]
            if category:
                papers = [p for p in papers if category in p["categories"]]
            return papers[:limit]
    
    def get_paper_by_id(self, arxiv_id):
        """Get a single paper by ID"""
        if self.connected:
            try:
                query = "SELECT * FROM papers_raw WHERE arxiv_id = %s LIMIT 1"
                result = self.session.execute(query, [arxiv_id])
                return result[0] if result else None
            except Exception as e:
                logger.error(f"Error querying Cassandra: {e}")
                return None
        else:
            # Return mock data
            for paper in self.mock_data["papers"]:
                if paper["arxiv_id"] == arxiv_id:
                    return paper
            return None
    
    def get_stats(self):
        """Get statistics"""
        if self.connected:
            try:
                total = self.session.execute("SELECT COUNT(*) as count FROM papers_raw")[0].count
                categories = [row.primary_category for row in self.session.execute("SELECT DISTINCT primary_category FROM papers_raw")]
                return {
                    "total": total,
                    "categories": categories,
                    "connected": True
                }
            except Exception as e:
                logger.error(f"Error fetching stats: {e}")
                return None
        else:
            # Return mock stats
            papers = self.mock_data["papers"]
            categories = list(set(p["primary_category"] for p in papers))
            return {
                "total": len(papers),
                "categories": categories,
                "connected": False
            }


# ============================================================================
# INITIALIZATION
# ============================================================================

cassandra = CassandraClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown"""
    # Startup
    logger.info("🚀 Starting ArXiv API Server")
    cassandra.connect()
    
    yield
    
    # Shutdown
    logger.info("Shutting down ArXiv API Server")
    cassandra.disconnect()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="ArXiv Papers API",
    description="REST API for accessing ArXiv papers from Cassandra",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Check API and Cassandra health"""
    return HealthCheck(
        status="healthy" if cassandra.connected else "healthy (mock)",
        cassandra_connected=cassandra.connected,
        timestamp=datetime.utcnow().isoformat()
    )


# ============================================================================
# PAPERS ENDPOINTS
# ============================================================================

@app.get("/api/papers", response_model=List[Paper], tags=["Papers"])
async def get_papers(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None)
):
    """
    Get all papers with pagination
    
    Parameters:
    - limit: Number of papers to return (1-100)
    - offset: Pagination offset
    - category: Filter by category (e.g., cs.LG)
    """
    try:
        rows = cassandra.get_papers(limit, category)
        
        papers = []
        for row in rows:
            if isinstance(row, dict):
                paper_dict = row
            else:
                paper_dict = {
                    'arxiv_id': row.arxiv_id,
                    'title': row.title,
                    'abstract': row.abstract,
                    'authors': list(row.authors) if row.authors else [],
                    'categories': list(row.categories) if row.categories else [],
                    'primary_category': row.primary_category,
                    'published_date': str(row.published_date),
                    'updated_date': str(row.updated_date),
                    'pdf_url': row.pdf_url,
                    'ingestion_date': str(row.ingestion_date)
                }
            
            papers.append(Paper(**paper_dict))
        
        return papers
    
    except Exception as e:
        logger.error(f"Error fetching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/{arxiv_id}", response_model=PaperDetail, tags=["Papers"])
async def get_paper(arxiv_id: str):
    """
    Get a specific paper by arXiv ID
    
    Parameters:
    - arxiv_id: ArXiv paper ID (e.g., 2605.21489v1)
    """
    try:
        row = cassandra.get_paper_by_id(arxiv_id)
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found")
        
        if isinstance(row, dict):
            return PaperDetail(**row)
        else:
            return PaperDetail(
                arxiv_id=row.arxiv_id,
                title=row.title,
                abstract=row.abstract,
                authors=list(row.authors) if row.authors else [],
                categories=list(row.categories) if row.categories else [],
                primary_category=row.primary_category,
                published_date=str(row.published_date),
                updated_date=str(row.updated_date),
                pdf_url=row.pdf_url,
                ingestion_date=str(row.ingestion_date),
                batch_id=str(row.batch_id),
                ingested_at=row.ingested_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching paper {arxiv_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/search", response_model=List[Paper], tags=["Papers"])
async def search_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search papers by title or abstract
    """
    try:
        rows = cassandra.get_papers(100)
        
        matching_papers = []
        for row in rows:
            if isinstance(row, dict):
                row_dict = row
            else:
                row_dict = {
                    'arxiv_id': row.arxiv_id,
                    'title': row.title,
                    'abstract': row.abstract,
                    'authors': list(row.authors) if row.authors else [],
                    'categories': list(row.categories) if row.categories else [],
                    'primary_category': row.primary_category,
                    'published_date': str(row.published_date),
                    'updated_date': str(row.updated_date),
                    'pdf_url': row.pdf_url,
                    'ingestion_date': str(row.ingestion_date)
                }
            
            if q.lower() in row_dict['title'].lower() or q.lower() in row_dict['abstract'].lower():
                matching_papers.append(Paper(**row_dict))
        
        return matching_papers[:limit]
    
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/category/{category}", response_model=List[Paper], tags=["Papers"])
async def get_papers_by_category(
    category: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get papers filtered by category
    
    Examples:
    - cs.AI: Artificial Intelligence
    - cs.LG: Machine Learning
    - cs.CV: Computer Vision
    - cs.CL: Computational Linguistics
    - stat.ML: Statistics / Machine Learning
    """
    try:
        rows = cassandra.get_papers(limit, category)
        
        papers = []
        for row in rows:
            if isinstance(row, dict):
                papers.append(Paper(**row))
            else:
                papers.append(Paper(
                    arxiv_id=row.arxiv_id,
                    title=row.title,
                    abstract=row.abstract,
                    authors=list(row.authors) if row.authors else [],
                    categories=list(row.categories) if row.categories else [],
                    primary_category=row.primary_category,
                    published_date=str(row.published_date),
                    updated_date=str(row.updated_date),
                    pdf_url=row.pdf_url,
                    ingestion_date=str(row.ingestion_date)
                ))
        
        return papers
    
    except Exception as e:
        logger.error(f"Error fetching papers by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATS ENDPOINT
# ============================================================================

@app.get("/api/stats", response_model=PipelineStats, tags=["Statistics"])
async def get_stats():
    """
    Get pipeline statistics and data summary
    """
    try:
        stats = cassandra.get_stats()
        
        if not stats:
            raise HTTPException(status_code=500, detail="Failed to fetch stats")
        
        papers_per_cat = {}
        for cat in stats["categories"]:
            rows = cassandra.get_papers(100, cat)
            papers_per_cat[cat] = len(rows)
        
        return PipelineStats(
            total_papers=stats["total"],
            unique_categories=stats["categories"],
            latest_ingestion_date="2026-05-21",
            ingestion_count=1,
            papers_per_category=papers_per_cat
        )
    
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXPORT ENDPOINT
# ============================================================================

@app.post("/api/export", tags=["Export"])
async def trigger_export(request: ExportRequest):
    """
    Trigger manual export to Parquet
    """
    try:
        import subprocess
        
        output_dir = request.output_dir
        chunk_size = request.chunk_size
        
        logger.info(f"Triggering export to {output_dir}")
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Run export script asynchronously (non-blocking)
        subprocess.Popen([
            sys.executable,
            "scripts/export_to_parquet.py",
            f"--output-dir {output_dir}",
            f"--chunk-size {chunk_size}"
        ])
        
        return {
            "status": "Export triggered",
            "output_dir": output_dir,
            "chunk_size": chunk_size,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error triggering export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "ArXiv Papers API v1.0",
        "status": "running",
        "cassandra_connected": cassandra.connected,
        "docs": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc",
        "endpoints": {
            "papers": "/api/papers",
            "search": "/api/papers/search?q=query",
            "by_id": "/api/papers/{arxiv_id}",
            "by_category": "/api/papers/category/{category}",
            "stats": "/api/stats",
            "export": "/api/export",
            "health": "/api/health"
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"🚀 Starting API server on port {port}")
    logger.info(f"📚 Swagger UI: http://localhost:{port}/docs")
    logger.info(f"📖 ReDoc: http://localhost:{port}/redoc")
    logger.info(f"🏠 Home: http://localhost:{port}/")
    logger.info("")
    
    uvicorn.run(
        "scripts.api_server:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
