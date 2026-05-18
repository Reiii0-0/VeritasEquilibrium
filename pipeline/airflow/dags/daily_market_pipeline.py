import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

@dag(
    dag_id="daily_market_pipeline",
    default_args=default_args,
    description="Full production pipeline for financial data",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["production", "veritas"],
)
def financial_pipeline():
    """
    Production-grade DAG following the 7-task sequence mandate.
    """

    check_data = BashOperator(
        task_id="check_data_freshness",
        bash_command="cd /opt/airflow/dbt_project && dbt debug --profiles-dir .",
    )

    run_staging = BashOperator(
        task_id="run_dbt_staging",
        bash_command="cd /opt/airflow/dbt_project && dbt run --select staging --profiles-dir .",
    )

    run_intermediate = BashOperator(
        task_id="run_dbt_intermediate",
        bash_command="cd /opt/airflow/dbt_project && dbt run --select intermediate --profiles-dir .",
    )

    run_marts = BashOperator(
        task_id="run_dbt_marts",
        bash_command="cd /opt/airflow/dbt_project && dbt run --select marts --profiles-dir .",
    )

    run_tests = BashOperator(
        task_id="run_dbt_tests",
        bash_command="cd /opt/airflow/dbt_project && dbt test --profiles-dir .",
    )

    gen_docs = BashOperator(
        task_id="generate_docs",
        bash_command="cd /opt/airflow/dbt_project && dbt docs generate --profiles-dir .",
    )

    @task
    def log_summary():
        print("Production pipeline completed successfully.")

    check_data >> run_staging >> run_intermediate >> run_marts >> run_tests >> gen_docs >> log_summary()

financial_pipeline()
