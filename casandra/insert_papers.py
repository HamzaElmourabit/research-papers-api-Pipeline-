import uuid
import datetime
from cassandra.query import BatchStatement, ConsistencyLevel

from casandra.cassandra_connection import CassandraConnection


CHUNK_SIZE = 25  # Cassandra recommends keeping batches small


def _prepare_insert(session):
    """Prepares the INSERT statement once and reuses it for all inserts."""
    return session.prepare("""
        INSERT INTO papers_raw (
            batch_id,
            ingestion_date,               
            arxiv_id,
            title,
            abstract,
            authors,
            categories,
            primary_category,
            published_date,
            updated_date,
            pdf_url,
            raw_json,
            ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)


def _chunk(papers: list, size: int):
    """Splits a list into chunks of a given size."""
    for i in range(0, len(papers), size):
        yield papers[i : i + size]


def insert_papers(papers: list[dict], chunk_size: int = CHUNK_SIZE) -> dict:
    """
    Inserts a list of validated papers into Cassandra in chunks.

    All papers in a single call share the same batch_id,
    so one ingestion run = one batch_id in the table.

    Returns a summary dict:
        {
            "batch_id": UUID,
            "total":    int,
            "inserted": int,
            "failed":   int,
        }
    """
    batch_id  = uuid.uuid4()
    ingestion_date = datetime.date.today()
    inserted  = 0
    failed    = 0

    with CassandraConnection() as conn:
        prepared = _prepare_insert(conn.session)

        for chunk in _chunk(papers, chunk_size):
            batch = BatchStatement(consistency_level=ConsistencyLevel.LOCAL_QUORUM)

            for paper in chunk:
                batch.add(prepared, (
                    batch_id,
                    ingestion_date,
                    paper["arxiv_id"],
                    paper["title"],
                    paper["abstract"],
                    paper["authors"],
                    paper["categories"],
                    paper["primary_category"],
                    paper["published_date"],
                    paper["updated_date"],
                    paper["pdf_url"],
                    paper["raw_json"],
                    paper["ingested_at"],
                ))

            try:
                conn.session.execute(batch)
                inserted += len(chunk)
            except Exception as e:
                # Chunk failed — count all papers in it as failed
                failed += len(chunk)

    return {
        "batch_id": batch_id,
        "ingestion_date": ingestion_date,
        "total":    len(papers),
        "inserted": inserted,
        "failed":   failed,
    }
