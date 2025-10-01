# dags/mri_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.sensors.filesystem import FileSensor
from datetime import datetime, timedelta
import os, time, glob, json

# Airflow 컨테이너 기준 공유 경로 (docker-compose에서 ./shared를 /opt/airflow/shared로 마운트한다고 가정)
SHARED = "/opt/airflow/shared"
ARTIFACT_ROOT = f"{SHARED}/artifacts/mri"

def _ensure_dir(d):
    os.makedirs(d, exist_ok=True)
    return d

def has_files(**ctx):
    conf = ctx["dag_run"].conf or {}
    inbox = conf.get("inbox")  # 예: /opt/airflow/shared/inbox/<job_id>
    if not inbox or not os.path.isdir(inbox):
        print("No inbox provided or not a directory:", inbox)
        return False
    files = glob.glob(os.path.join(inbox, "*"))
    print("Found files:", files)
    return len(files) > 0

def preprocess(**ctx):
    # 데모용 지연
    time.sleep(2)

def inference(**ctx):
    time.sleep(2)

def postprocess(**ctx):
    run_id = ctx["dag_run"].run_id
    conf   = ctx["dag_run"].conf or {}
    inbox  = conf.get("inbox", "N/A")
    out_dir = _ensure_dir(os.path.join(ARTIFACT_ROOT, run_id))
    report = os.path.join(out_dir, "report.html")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"""
        <h2>MRI Pipeline Report</h2>
        <p>Status: Success ✅</p>
        <p>Inbox: {inbox}</p>
        <p>Processed at: {datetime.utcnow()}</p>
        """)
    print("Report:", report)

with DAG(
    dag_id="mri_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,  # 필요시 cron으로 변경
    catchup=False,
    default_args={"retries": 0, "retry_delay": timedelta(minutes=1)},
    tags=["mri","demo"]
) as dag:

    # 업로드 경로에 파일이 없으면 이후 태스크 모두 skip
    check = ShortCircuitOperator(task_id="check_inbox_has_files", python_callable=has_files, provide_context=True)

    # 파일이 있어도 파일시스템 안정화 대기(옵션)
    wait = FileSensor(task_id="wait_for_files",
                      filepath="{{ dag_run.conf['inbox'] }}",
                      poke_interval=15, timeout=600, mode="poke")

    t1 = PythonOperator(task_id="preprocess",  python_callable=preprocess,  provide_context=True)
    t2 = PythonOperator(task_id="inference",   python_callable=inference,   provide_context=True)
    t3 = PythonOperator(task_id="postprocess", python_callable=postprocess, provide_context=True)

    check >> wait >> t1 >> t2 >> t3
