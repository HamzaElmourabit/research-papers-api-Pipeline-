#!/usr/bin/env python3
"""
🚀 Kafka Producer - Streams ArXiv papers to Kafka topic
Fetches papers from ArXiv API and publishes them to Kafka in real-time
"""

import json
import sys
import time
import logging
from typing import Optional
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import KafkaError
import uuid

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0].rsplit("\\", 1)[0])

from ingestion.fetch_papers import PaperFetcher
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def json_safe_serializer(obj):
    """Serialize Python objects into JSON-safe values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    return str(obj)


class ArXivKafkaProducer:
    """Produces ArXiv papers to Kafka topic"""

    def __init__(
        self,
        kafka_bootstrap_servers: str = "kafka:9092",
        topic: str = "arxiv-papers-raw",
        batch_size: int = 50,
    ):
        """
        Initialize Kafka producer
        
        Args:
            kafka_bootstrap_servers: Kafka broker address
            topic: Kafka topic name
            batch_size: Number of papers to fetch per domain
        """
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.topic = topic
        self.batch_size = batch_size
        self.producer: Optional[KafkaProducer] = None
        self.fetcher = PaperFetcher(batch_size=batch_size)
        self.session_id = str(uuid.uuid4())[:8]
        self.batch_id = None

    def connect(self, max_retries: int = 5) -> bool:
        """Connect to Kafka broker with retries"""
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🔗 Connecting to Kafka (attempt {attempt + 1}/{max_retries}): {self.kafka_bootstrap_servers}"
                )
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(
                        v,
                        default=json_safe_serializer,
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    acks="all",
                    retries=5,
                    max_in_flight_requests_per_connection=5,
                    request_timeout_ms=90000,
                    connections_max_idle_ms=120000,
                    metadata_max_age_ms=30000,
                )
                logger.info("✅ Connected to Kafka successfully")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error("❌ Failed to connect to Kafka after retries")
        return False

    def produce_papers(
        self, domains: Optional[list[str]] = None, max_papers: int = 50
    ) -> dict:
        """
        Fetch papers from ArXiv and produce to Kafka
        
        Args:
            domains: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
            max_papers: Maximum papers per domain
            
        Returns:
            Statistics dictionary
        """
        if not self.producer:
            logger.error("❌ Producer not connected. Call connect() first.")
            return {"status": "error", "message": "Producer not connected"}

        if domains is None:
            domains = ["cs.AI", "cs.LG", "cs.CV", "stat.ML", "math.CO"]

        self.batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{self.session_id}"
        stats = {
            "batch_id": self.batch_id,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_papers": 0,
            "domains_processed": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "errors": [],
        }

        logger.info(f"🚀 Starting ArXiv → Kafka producer for {len(domains)} domains")

        for domain in domains:
            try:
                logger.info(f"📦 Fetching papers from {domain}...")
                papers = self.fetcher._fetch_domain_papers(domain)

                for idx, paper in enumerate(papers):
                    if idx >= max_papers:
                        break

                    paper_payload = paper
                    if not isinstance(paper_payload, dict):
                        if hasattr(paper_payload, "model_dump"):
                            paper_payload = paper_payload.model_dump()
                        else:
                            paper_payload = dict(paper_payload)

                    message = {
                        "batch_id": self.batch_id,
                        "session_id": self.session_id,
                        "domain": domain,
                        "timestamp": datetime.now().isoformat(),
                        "paper": paper_payload,
                    }

                    try:
                        future = self.producer.send(self.topic, value=message)
                        record_metadata = future.get(timeout=10)

                        stats["messages_sent"] += 1
                        stats["total_papers"] += 1

                        logger.debug(
                            f"  ✓ Paper {idx + 1} sent to {self.topic} "
                            f"[partition={record_metadata.partition}, "
                            f"offset={record_metadata.offset}]"
                        )

                    except Exception as e:
                        stats["messages_failed"] += 1
                        stats["errors"].append(f"Paper {idx}: {str(e)}")
                        logger.error(f"  ✗ Failed to produce paper {idx}: {e}")

                stats["domains_processed"] += 1
                logger.info(
                    f"✅ Completed {domain}: {min(len(papers), max_papers)} papers sent"
                )

            except Exception as e:
                logger.error(f"❌ Error processing domain {domain}: {e}")
                stats["errors"].append(f"Domain {domain}: {str(e)}")

        # Flush all messages
        logger.info("🔄 Flushing remaining messages...")
        self.producer.flush(timeout=30)

        stats["status"] = "success" if stats["messages_failed"] == 0 else "partial"
        logger.info(
            f"\n{'='*60}\n"
            f"📊 Production Summary:\n"
            f"  • Batch ID: {stats['batch_id']}\n"
            f"  • Total Papers: {stats['total_papers']}\n"
            f"  • Messages Sent: {stats['messages_sent']}\n"
            f"  • Messages Failed: {stats['messages_failed']}\n"
            f"  • Status: {stats['status']}\n"
            f"{'='*60}"
        )

        return stats

    def close(self):
        """Close Kafka producer"""
        if self.producer:
            logger.info("🛑 Closing Kafka producer...")
            self.producer.close(timeout=10)
            self.producer = None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ArXiv → Kafka Producer")
    parser.add_argument(
        "--kafka-server",
        default="localhost:9092",
        help="Kafka bootstrap server (default: localhost:9092)",
    )
    parser.add_argument(
        "--topic",
        default="arxiv-papers-raw",
        help="Kafka topic name (default: arxiv-papers-raw)",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["cs.AI", "cs.LG"],
        help="ArXiv domains to fetch (default: cs.AI cs.LG)",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=50,
        help="Maximum papers per domain (default: 50)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously with interval",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval between runs in seconds (default: 3600)",
    )

    args = parser.parse_args()

    producer = ArXivKafkaProducer(
        kafka_bootstrap_servers=args.kafka_server,
        topic=args.topic,
    )

    try:
        if not producer.connect():
            logger.error("Failed to connect to Kafka")
            sys.exit(1)

        if args.continuous:
            logger.info(f"🔄 Running in continuous mode with {args.interval}s interval")
            iteration = 0
            while True:
                iteration += 1
                logger.info(f"\n{'='*60}\n📍 Iteration {iteration}")
                producer.produce_papers(domains=args.domains, max_papers=args.max_papers)
                logger.info(f"⏳ Waiting {args.interval}s before next run...")
                time.sleep(args.interval)
        else:
            producer.produce_papers(domains=args.domains, max_papers=args.max_papers)

    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        producer.close()


if __name__ == "__main__":
    main()
