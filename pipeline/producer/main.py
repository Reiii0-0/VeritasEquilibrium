import csv
import json
import logging
import os
import random
import signal
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator

from confluent_kafka import Producer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("producer")

_running = True


def handle_shutdown(signum: int, frame: Any) -> None:
    """Handles SIGTERM and SIGINT for graceful shutdown."""
    global _running
    logger.info("Shutdown signal received. Stopping producer...")
    _running = False


def get_kafka_producer() -> Producer:
    """Initializes and returns a Kafka Producer instance."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "client.id": "financial-pipeline-producer"
    }
    return Producer(conf)


def generate_synthetic_loan() -> Dict[str, Any]:
    """Generates a full-fidelity loan application compliant with API schemas."""
    purposes = [
        "debt_consolidation", "credit_card", "home_improvement", 
        "major_purchase", "small_business", "car", "moving"
    ]
    grades = ["A", "B", "C", "D", "E"]
    home_ownerships = ["MORTGAGE", "RENT", "OWN", "ANY"]
    
    # Generate coherent FICO
    fico_low = random.uniform(660, 800)
    fico_high = fico_low + 4
    
    # Generate coherent Loan vs Funded
    loan_amnt = round(random.uniform(1000, 40000), 2)
    
    return {
        "application_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "loan_amnt": loan_amnt,
        "funded_amnt": loan_amnt,
        "term": random.choice([36, 60]),
        "int_rate": round(random.uniform(5.0, 25.0), 2),
        "installment": round(loan_amnt / 36, 2), # Simplified
        "grade": random.choice(grades),
        "sub_grade": random.choice(["1", "2", "3", "4", "5"]),
        "emp_length": random.randint(0, 10),
        "home_ownership": random.choice(home_ownerships),
        "annual_inc": round(random.uniform(30000, 150000), 2),
        "verification_status": random.choice(["Verified", "Source Verified", "Not Verified"]),
        "purpose": random.choice(purposes),
        "dti": round(random.uniform(0.0, 35.0), 2),
        "delinq_2yrs": float(random.randint(0, 2)),
        "fico_range_low": round(fico_low, 1),
        "fico_range_high": round(fico_high, 1),
        "open_acc": float(random.randint(5, 20)),
        "pub_rec": float(random.randint(0, 1)),
        "revol_bal": round(random.uniform(1000, 50000), 2),
        "revol_util": round(random.uniform(0.0, 100.0), 1),
        "total_acc": float(random.randint(10, 50)),
        "initial_list_status": random.choice(["w", "f"]),
        "application_type": "Individual"
    }


def delivery_report(err: Any, msg: Any) -> None:
    """Callback for message delivery status."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")


def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Cleans a raw CSV row to match the Pydantic schema types."""
    try:
        # Map fields to match LoanApplication schema
        clean = {
            "application_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loan_amnt": float(row.get("loan_amnt", 0)),
            "funded_amnt": float(row.get("funded_amnt", 0)),
            "term": int(str(row.get("term", "36")).replace(" months", "").strip()),
            "int_rate": float(str(row.get("int_rate", "0")).replace("%", "").strip()),
            "installment": float(row.get("installment", 0)),
            "grade": row.get("grade", "U"),
            "sub_grade": row.get("sub_grade", "U0"),
            "emp_length": int(''.join(filter(str.isdigit, str(row.get("emp_length", "0")))) or 0),
            "home_ownership": row.get("home_ownership", "OTHER"),
            "annual_inc": float(row.get("annual_inc", 0)),
            "verification_status": row.get("verification_status", "Not Verified"),
            "purpose": row.get("purpose", "other"),
            "dti": float(row.get("dti", 0)),
            "delinq_2yrs": float(row.get("delinq_2yrs", 0)),
            "fico_range_low": float(row.get("fico_range_low", 0)),
            "fico_range_high": float(row.get("fico_range_high", 0)),
            "open_acc": float(row.get("open_acc", 0)),
            "pub_rec": float(row.get("pub_rec", 0)),
            "revol_bal": float(row.get("revol_bal", 0)),
            "revol_util": float(str(row.get("revol_util", "0")).replace("%", "").strip()),
            "total_acc": float(row.get("total_acc", 0)),
            "initial_list_status": row.get("initial_list_status", "f"),
            "application_type": row.get("application_type", "Individual")
        }
        return clean
    except Exception as e:
        logger.warning(f"Failed to clean row: {e}")
        return None


def data_generator(csv_path: str) -> Generator[Dict[str, Any], None, None]:
    """Generates data from CSV or falls back to synthetic data."""
    if os.path.exists(csv_path):
        logger.info(f"Reading data from {csv_path}")
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = clean_row(row)
                if cleaned:
                    yield cleaned
    else:
        logger.warning(f"CSV file not found at {csv_path}. Generating synthetic data.")
        while True:
            yield generate_synthetic_loan()


def main() -> None:
    """Main function to run the producer loop."""
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    producer = get_kafka_producer()
    topic = os.getenv("KAFKA_TOPIC_LOAN_APPS", "raw.loan_applications")
    csv_path = os.getenv("CSV_FILE_PATH", "/app/data/accepted_2007_to_2018Q4.csv")

    logger.info(f"Starting producer loop for topic: {topic}")
    
    try:
        for record in data_generator(csv_path):
            if not _running:
                break
                
            try:
                payload = json.dumps(record)
                producer.produce(
                    topic, 
                    key=record["application_id"], 
                    value=payload, 
                    callback=delivery_report
                )
                producer.poll(0)
                
                # Control the rate (approx 1 record per second)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error producing message: {e}")
                time.sleep(1)
    finally:
        logger.info("Flushing producer...")
        producer.flush(timeout=5)
        logger.info("Producer shut down successfully.")


if __name__ == "__main__":
    main()
