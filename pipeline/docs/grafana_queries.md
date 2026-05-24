# 📊 FAANG-Level Grafana Visualization Guide

This document provides the exact production-grade SQL queries and a step-by-step guide to building your **Veritas Equilibrium** dashboard from scratch. 

---

## 🏗️ 1. Setup Datasource (First Step)
Before creating panels, ensure your connection is healthy:
1. Go to **Connections** -> **Data sources**.
2. Add **PostgreSQL**.
3. Use these settings:
   - **Host**: `postgres:5432`
   - **Database**: `veritas_db`
   - **User**: `veritas_admin`
   - **Password**: `veritas_secure_password`
   - **TLS/SSL Mode**: `disable`
4. Click **Save & test**. You should see "Database Connection OK".

---

## 📈 2. The Queries (Production Ready)

### Panel 1: Total Applications (Live Count)
- **Type**: `Stat`
- **Goal**: Shows the total volume of loans ingested in the latest hour.
- **SQL**:
```sql
SELECT 
  calculation_date as time, 
  total_applications as value 
FROM marts.mrt_approval_stats 
ORDER BY 1 DESC 
LIMIT 1
```
- **FAANG Setting**: Set **Unit** to `none`, **Thresholds** to `green` (base). Enable **Sparkline** in Options.

---

### Panel 2: Live Approval Rate (%)
- **Type**: `Stat`
- **Goal**: Tracks the quality of the incoming loan funnel.
- **SQL**:
```sql
SELECT 
  calculation_date as time, 
  approval_rate as value 
FROM marts.mrt_approval_stats 
ORDER BY 1 DESC 
LIMIT 1
```
- **FAANG Setting**: 
  - **Unit**: `percent (0-100)`.
  - **Thresholds**: `0 (Red)`, `45 (Yellow)`, `55 (Green)`.
  - **Color mode**: `Value`.

---

### Panel 3: Ingestion Trends (Time Series)
- **Type**: `Time series`
- **Goal**: Professional visualization of volume over time.
- **SQL**:
```sql
SELECT 
  calculation_date as time, 
  total_applications, 
  approved_applications 
FROM marts.mrt_approval_stats 
WHERE $__timeFilter(calculation_date)
ORDER BY 1
```
- **FAANG Setting**:
  - **Graph Styles**: Set **Line interpolation** to `Smooth`.
  - **Fill opacity**: `15`.
  - **Gradient mode**: `Opacity`.
  - **Tooltip mode**: `All series`.

---

### Panel 4: Avg Interest Rate Trend
- **Type**: `Time series`
- **Goal**: Monitoring market risk and pricing.
- **SQL**:
```sql
SELECT 
  calculation_date as time, 
  avg_interest_rate as value
FROM marts.mrt_approval_stats 
WHERE $__timeFilter(calculation_date)
ORDER BY 1
```
- **FAANG Setting**: Set **Unit** to `percent (0-100)`. Use a distinct color like `Orange` or `Purple`.

---

### Panel 5: Total Portfolio Volume (USD)
- **Type**: `Bar gauge`
- **Goal**: High-impact business value visualization.
- **SQL**:
```sql
SELECT 
  calculation_date as time, 
  total_loan_volume as value 
FROM marts.mrt_approval_stats 
ORDER BY 1 DESC 
LIMIT 10
```
- **FAANG Setting**: 
  - **Unit**: `currency (USD)`.
  - **Orientation**: `Horizontal`.
  - **Display mode**: `Retro LCD` or `Gradient`.

---

## 🛠️ 3. "The FAANG Secret" (Pro Tips)

1. **Format as**: Always set this to **"Time series"** in the Query editor, NOT "Table".
2. **Time Range**: Set your dashboard to **"Last 24 hours"** or **"Last 12 hours"**.
3. **Auto-Refresh**: Set the top-right refresh interval to **5s** for the "Real-Time" effect.
4. **Inspect First**: If a panel shows "No Data", click the panel title -> **Inspect** -> **Data**. If you see numbers there but the graph is empty, it means your **Unit** or **Time Range** setting is wrong.

---

*Note: These queries target the `marts` schema created by Airflow. Ensure your `daily_market_pipeline` DAG has finished successfully (All Green) before building.*

### Panel 6: Portfolio Risk Composition (%)
- **Type**: `Bar gauge`
- **Goal**: Advanced breakdown of loan risk tiers.
- **SQL**:
```sql
SELECT risk_category as metric, share_percentage as value FROM marts.mrt_risk_distribution
```
- **FAANG Setting**: Set **Display mode** to `Gradient`, **Orientation** to `Horizontal`.

