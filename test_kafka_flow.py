#!/usr/bin/env python3
"""Test Kafka producer/consumer flow"""
import sys
import json
from datetime import datetime

print("Step 1: Testing paper fetching...", flush=True)
try:
    from ingestion.fetch_papers import PaperFetcher
    fetcher = PaperFetcher()
    papers = fetcher._fetch_domain_papers('cs.AI')
    print(f"✅ Fetched {len(papers)} papers from ArXiv", flush=True)
    if papers:
        first = papers[0]
        if isinstance(first, dict):
            paper_title = first.get('title', 'N/A')
        else:
            paper_title = first.title
        print(f"   First paper: {str(paper_title)[:50]}...", flush=True)
        print(f"   Paper type: {type(first)}", flush=True)
except Exception as e:
    print(f"❌ Failed to fetch papers: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Testing Kafka producer...", flush=True)
try:
    from kafka import KafkaProducer
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        request_timeout_ms=90000,
        value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
    )
    print("✅ Connected to Kafka", flush=True)
    
    # Send a test message
    msg = {
        "test": "message",
        "timestamp": datetime.now().isoformat(),
        "paper_count": len(papers)
    }
    future = producer.send('test-topic', value=msg)
    meta = future.get(timeout=10)
    print(f"✅ Sent test message to partition {meta.partition} offset {meta.offset}", flush=True)
    producer.close()
except Exception as e:
    print(f"❌ Failed Kafka test: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Testing Kafka consumer...", flush=True)
try:
    from kafka import KafkaConsumer
    consumer = KafkaConsumer(
        'test-topic',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        session_timeout_ms=10000,
        request_timeout_ms=60000,
        max_poll_records=10,
        consumer_timeout_ms=5000
    )
    print("✅ Connected to Kafka consumer", flush=True)
    
    messages = consumer.poll(timeout_ms=5000, max_records=10)
    print(f"✅ Received {sum(len(v) for v in messages.values())} messages", flush=True)
    for topic_partition, records in messages.items():
        for record in records:
            print(f"   Message: {record.value}", flush=True)
    consumer.close()
except Exception as e:
    print(f"❌ Failed consumer test: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed!", flush=True)
