import os
import uuid
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ===== 환경변수 기본값 =====
AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://airflow:8080")
AIRFLOW_API  = f"{AIRFLOW_BASE}/api/v1"
AIRFLOW_DAG  = os.getenv("AIRFLOW_DAG_ID", "mri_pipeline")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.getenv("AIRFLOW_PASSWORD", "admin")

app = FastAPI(title="AIMed Pipeline Backend")

# Streamlit(별도 컨테이너)에서 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def _auth():
    return (AIRFLOW_USER, AIRFLOW_PASS)

@app.get("/")
def root():
    return {"ok": True, "airflow": AIRFLOW_BASE, "dag": AIRFLOW_DAG}

@app.post("/run-job")
def run_job(job_type: str = "MRI 분석"):
    # Airflow DAGRun 생성
    run_id = f"ui_{uuid.uuid4().hex[:8]}"
    payload = {"dag_run_id": run_id, "conf": {"job_type": job_type}}
    r = requests.post(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns", json=payload, auth=_auth())
    if r.status_code not in (200, 201):
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return {"job_id": run_id}

@app.get("/job-status/{job_id}")
def job_status(job_id: str):
    # 전체 DagRun 상태
    dr = requests.get(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}", auth=_auth())
    if dr.status_code != 200:
        raise HTTPException(status_code=dr.status_code, detail=dr.text)
    drj = dr.json()
    state = drj.get("state", "unknown")

    # 태스크 인스턴스 상태
    tis = requests.get(
        f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}/taskInstances",
        auth=_auth()
    )
    if tis.status_code != 200:
        raise HTTPException(status_code=tis.status_code, detail=tis.text)
    tasks = []
    for ti in tis.json().get("task_instances", []):
        tasks.append({
            "task_id": ti["task_id"],
            "state": ti["state"],
            "start_date": ti.get("start_date"),
            "end_date": ti.get("end_date"),
            "try_number": ti.get("try_number"),
        })

    # 진행률(성공한 태스크 비율 + 실행중 가중치)
    total = max(len(tasks), 1)
    success = sum(1 for t in tasks if (t["state"] or "").lower() == "success")
    running = sum(1 for t in tasks if (t["state"] or "").lower() in ("queued", "running"))
    progress = int((success/total)*100 + (running/total)*25)
    progress = min(progress, 99 if state.lower() not in ("success", "failed") else 100)

    ui_url = f"{AIRFLOW_BASE}/dag/{AIRFLOW_DAG}/grid?dag_run_id={job_id}"
    return {
        "status": state, "tasks": tasks, "progress": progress,
        "airflow_ui": ui_url, "log": f"DagRun {job_id} is {state}"
    }
