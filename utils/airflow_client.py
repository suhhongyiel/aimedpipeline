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

def run_url(base_url, dag_id, dag_run_id):
    return f"{base_url.rstrip('/')}/graph?dag_id={dag_id}&dag_run_id={dag_run_id}"
