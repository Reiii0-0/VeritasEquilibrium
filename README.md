# 🏦 VeritasEquilibrium: Financial Data Engineering & Credit Risk Ops

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Production_Ready-blue.svg)](https://www.docker.com/)

Welcome to **VeritasEquilibrium**, a high-fidelity monorepo demonstrating enterprise-grade capabilities in **Data Engineering (FinOps)** and **Machine Learning Operations (MLOps)**. This project simulates a modern financial institution's data backbone, from raw market ingestion to risk-weighted lending decisions.

---

## 🏗️ Core Architecture

### 1. [Real-Time Data Pipeline](./pipeline/) (Data Engineering)
A high-throughput streaming platform built for sub-second ingestion and multi-layered analytical transformations.
- **Ingestion:** Python-based multi-threaded Producers → Kafka (KRaft).
- **Warehouse:** Kafka Consumer → PostgreSQL (Raw Schema).
- **Transformation:** **dbt 3-Layer Architecture** (Staging → Intermediate → Marts).
- **Orchestration:** Airflow (7-task production sequence).
- **Visualization:** High-resolution Grafana dashboards (Minute-level granularity).

### 2. [Credit Risk Scorecard API](./credit-risk/) (Machine Learning)
A Basel-III compliant credit risk engine providing transparent, explainable scoring.
- **Model:** Tuned XGBoost using Weight of Evidence (WoE) and Information Value (IV) encoding.
- **Explainability:** Integrated SHAP (TreeExplainer) for local and global feature importance.
- **Deployment:** FastAPI microservice with Pydantic validation and JSON logging.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose (v2.20+)
- Python 3.11+
- At least 8GB RAM for the Docker stack.

### Quick Deployment (Pipeline)
1. **Configure Secrets:**
   ```bash
   cd pipeline
   cp .env.example .env
   # Update variables in .env as needed
   ```
2. **Start Services:**
   ```bash
   docker compose up -d --build
   ```
3. **Initialize Orchestration:**
   Access Airflow at `http://localhost:8082` (admin/admin), then enable and trigger the `daily_market_pipeline` DAG.

### Quick Deployment (Credit Risk API)
1. **Setup Environment:**
   ```bash
   cd credit-risk
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Launch API:**
   ```bash
   python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *Documentation available at `http://localhost:8000/docs`.*

---

## ⚖️ License
This project is licensed under the **MIT License** - see the [LICENSE](./LICENSE) file for details.

---
*Developed with rigorous alignment to GEMINI Engineering Mandates.*
