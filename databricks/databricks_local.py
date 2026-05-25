"""
Databricks ELT Pipeline (Local/Python Implementation)
Bronze → Silver → Gold Layer Transformations
Using Pandas instead of PySpark for compatibility on Windows
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import os

# Configuration
CASSANDRA_HOST = "127.0.0.1"
CASSANDRA_PORT = 9042
CASSANDRA_KEYSPACE = "arxiv"
CASSANDRA_TABLE = "papers_raw"

OUTPUT_DIR = Path("data/parquet")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 1. BRONZE LAYER: Extract & Load
# ============================================================================

def load_from_cassandra():
    """Load data from Cassandra using cqlsh via Docker"""
    import subprocess
    import json
    
    print("\n" + "="*70)
    print("🥉 BRONZE LAYER: Extracting from Cassandra")
    print("="*70)
    
    # Query Cassandra via Docker cqlsh
    query = f"SELECT * FROM {CASSANDRA_KEYSPACE}.{CASSANDRA_TABLE};"
    
    try:
        result = subprocess.run(
            ["docker", "exec", "cassandra_arxiv", "cqlsh", "-e", query],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Query failed: {result.stderr}")
            return None
            
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            print("❌ No data returned from Cassandra")
            return None
        
        # Parse output (simple CSV format from cqlsh)
        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
        data = []
        
        for line in lines[2:]:
            if line.strip() and '|' in line:
                values = [v.strip() for v in line.split('|')[1:-1]]
                if len(values) == len(headers):
                    row = dict(zip(headers, values))
                    data.append(row)
        
        if not data:
            print("❌ No rows parsed from Cassandra output")
            return None
            
        df = pd.DataFrame(data)
        print(f"✅ Loaded {len(df)} rows from Cassandra")
        return df
        
    except Exception as e:
        print(f"❌ Error loading from Cassandra: {e}")
        return None


def create_bronze_layer():
    """Create Bronze layer with metadata"""
    
    # Load from Cassandra
    df = load_from_cassandra()
    if df is None or len(df) == 0:
        print("⚠️  No data to process. Creating sample Bronze layer...")
        # Create a minimal sample for testing
        df = pd.DataFrame({
            'batch_id': ['test_batch_1'],
            'arxiv_id': ['2024.00001'],
            'title': ['Sample Paper'],
            'abstract': ['Sample abstract text'],
            'authors': [['Author 1', 'Author 2']],
            'categories': [['cs.AI', 'cs.LG']],
            'primary_category': ['cs.AI'],
            'published_date': [datetime(2024, 1, 1)],
            'updated_date': [datetime(2024, 1, 1)],
            'pdf_url': ['http://example.com/sample.pdf'],
            'raw_json': ['{}'],
            'ingestion_date': [datetime.now()],
            'processing_status': ['completed'],
            'notes': ['sample']
        })
    
    # Add Bronze metadata columns
    df['_ingestion_timestamp'] = datetime.now()
    df['_source_system'] = 'cassandra_arxiv'
    df['_record_hash'] = (df['arxiv_id'].astype(str) + df['title'].astype(str)).apply(
        lambda x: __import__('hashlib').md5(x.encode()).hexdigest()
    )
    
    # Save Bronze layer
    bronze_path = OUTPUT_DIR / "papers_bronze.parquet"
    df.to_parquet(bronze_path, index=False)
    
    print(f"\n✅ Bronze Layer saved to {bronze_path}")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {list(df.columns)}")
    
    return df


# ============================================================================
# 2. SILVER LAYER: Clean & Transform
# ============================================================================

def create_silver_layer(bronze_df):
    """Create Silver layer with data quality improvements"""
    
    print("\n" + "="*70)
    print("🥈 SILVER LAYER: Cleaning & Transforming")
    print("="*70)
    
    df = bronze_df.copy()
    
    # 1. Remove duplicates
    original_count = len(df)
    df = df.drop_duplicates(subset=['arxiv_id'], keep='first')
    print(f"✅ Deduplicated: {original_count} → {len(df)} rows")
    
    # 2. Trim text columns
    text_cols = ['title', 'abstract', 'primary_category']
    for col in text_cols:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # 3. Parse dates
    date_cols = ['published_date', 'updated_date', 'ingestion_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # 4. Extract year
    if 'published_date' in df.columns:
        df['publication_year'] = df['published_date'].dt.year
    
    # 5. Calculate metrics
    if 'title' in df.columns:
        df['title_length'] = df['title'].str.len().fillna(0).astype(int)
    if 'abstract' in df.columns:
        df['abstract_length'] = df['abstract'].str.len().fillna(0).astype(int)
    
    # 6. Parse array columns (authors, categories)
    if 'authors' in df.columns:
        df['authors'] = df['authors'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
        )
        df['authors_count'] = df['authors'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    if 'categories' in df.columns:
        df['categories'] = df['categories'].apply(
            lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
        )
        df['categories_count'] = df['categories'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    # 7. Explode authors (one row per author)
    if 'authors' in df.columns:
        df_exploded = df.explode('authors', ignore_index=False).copy()
        df_exploded = df_exploded.rename(columns={'authors': 'author'})
    else:
        df_exploded = df.copy()
    
    # Save Silver layer
    silver_path = OUTPUT_DIR / "papers_silver.parquet"
    df_exploded.to_parquet(silver_path, index=False)
    
    print(f"\n✅ Silver Layer saved to {silver_path}")
    print(f"   Rows: {len(df_exploded)} (exploded authors)")
    print(f"   Unique papers: {df_exploded['arxiv_id'].nunique() if 'arxiv_id' in df_exploded.columns else 'N/A'}")
    
    return df_exploded


# ============================================================================
# 3. GOLD LAYER: Analytical Tables
# ============================================================================

def create_gold_layer(silver_df):
    """Create Gold layer with analytical tables"""
    
    print("\n" + "="*70)
    print("🥇 GOLD LAYER: Creating Analytical Tables")
    print("="*70)
    
    gold_tables = {}
    
    # 1. Papers by Year
    if 'publication_year' in silver_df.columns and 'arxiv_id' in silver_df.columns:
        papers_by_year = silver_df.groupby('publication_year').agg({
            'arxiv_id': 'nunique',
            'abstract_length': 'mean' if 'abstract_length' in silver_df.columns else 'count'
        }).reset_index()
        papers_by_year.columns = ['publication_year', 'paper_count', 'avg_abstract_length']
        gold_tables['papers_by_year'] = papers_by_year
        print(f"\n✅ Table 1: Papers by Year ({len(papers_by_year)} years)")
    
    # 2. Authors frequency
    if 'author' in silver_df.columns:
        authors_freq = silver_df.groupby('author').agg({
            'arxiv_id': 'nunique'
        }).reset_index().sort_values('arxiv_id', ascending=False)
        authors_freq.columns = ['author', 'paper_count']
        gold_tables['top_authors'] = authors_freq.head(50)
        print(f"✅ Table 2: Top 50 Authors ({len(gold_tables['top_authors'])} entries)")
    
    # 3. Categories distribution
    if 'categories' in silver_df.columns and 'arxiv_id' in silver_df.columns:
        categories_data = []
        for idx, row in silver_df.iterrows():
            if isinstance(row['categories'], list):
                for cat in row['categories']:
                    categories_data.append({'category': cat, 'arxiv_id': row['arxiv_id']})
        
        if categories_data:
            categories_df = pd.DataFrame(categories_data)
            categories_dist = categories_df.groupby('category').agg({
                'arxiv_id': 'nunique'
            }).reset_index().sort_values('arxiv_id', ascending=False)
            categories_dist.columns = ['category', 'paper_count']
            gold_tables['categories_distribution'] = categories_dist
            print(f"✅ Table 3: Categories Distribution ({len(gold_tables['categories_distribution'])} categories)")
    
    # 4. Publication trends
    if 'publication_year' in silver_df.columns and 'primary_category' in silver_df.columns:
        trends = silver_df.groupby(['publication_year', 'primary_category']).agg({
            'arxiv_id': 'nunique'
        }).reset_index()
        trends.columns = ['publication_year', 'primary_category', 'paper_count']
        gold_tables['publication_trends'] = trends.sort_values(['publication_year', 'paper_count'], ascending=[True, False])
        print(f"✅ Table 4: Publication Trends ({len(gold_tables['publication_trends'])} entries)")
    
    # 5. Abstract statistics
    if 'abstract_length' in silver_df.columns:
        abstract_stats = pd.DataFrame({
            'metric': ['min', 'max', 'mean', 'median'],
            'value': [
                silver_df['abstract_length'].min(),
                silver_df['abstract_length'].max(),
                silver_df['abstract_length'].mean(),
                silver_df['abstract_length'].median()
            ]
        })
        gold_tables['abstract_statistics'] = abstract_stats
        print(f"✅ Table 5: Abstract Statistics")
    
    # Save all Gold tables
    for table_name, table_df in gold_tables.items():
        path = OUTPUT_DIR / f"{table_name}.parquet"
        table_df.to_parquet(path, index=False)
        print(f"   └─ {table_name}: {len(table_df)} rows → {path}")
    
    print(f"\n✅ Gold Layer: {len(gold_tables)} analytical tables created")
    return gold_tables


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 DATABRICKS ELT PIPELINE (Local Python Implementation)")
    print("="*70)
    
    try:
        # Bronze Layer
        bronze_df = create_bronze_layer()
        
        # Silver Layer
        silver_df = create_silver_layer(bronze_df)
        
        # Gold Layer
        gold_tables = create_gold_layer(silver_df)
        
        # Summary
        print("\n" + "="*70)
        print("✅ PIPELINE COMPLETE")
        print("="*70)
        print(f"\n📊 Output Statistics:")
        print(f"   • Bronze records: {len(bronze_df)}")
        print(f"   • Silver records: {len(silver_df)}")
        print(f"   • Gold tables: {len(gold_tables)}")
        print(f"   • Output directory: {OUTPUT_DIR.absolute()}")
        
        # List output files
        print(f"\n📁 Generated Files:")
        for parquet_file in sorted(OUTPUT_DIR.glob("*.parquet")):
            size_mb = parquet_file.stat().st_size / (1024*1024)
            print(f"   ✓ {parquet_file.name} ({size_mb:.2f} MB)")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
