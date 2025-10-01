# services/orchestrator.py
import os, streamlit as st
from utils import airflow_client as ac

# Streamlit secrets에서 Airflow 설정 읽기
def _cfg():
    cfg = st.secrets["airflow"]
    return dict(base_url=cfg["base_url"],
                username=cfg.get("username"),
                password=cfg.get("password"),
                bearer_token=cfg.get("bearer_token"))

# MRI 파이프라인 실행 (dag_id는 데모/실전 둘 다 이 이름을 씀)
DAG_ID = "mri_pipeline"

def start_mri(conf: dict):
    return ac.trigger_dag(dag_id=DAG_ID, conf=conf, **_cfg())

def get_status(dag_run_id: str):
    run  = ac.get_dag_run(dag_id=DAG_ID, dag_run_id=dag_run_id, **_cfg())
    tis  = ac.get_task_instances(dag_id=DAG_ID, dag_run_id=dag_run_id, **_cfg())
    total = max(len(tis), 1)
    done  = sum(t["state"] in ("success", "skipped") for t in tis)
    failed = [t for t in tis if t["state"] == "failed"]
    return {
        "state": run.get("state", "queued"),
        "progress": int(100*done/total),
        "tasks": [{"task_id": t["task_id"], "state": t["state"]} for t in tis],
        "failed_tasks": [t["task_id"] for t in failed],
        "airflow_url": ac.run_url(**_cfg(), dag_id=DAG_ID, dag_run_id=dag_run_id),
    }

# Streamlit에서 읽을 아티팩트 경로 규약 (공유볼륨)
def artifact_path(dag_run_id: str) -> str:
    # Streamlit 컨테이너 기준 로컬 경로
    return f"./shared/artifacts/mri/{dag_run_id}/report.html"
