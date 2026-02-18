"""NYC Taxi Pipeline DAG - Production Orchestration.

Manual trigger (schedule=None):
  1. Check Flink cluster health
  2. Run dbt build (Silver -> Gold, includes tests)
  3. Alert if Flink is down
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from datetime import datetime, timedelta
import requests


default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'nyc_taxi_pipeline',
    default_args=default_args,
    description='NYC Taxi Real-Time Pipeline Orchestration',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['production', 'nyc-taxi', 'real-time'],
) as dag:

    def check_flink_health(**context):
        """Check if Flink cluster is healthy and jobs are running."""
        try:
            response = requests.get('http://flink-jobmanager:8081/jobs/overview')
            response.raise_for_status()
            jobs = response.json()['jobs']
            running_jobs = [j for j in jobs if j['state'] == 'RUNNING']
            if not running_jobs:
                raise ValueError("No running Flink jobs found")
            print(f"Flink healthy: {len(running_jobs)} jobs running")
            return 'run_dbt'
        except Exception as e:
            print(f"Flink health check failed: {e}")
            return 'alert_flink_down'

    health_check = BranchPythonOperator(
        task_id='check_flink_health',
        python_callable=check_flink_health,
    )

    # dbt build runs models + tests (no separate dbt test needed)
    run_dbt = BashOperator(
        task_id='run_dbt',
        bash_command='cd /opt/airflow/dbt && dbt build --profiles-dir . --target prod',
    )

    alert_flink_down = BashOperator(
        task_id='alert_flink_down',
        bash_command='echo "ALERT: Flink cluster unhealthy" && exit 1',
    )

    health_check >> [run_dbt, alert_flink_down]
