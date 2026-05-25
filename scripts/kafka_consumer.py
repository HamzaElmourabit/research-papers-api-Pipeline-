#!/usr/bin/env python3
"""
📥 Kafka Consumer - Consumes ArXiv papers from Kafka and stores in Cassandra
Real-time streaming of papers from Kafka topic to NoSQL database
"""

import json
import sys
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import uuid

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0].rsplit("\\", 1)[0])

from casandra.insert_papers import insert_papers
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KafkaArXivConsumer:
    """Consumes papers from Kafka and stores in Cassandra"""

    def __init__(
        self,
        kafka_bootstrap_servers: str = "kafka:9092",
        topic: str = "arxiv-papers-raw",
        group_id: str = "arxiv-consumer-group",
        cassandra_host: str = "cassandra",
        cassandra_port: int = 9042,
    ):
        """
        Initialize Kafka consumer
        
        Args:
            kafka_bootstrap_servers: Kafka broker address
            topic: Kafka topic name
            group_id: Consumer group ID
            cassandra_host: Cassandra host (for info only)
            cassandra_port: Cassandra port (for info only)
        """
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer: Optional[KafkaConsumer] = None
        self.cassandra_host = cassandra_host
        self.cassandra_port = cassandra_port
        self.session_id = str(uuid.uuid4())[:8]
        self.stats = {
            "messages_received": 0,
            "papers_inserted": 0,
            "papers_skipped": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    def connect(self, max_retries: int = 5) -> bool:
        """Connect to Kafka broker with retries"""
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🔗 Connecting to Kafka consumer (attempt {attempt + 1}/{max_retries}): {self.kafka_bootstrap_servers}"
                )
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    max_poll_records=100,
                    # Keep session timeout relatively low so group rebalances
                    session_timeout_ms=10000,
                    # request_timeout_ms must be larger than session_timeout_ms
                    request_timeout_ms=60000,
                )
                logger.info("✅ Connected to Kafka consumer successfully")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error("❌ Failed to connect to Kafka after retries")
        return False

    def consume_papers(
        self, max_messages: Optional[int] = None, timeout_ms: int = 1000
    ) -> Dict[str, Any]:
        """
        Consume papers from Kafka and insert into Cassandra
        
        Args:
            max_messages: Maximum messages to consume (None = infinite)
            timeout_ms: Kafka poll timeout in milliseconds
            
        Returns:
            Statistics dictionary
        """
        if not self.consumer:
            logger.error("❌ Consumer not connected. Call connect() first.")
            return {"status": "error", "message": "Consumer not connected"}

        self.stats["start_time"] = datetime.now().isoformat()
        logger.info(
            f"📥 Starting Kafka consumer for topic '{self.topic}' "
            f"[group: {self.group_id}]"
        )

        try:
            message_count = 0
            batch_ids = set()

            while True:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=timeout_ms, max_records=100)

                if not messages:
                    if max_messages and message_count >= max_messages:
                        break
                    # No messages, wait a bit
                    time.sleep(1)
                    continue

                for topic_partition, records in messages.items():
                    for record in records:
                        if max_messages and message_count >= max_messages:
                            break

                        try:
                            message = record.value
                            batch_ids.add(message.get("batch_id"))

                            logger.debug(
                                f"📨 Message received [offset={record.offset}, "
                                f"partition={record.partition}]"
                            )

                            # Extract paper data
                            paper_data = message.get("paper")
                            if not paper_data:
                                logger.warning(
                                    f"⚠️ Empty paper data in message at offset {record.offset}"
                                )
                                self.stats["papers_skipped"] += 1
                                continue

                            # Insert paper into Cassandra
                            try:
                                result = insert_papers([paper_data])
                                if result.get("inserted", 0) > 0:
                                    self.stats["papers_inserted"] += 1
                                    logger.debug(
                                        f"  ✓ Paper inserted: {paper_data.get('arxiv_id')}"
                                    )
                                else:
                                    logger.warning(f"  ✗ Paper insert returned 0: {paper_data.get('arxiv_id')}")
                                    self.stats["papers_skipped"] += 1
                            except Exception as e:
                                logger.warning(f"  ✗ Failed to insert paper: {e}")
                                self.stats["papers_skipped"] += 1
                                self.stats["errors"].append(str(e)[:100])

                            self.stats["messages_received"] += 1
                            message_count += 1

                            if message_count % 10 == 0:
                                logger.info(
                                    f"📊 Progress: {message_count} messages, "
                                    f"{self.stats['papers_inserted']} papers inserted"
                                )

                        except Exception as e:
                            logger.error(f"❌ Error processing record: {e}")
                            self.stats["errors"].append(f"Record error: {str(e)[:100]}")

        except KeyboardInterrupt:
            logger.info("⏹️ Consumer interrupted")
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}", exc_info=True)
            self.stats["errors"].append(f"Consumer error: {str(e)[:100]}")

        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["status"] = "success"

        logger.info(
            f"\n{'='*60}\n"
            f"📊 Consumption Summary:\n"
            f"  • Messages Received: {self.stats['messages_received']}\n"
            f"  • Papers Inserted: {self.stats['papers_inserted']}\n"
            f"  • Papers Skipped: {self.stats['papers_skipped']}\n"
            f"  • Batches: {len(batch_ids)}\n"
            f"  • Errors: {len(self.stats['errors'])}\n"
            f"  • Duration: {self.stats['start_time']} to {self.stats['end_time']}\n"
            f"{'='*60}"
        )

        return self.stats

    def close(self):
        """Close Kafka consumer"""
        if self.consumer:
            logger.info("🛑 Closing Kafka consumer...")
            self.consumer.close()
            self.consumer = None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Kafka → Cassandra Consumer")
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
        "--group-id",
        default="arxiv-consumer-group",
        help="Consumer group ID (default: arxiv-consumer-group)",
    )
    parser.add_argument(
        "--cassandra-host",
        default="cassandra",
        help="Cassandra host (default: cassandra)",
    )
    parser.add_argument(
        "--cassandra-port",
        type=int,
        default=9042,
        help="Cassandra port (default: 9042)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Maximum messages to consume (default: infinite)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1000,
        help="Poll timeout in milliseconds (default: 1000)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously",
    )

    args = parser.parse_args()

    consumer = KafkaArXivConsumer(
        kafka_bootstrap_servers=args.kafka_server,
        topic=args.topic,
        group_id=args.group_id,
        cassandra_host=args.cassandra_host,
        cassandra_port=args.cassandra_port,
    )

    try:
        if not consumer.connect():
            logger.error("Failed to connect to Kafka")
            sys.exit(1)

        if args.continuous:
            logger.info("🔄 Running in continuous mode")
            while True:
                consumer.consume_papers(
                    max_messages=None, timeout_ms=args.timeout
                )
        else:
            consumer.consume_papers(
                max_messages=args.max_messages, timeout_ms=args.timeout
            )

    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
