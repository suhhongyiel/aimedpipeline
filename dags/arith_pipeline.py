from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime
import os

ARTIFACT_ROOT = "/opt/airflow/shared/artifacts/arith"

def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def parse_conf(**ctx):
    conf = ctx["dag_run"].conf or {}
    try:
        a = float(conf.get("a"))
        b = float(conf.get("b"))
        op = str(conf.get("op", "add")).lower()
        if op not in {"add", "sub", "mul", "div"}:
            raise ValueError("Unsupported op")
        ti = ctx["ti"]
        ti.xcom_push(key="a", value=a)
        ti.xcom_push(key="b", value=b)
        ti.xcom_push(key="op", value=op)
    except Exception as e:
        raise ValueError(f"Bad inputs: {conf} ({e})")

def branch_by_op(**ctx):
    op = ctx["ti"].xcom_pull(key="op")
    return {"add": "do_add", "sub": "do_sub", "mul": "do_mul", "div": "do_div"}[op]

def _math(op, a, b):
    if op == "add": return a + b
    if op == "sub": return a - b
    if op == "mul": return a * b
    if op == "div":
        if b == 0: raise ZeroDivisionError("b cannot be zero")
        return a / b

def compute(op_key, **ctx):
    ti = ctx["ti"]
    a = ti.xcom_pull(key="a")
    b = ti.xcom_pull(key="b")
    res = _math(op_key, a, b)
    ti.xcom_push(key="result", value=res)

def save_report(**ctx):
    run_id = ctx["dag_run"].run_id
    ti = ctx["ti"]
    a = ti.xcom_pull(key="a")
    b = ti.xcom_pull(key="b")
    op = ti.xcom_pull(key="op")
    result = ti.xcom_pull(key="result")
    out_dir = _ensure_dir(os.path.join(ARTIFACT_ROOT, run_id))
    html = f"""
    <h2>Arithmetic Demo Report</h2>
    <p>Inputs: a={a}, b={b}, op={op}</p>
    <p><b>Result: {result}</b></p>
    <p>Run ID: {run_id}</p>
    """
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html)

with DAG(
    dag_id="arith_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["demo","arith"]
) as dag:
    parse = PythonOperator(task_id="parse_conf", python_callable=parse_conf)

    branch = BranchPythonOperator(task_id="branch_by_op", python_callable=branch_by_op)

    add = PythonOperator(task_id="do_add", python_callable=lambda **c: compute("add", **c))
    sub = PythonOperator(task_id="do_sub", python_callable=lambda **c: compute("sub", **c))
    mul = PythonOperator(task_id="do_mul", python_callable=lambda **c: compute("mul", **c))
    div = PythonOperator(task_id="do_div", python_callable=lambda **c: compute("div", **c))

    save = PythonOperator(
        task_id="save_report",
        python_callable=save_report,
        # 브랜치 이후 합류 노드는 이 트리거룰이 핵심!
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    parse >> branch
    branch >> [add, sub, mul, div] >> save
