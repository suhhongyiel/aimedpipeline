# utils/airflow_client.py
import base64, requests

def _headers(username=None, password=None, bearer_token=None):
    if bearer_token:
        return {"Authorization": f"Bearer {bearer_token}", "Content-Type":"application/json"}
    b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {b64}", "Content-Type":"application/json"}

def trigger_dag(base_url, dag_id, conf=None, **auth):
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns"
    r = requests.post(url, json={"conf": conf or {}}, headers=_headers(**auth), timeout=20)
    r.raise_for_status()
    return r.json()  # {'dag_run_id': '...'} 등

def get_dag_run(base_url, dag_id, dag_run_id, **auth):
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
    r = requests.get(url, headers=_headers(**auth), timeout=20)
    r.raise_for_status()
    return r.json()

def get_task_instances(base_url, dag_id, dag_run_id, **auth):
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
    r = requests.get(url, headers=_headers(**auth), timeout=20)
    r.raise_for_status()
    return r.json().get("task_instances", [])

def get_task_log(base_url, dag_id, dag_run_id, task_id, try_number=1, **auth):
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number}"
    r = requests.get(url, headers=_headers(**auth), timeout=30)
    if r.status_code == 404:
        return ""
    r.raise_for_status()
    # Airflow는 {"content": "..."} 형태로 줍니다
    return r.json().get("content", "")

# ⬇️ 새로 추가: XCom 조회
def get_xcom(base_url, dag_id, dag_run_id, task_id, key, **auth):
    url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries/{key}"
    r = requests.get(url, headers=_headers(**auth), timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json().get("value")

# ⬇️ 새로 추가: 헬스 체크(옵션)
def get_health(base_url, **auth):
    url = f"{base_url.rstrip('/')}/health"
    r = requests.get(url, headers=_headers(**auth), timeout=10)
    r.raise_for_status()
    return r.json()



def run_url(base_url, dag_id, dag_run_id):
    return f"{base_url.rstrip('/')}/graph?dag_id={dag_id}&dag_run_id={dag_run_id}"
