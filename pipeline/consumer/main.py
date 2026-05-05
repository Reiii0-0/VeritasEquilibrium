import json
import logging
import os
import signal
import time
from typing import Any, Dict, List

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values
from confluent_kafka import Consumer, KafkaError
from pydantic import ValidationError

# Import our shared schema
from api.schemas import LoanInflowEvent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("consumer")

_running = True

def handle_shutdown(signum: int, frame: Any) -> None:
    """Handles SIGTERM and SIGINT for graceful shutdown."""
    global _running
    logger.info("Shutdown signal received. Stopping consumer...")
    _running = False

def get_db_pool() -> pool.ThreadedConnectionPool:
    """Initializes and returns a PostgreSQL connection pool."""
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "postgres")
    
    return pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )

def setup_tables(db_pool: pool.ThreadedConnectionPool) -> None:
    """Creates raw schema and necessary tables if they don't exist."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.loans (
                    id SERIAL PRIMARY KEY,
                    application_id UUID NOT NULL UNIQUE,
                    timestamp TIMESTAMPTZ NOT NULL,
                    payload JSONB NOT NULL,
                    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.dead_letter (
                    id SERIAL PRIMARY KEY,
                    payload TEXT,
                    error_message TEXT,
                    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error setting up tables: {e}")
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)

def handle_dead_letter(
    db_pool: pool.ThreadedConnectionPool, 
    batch: List[Dict[str, Any]], 
    error_msg: str
) -> None:
    """Writes failed messages to the dead letter table."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            query = """
                INSERT INTO raw.dead_letter (payload, error_message)
                VALUES %s
            """
            values = [(json.dumps(msg), error_msg) for msg in batch]
            execute_values(cur, query, values)
        conn.commit()
        logger.warning(f"Routed {len(batch)} records to dead_letter due to: {error_msg[:100]}...")
    except Exception as e:
        logger.critical(f"Failed to write to dead_letter: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)

def insert_batch(db_pool: pool.ThreadedConnectionPool, batch: List[Dict[str, Any]]) -> None:
    """Inserts a batch of loan applications into PostgreSQL with idempotency."""
    if not batch:
        return
        
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            query = """
                INSERT INTO raw.loans (application_id, timestamp, payload)
                VALUES %s
                ON CONFLICT (application_id) DO NOTHING
            """
            values = []
            for record in batch:
                # Metadata is already validated and part of the record dict
                app_id = record.get("application_id")
                ts = record.get("timestamp")
                
                # Double-check extraction to avoid NULLs in the tuple
                if not app_id or not ts:
                    logger.error(f"Missing mandatory fields in record: {record.keys()}")
                    continue
                    
                values.append((app_id, ts, json.dumps(record, default=str)))
                
            if values:
                execute_values(cur, query, values)
                conn.commit()
                logger.info(f"Successfully processed batch of {len(values)} records.")
            else:
                logger.warning("Batch was empty after filtering out invalid records.")
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        conn.rollback()
        handle_dead_letter(db_pool, batch, str(e))
    finally:
        db_pool.putconn(conn)

def main() -> None:
    """Main function to run the consumer loop."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Retry connecting to DB
    db_pool = None
    while _running:
        try:
            db_pool = get_db_pool()
            setup_tables(db_pool)
            break
        except Exception as e:
            logger.warning(f"Waiting for database to be ready: {e}")
            time.sleep(2)
            
    if not db_pool:
        return
    
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "group.id": "financial-pipeline-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False
    }
    
    consumer = Consumer(conf)
    topic = os.getenv("KAFKA_TOPIC_LOAN_APPS", "raw.loan_applications")
    consumer.subscribe([topic])
    
    batch = []
    last_commit_time = time.time()
    batch_size = 100
    batch_timeout = 5.0  # seconds
    
    logger.info(f"Starting integrated consumer for topic: {topic}")
    
    try:
        while _running:
            msg = consumer.poll(1.0)
            
            if msg is None:
                pass
            elif msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
            else:
                try:
                    raw_payload = json.loads(msg.value().decode("utf-8"))
                    
                    # FLAWLESS INTEGRATION: Validate against Inflow Schema (metadata + features)
                    validated_loan = LoanInflowEvent(**raw_payload)

                    # Store the validated model as a dict (includes application_id and timestamp)
                    batch.append(validated_loan.model_dump())
                except ValidationError as ve:
                    logger.warning(f"Validation failed for record: {ve}")
                    handle_dead_letter(db_pool, [raw_payload], f"Schema Validation Error: {ve}")
                except Exception as e:
                    logger.error(f"Processing error: {e}")
                    handle_dead_letter(
                        db_pool, 
                        [{"raw_value": msg.value().decode("utf-8", errors="replace")}], 
                        str(e)
                    )
            
            current_time = time.time()
            if len(batch) >= batch_size or (batch and current_time - last_commit_time >= batch_timeout):
                insert_batch(db_pool, batch)
                consumer.commit(asynchronous=False)
                batch = []
                last_commit_time = current_time
                
    finally:
        if batch:
            insert_batch(db_pool, batch)
            try:
                consumer.commit(asynchronous=False)
            except Exception as e:
                logger.error(f"Final commit failed: {e}")
            
        consumer.close()
        db_pool.closeall()
        logger.info("Consumer shut down successfully.")

if __name__ == "__main__":
    main()
