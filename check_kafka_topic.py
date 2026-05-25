#!/usr/bin/env python3
"""Check Kafka topic for messages"""
import json
from kafka import KafkaConsumer

print("Connecting to Kafka consumer...", flush=True)
consumer = KafkaConsumer(
    'arxiv-papers-raw',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    session_timeout_ms=10000,
    request_timeout_ms=60000,
    consumer_timeout_ms=3000
)
print("Connected. Polling for messages...", flush=True)
messages = consumer.poll(timeout_ms=5000, max_records=50)
msg_count = sum(len(v) for v in messages.values())
print(f"✅ Received {msg_count} messages from arxiv-papers-raw topic", flush=True)

for topic_partition, records in messages.items():
    for i, record in enumerate(records[:3]):
        msg = record.value
        paper_id = msg.get("paper", {}).get("arxiv_id", "N/A")
        print(f"  [{i+1}] batch={msg.get('batch_id')}, domain={msg.get('domain')}, paper={paper_id[:20]}...", flush=True)

consumer.close()
print("Done!", flush=True)
