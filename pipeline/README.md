# 📊 Real-Time Financial Data Pipeline

A production-grade ELT pipeline designed for sub-second data ingestion and advanced analytics engineering.

## 🛠️ Technical Stack
- **Streaming:** confluent-kafka (Producer/Consumer)
- **Database:** PostgreSQL 15 (Raw, Staging, Intermediate, Marts schemas)
- **Analytics:** dbt Core (3-Layer transformation architecture)
- **Orchestration:** Apache Airflow 2.8 (7-task production sequence)
- **Monitoring:** Grafana 10 (Minute-level data resolution)

## 📐 Data Governance & Architecture

### The dbt 3-Layer Flow:
1.  **Staging (`staging`):** Standardizes raw Kafka JSON payloads into clean, typed views.
2.  **Intermediate (`intermediate`):** Encapsulates business logic, risk tiering calculations, and complex joins.
3.  **Marts (`marts`):** Final materialized tables optimized for high-performance dashboarding.

### Airflow Orchestration (7-Task Sequence):
`Check Freshness` → `Run Staging` → `Run Intermediate` → `Run Marts` → `Run Tests` → `Generate Docs` → `Log Summary`.

---

## 🚀 Execution Guide

1.  **Initialize Environment:**
    ```bash
    cp .env.example .env
    ```
    *Note: Generate a Fernet Key for Airflow using the command provided in `.env.example`.*

2.  **Start Infrastructure:**
    ```bash
    docker compose up -d --build
    ```

3.  **Run Transformations:**
    - Login to Airflow (`http://localhost:8082`, User: `admin`, Pass: `admin`).
    - Enable and Trigger the `daily_market_pipeline` DAG.

4.  **Visualize Data:**
    - Access Grafana (`http://localhost:3000`, User: `admin`, Pass: `admin_password`).
    - The **"VERITAS_MASTERPIECE_V13_FAANG_PRO"** dashboard is auto-provisioned.
    - *If visualizing for the first time, ensure your time range is set to "Last 24 Hours".*

---

## 📈 Analytical Capabilities
- **System Latency Monitoring:** Real-time tracking of ingestion delay.
- **Portfolio Risk Breakdown:** High/Medium/Low tier distribution.
- **Cumulative Volume Tracking:** Total capital flow monitoring in USD.
