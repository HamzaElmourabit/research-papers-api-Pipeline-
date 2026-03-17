CREATE KEYSPACE IF NOT EXISTS arxiv
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE arxiv;

CREATE TABLE IF NOT EXISTS papers_raw (
    batch_id uuid,
    ingestion_date date,
    arxiv_id text,
    title text,
    abstract text,
    authors list<text>,
    categories list<text>,
    primary_category text,
    published_date timestamp,
    updated_date timestamp,
    pdf_url text,
    raw_json text,
    ingested_at timestamp,
    
    PRIMARY KEY (batch_id, arxiv_id)
);
