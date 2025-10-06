import os
import uuid
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# db 관련
# --- DB 관련 import 수정 ---
from .database import SessionLocal
from .models import JobLog
from . import models
from .database import engine
from sqlalchemy.orm import Session
from fastapi import Depends 

# ===== 환경변수 기본값 =====
AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://airflow:8080")
#AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_API  = f"{AIRFLOW_BASE}/api/v1"
AIRFLOW_DAG  = os.getenv("AIRFLOW_DAG_ID", "mri_pipeline")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.getenv("AIRFLOW_PASSWORD", "admin")

# --- 서버 시작 시 DB 테이블 생성 ---
# 이미 있으면 별 작업 안함
models.Base.metadata.create_all(bind=engine)
# --------------------------------
app = FastAPI(title="AIMed Pipeline Backend")

# Streamlit(별도 컨테이너)에서 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def _auth():
    return (AIRFLOW_USER, AIRFLOW_PASS)

# db session 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"ok": True, "airflow": AIRFLOW_BASE, "dag": AIRFLOW_DAG}

@app.post("/run-job")
def run_job(job_type: str = "MRI 분석", db: Session = Depends(get_db)):
    run_id = f"ui_{uuid.uuid4().hex[:8]}"
    payload = {"dag_run_id": run_id, "conf": {"job_type": job_type}}
    # Airflow mock (실제 Airflow 없이)
    try:
        r = requests.post(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns", json=payload, auth=_auth(), timeout=2)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text)
    except Exception as e:
        print(f"[Mock] Airflow 호출 실패, 테스트용으로 무시: {e}")
        
    # ---- 로그 DB에 저장 ----
    log = JobLog(
        job_id=run_id,
        job_type=job_type,
        status="requested",
        log="Job requested (mock)"
    )
    db.add(log)
    db.commit()
    return {"job_id": run_id, "note": "Airflow 미연동 mock"}

@app.get("/job-status/{job_id}")
def job_status(job_id: str):
    try:
        # 실제 Airflow REST API 호출 부분
        dr = requests.get(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}", auth=_auth(), timeout=2)
        if dr.status_code != 200:
            raise HTTPException(status_code=dr.status_code, detail=dr.text)
        drj = dr.json()
        state = drj.get("state", "unknown")

        tis = requests.get(
            f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}/taskInstances",
            auth=_auth(), timeout=2
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
    except Exception as e:
        # Airflow 요청 실패 시 mock 데이터 반환 (에러 안 나게 함)
        print(f"[Mock] Airflow 상태조회 실패, 더미값 반환: {e}")
        return {
            "status": "mocked",
            "tasks": [{"task_id": "mocked_task", "state": "success"}],
            "progress": 100,
            "airflow_ui": "mock_url",
            "log": f"Mock DagRun {job_id} is mocked"
        }