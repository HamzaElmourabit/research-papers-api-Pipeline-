#!/usr/bin/env python3
"""
🚀 Orchestrate Kafka Streaming Pipeline
Manages ArXiv → Kafka → Cassandra streaming workflow
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit("\\", 1)[0].rsplit("\\", 1)[0])

from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KafkaStreamingOrchestrator:
    """Orchestrates the complete Kafka streaming pipeline"""

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = Path(workspace_dir)
        self.processes: Dict[str, subprocess.Popen] = {}
        self.kafka_server = "localhost:9092"
        self.kafka_topic = "arxiv-papers-raw"

    def start_docker_services(self) -> bool:
        """Start Docker services (Kafka, Zookeeper, Cassandra)"""
        logger.info("🐳 Starting Docker services...")
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d", "zookeeper", "kafka", "cassandra"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"❌ Docker compose failed: {result.stderr}")
                return False

            logger.info("✅ Docker services started")
            logger.info("⏳ Waiting for services to be ready...")
            time.sleep(10)  # Wait for services to be ready

            return True
        except Exception as e:
            logger.error(f"❌ Error starting Docker services: {e}")
            return False

    def check_kafka_ready(self, max_retries: int = 10) -> bool:
        """Check if Kafka is ready to accept connections"""
        logger.info("🔍 Checking Kafka broker status...")
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "kafka_arxiv",
                        "kafka-broker-api-versions.sh",
                        "--bootstrap-server",
                        "localhost:9092",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.info("✅ Kafka is ready")
                    return True
            except Exception as e:
                logger.debug(f"  Kafka check attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        logger.error("❌ Kafka failed to become ready")
        return False

    def create_kafka_topic(self) -> bool:
        """Create Kafka topic for papers"""
        logger.info(f"📋 Creating Kafka topic: {self.kafka_topic}...")
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "kafka_arxiv",
                    "kafka-topics.sh",
                    "--create",
                    "--topic",
                    self.kafka_topic,
                    "--bootstrap-server",
                    "localhost:9092",
                    "--partitions",
                    "3",
                    "--replication-factor",
                    "1",
                    "--if-not-exists",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                logger.error(f"❌ Topic creation failed: {result.stderr}")
                return False

            logger.info(f"✅ Topic created: {self.kafka_topic}")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating topic: {e}")
            return False

    def start_producer(self, domains: List[str] = None, continuous: bool = False) -> bool:
        """Start Kafka producer in background"""
        if domains is None:
            domains = ["cs.AI", "cs.LG"]

        logger.info("🚀 Starting Kafka Producer...")
        try:
            cmd = [
                sys.executable,
                str(self.workspace_dir / "scripts" / "kafka_producer.py"),
                "--kafka-server",
                self.kafka_server,
                "--topic",
                self.kafka_topic,
                "--domains",
                *domains,
                "--max-papers",
                "50",
            ]

            if continuous:
                cmd.extend(["--continuous", "--interval", "3600"])

            process = subprocess.Popen(
                cmd,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes["producer"] = process
            logger.info("✅ Producer started")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"❌ Error starting producer: {e}")
            return False

    def start_consumer(self, continuous: bool = True) -> bool:
        """Start Kafka consumer in background"""
        logger.info("📥 Starting Kafka Consumer...")
        try:
            cmd = [
                sys.executable,
                str(self.workspace_dir / "scripts" / "kafka_consumer.py"),
                "--kafka-server",
                self.kafka_server,
                "--topic",
                self.kafka_topic,
            ]

            if continuous:
                cmd.append("--continuous")

            process = subprocess.Popen(
                cmd,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes["consumer"] = process
            logger.info("✅ Consumer started")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"❌ Error starting consumer: {e}")
            return False

    def start_api_server(self) -> bool:
        """Start FastAPI server in background"""
        logger.info("🌐 Starting API Server...")
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.workspace_dir / "scripts" / "api_server.py")],
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.processes["api"] = process
            logger.info("✅ API Server started (http://localhost:8000)")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"❌ Error starting API server: {e}")
            return False

    def list_topics(self) -> List[str]:
        """List Kafka topics"""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "kafka_arxiv",
                    "kafka-topics.sh",
                    "--list",
                    "--bootstrap-server",
                    "localhost:9092",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                topics = result.stdout.strip().split("\n")
                return [t for t in topics if t]
            return []
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []

    def monitor_pipeline(self):
        """Monitor the running pipeline"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 PIPELINE MONITORING")
        logger.info("=" * 60)

        logger.info("\n🐳 Docker Containers:")
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
            )
            logger.info(result.stdout)
        except Exception as e:
            logger.error(f"Error listing containers: {e}")

        logger.info("\n📨 Kafka Topics:")
        topics = self.list_topics()
        for topic in topics:
            logger.info(f"  • {topic}")

        logger.info("\n⚙️ Running Processes:")
        for name, process in self.processes.items():
            status = "✅ Running" if process.poll() is None else "❌ Stopped"
            logger.info(f"  • {name}: {status}")

        logger.info("\n🌐 Access Points:")
        logger.info("  • API (Swagger): http://localhost:8000/docs")
        logger.info("  • Cassandra: localhost:9042")
        logger.info("  • Kafka: localhost:9092")
        logger.info("=" * 60 + "\n")

    def stop_all(self):
        """Stop all processes"""
        logger.info("🛑 Stopping all processes...")

        # Stop Python processes
        for name, process in self.processes.items():
            try:
                logger.info(f"  Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"  Error stopping {name}: {e}")
                try:
                    process.kill()
                except:
                    pass

        # Stop Docker services
        logger.info("  Stopping Docker services...")
        try:
            subprocess.run(
                ["docker-compose", "down"],
                cwd=self.workspace_dir,
                capture_output=True,
            )
        except Exception as e:
            logger.warning(f"  Error stopping Docker: {e}")

        logger.info("✅ All processes stopped")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Orchestrate Kafka Streaming Pipeline"
    )
    parser.add_argument(
        "--action",
        choices=["start", "stop", "restart", "monitor"],
        default="start",
        help="Action to perform (default: start)",
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["cs.AI", "cs.LG"],
        help="ArXiv domains to fetch",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run producer in continuous mode",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory",
    )

    args = parser.parse_args()

    orchestrator = KafkaStreamingOrchestrator(workspace_dir=args.workspace)

    try:
        if args.action == "start":
            logger.info("\n" + "=" * 60)
            logger.info("🚀 KAFKA STREAMING PIPELINE - STARTUP")
            logger.info("=" * 60 + "\n")

            # Start services
            if not orchestrator.start_docker_services():
                logger.error("Failed to start Docker services")
                sys.exit(1)

            if not orchestrator.check_kafka_ready():
                logger.error("Kafka failed to become ready")
                sys.exit(1)

            if not orchestrator.create_kafka_topic():
                logger.error("Failed to create Kafka topic")
                sys.exit(1)

            if not orchestrator.start_producer(
                domains=args.domains, continuous=args.continuous
            ):
                logger.error("Failed to start producer")
                sys.exit(1)

            if not orchestrator.start_consumer(continuous=True):
                logger.error("Failed to start consumer")
                sys.exit(1)

            if not orchestrator.start_api_server():
                logger.error("Failed to start API server")
                sys.exit(1)

            # Monitor
            orchestrator.monitor_pipeline()

            # Keep running
            logger.info("✅ Pipeline is running! Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(10)
            except KeyboardInterrupt:
                logger.info("\n⏹️ Stopping pipeline...")
                orchestrator.stop_all()

        elif args.action == "stop":
            orchestrator.stop_all()

        elif args.action == "restart":
            orchestrator.stop_all()
            time.sleep(5)
            logger.info("Restarting...")
            os.execvp(sys.executable, [sys.executable] + sys.argv[:-1] + ["--action", "start"])

        elif args.action == "monitor":
            orchestrator.monitor_pipeline()

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
