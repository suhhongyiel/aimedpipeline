from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os, random, time

DAG_ID = "mri_pipeline"

def _run_step(step_name: str, **context):
    fail_rate = float(os.getenv("FAIL_RATE", "0.2"))
    sleep_sec = random.randint(2, 6)
    print(f"[{step_name}] running... (sleep {sleep_sec}s)")
    time.sleep(sleep_sec)
    if random.random() < fail_rate:
        raise RuntimeError(f"{step_name} failed randomly")
    print(f"[{step_name}] success")

default_args = {
    "owner": "you",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(seconds=5),
}

with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    tags=["mri", "demo"],
) as dag:

    bids = PythonOperator(
        task_id="1_bids_conversion",
        python_callable=_run_step,
        op_kwargs={"step_name": "BIDS conversion"},
    )
    proc_struct = PythonOperator(
        task_id="2_proc_structural",
        python_callable=_run_step,
        op_kwargs={"step_name": "proc_structural"},
    )
    proc_surf = PythonOperator(
        task_id="3_proc_surf",
        python_callable=_run_step,
        op_kwargs={"step_name": "proc_surf"},
    )
    post_struct = PythonOperator(
        task_id="4_post_structural",
        python_callable=_run_step,
        op_kwargs={"step_name": "post_structural"},
    )
    proc_func = PythonOperator(
        task_id="5_proc_func",
        python_callable=_run_step,
        op_kwargs={"step_name": "proc_func"},
    )
    finalize = PythonOperator(
        task_id="6_finalize_results",
        python_callable=_run_step,
        op_kwargs={"step_name": "finalize_results"},
    )

    bids >> proc_struct >> proc_surf >> post_struct >> proc_func >> finalize
