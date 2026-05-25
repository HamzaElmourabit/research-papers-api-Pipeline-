import os
os.environ['LIBEV_FALLBACK_LOOP'] = '1'

from casandra.insert_papers import insert_papers

# Test with sample paper data
test_papers = [
    {
        "arxiv_id": "2401.00001",
        "title": "Test Paper 1",
        "abstract": "This is a test paper",
        "authors": ["John Doe"],
        "categories": ["cs.AI"],
        "primary_category": "cs.AI",
        "published_date": "2024-01-01T00:00:00Z",
        "updated_date": "2024-01-01T00:00:00Z",
        "pdf_url": "https://arxiv.org/pdf/2401.00001",
        "raw_json": "{}",
        "ingested_at": "2024-01-01T00:00:00Z"
    }
]

try:
    print("Attempting insert...")
    result = insert_papers(test_papers)
    print("Result:", result)
    print("✅ Insert successful!")
    
    # Query Cassandra to verify
    from cassandra.cluster import Cluster
    cluster = Cluster(['127.0.0.1'])
    session = cluster.connect('arxiv')
    rows = session.execute('SELECT COUNT(*) FROM papers_raw')
    print(f"papers_raw count: {rows.one()[0]}")
    cluster.shutdown()
    
except Exception as e:
    print(f"❌ Error: {str(e)[:500]}")
    import traceback
    traceback.print_exc()
