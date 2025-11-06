"""
MICA Pipeline Airflow DAG
여러 사용자가 동시에 MICA Pipeline을 실행할 때 중앙 집중식 관리를 위한 DAG
"""
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import os

DAG_ID = "mica_pipeline"

def log_start(**context):
    """작업 시작 로그"""
    conf = context['dag_run'].conf
    subject_id = conf.get('subject_id', 'unknown')
    session_id = conf.get('session_id', '')
    processes = conf.get('processes', [])
    user = conf.get('user', 'anonymous')
    
    print(f"=" * 80)
    print(f"MICA Pipeline 시작")
    print(f"User: {user}")
    print(f"Subject: {subject_id}")
    print(f"Session: {session_id if session_id else 'auto-detect'}")
    print(f"Processes: {', '.join(processes)}")
    print(f"=" * 80)
    
    # XCom에 정보 저장 (다음 task에서 사용)
    return {
        'subject_id': subject_id,
        'session_id': session_id,
        'processes': processes,
        'user': user
    }

def build_docker_command(**context):
    """Docker 실행 명령어 생성"""
    import os
    from pathlib import Path
    
    ti = context['ti']
    conf = context['dag_run'].conf
    
    # 파라미터 추출
    subject_id = conf.get('subject_id', 'sub-001')
    session_id = conf.get('session_id', '')
    processes = conf.get('processes', ['proc_structural'])
    bids_dir = conf.get('bids_dir', '/data/bids')
    output_dir = conf.get('output_dir', '/data/derivatives')
    fs_licence = conf.get('fs_licence', '/data/license.txt')
    threads = conf.get('threads', 4)
    freesurfer = conf.get('freesurfer', True)
    
    # subject ID에서 "sub-" 제거
    sub_id = subject_id.replace("sub-", "")
    
    # Session 자동 감지 (session_id가 없을 때)
    if not session_id:
        subject_path = Path(bids_dir) / subject_id
        if subject_path.exists():
            # ses-* 디렉토리 찾기
            session_dirs = [d.name.replace("ses-", "") for d in subject_path.iterdir() 
                          if d.is_dir() and d.name.startswith("ses-")]
            if session_dirs:
                session_id = session_dirs[0]  # 첫 번째 session 사용
                print(f"Auto-detected session: {session_id}")
            else:
                print("No session found - using direct path")
        else:
            print(f"Warning: Subject path not found: {subject_path}")
    
    # 컨테이너 이름 생성
    container_name = f"{subject_id}"
    if session_id:
        container_name += f"_ses-{session_id}"
    if processes:
        container_name += f"_{processes[0]}"
    
    # 로그 디렉토리
    log_base = f"{output_dir}/logs/{processes[0] if processes else 'default'}"
    log_file = f"{log_base}/fin/{container_name}.log"
    error_log_file = f"{log_base}/error/{container_name}_error.log"
    
    # 프로세스 플래그
    process_flags = " ".join([f"-{p}" for p in processes])
    
    # Docker 명령어 구성
    cmd_parts = [
        "docker run --rm",
        f"--name {container_name}",
        f"-v {bids_dir}:{bids_dir}",
        f"-v {output_dir}:{output_dir}",
    ]
    
    # FreeSurfer 라이센스
    if os.path.exists(fs_licence):
        cmd_parts.append(f"-v {fs_licence}:{fs_licence}")
    
    cmd_parts.extend([
        "micalab/micapipe:v0.2.3",
        f"-bids {bids_dir}",
        f"-out {output_dir}",
        f"-sub {sub_id}",
    ])
    
    if session_id:
        cmd_parts.append(f"-ses {session_id}")
    
    if os.path.exists(fs_licence):
        cmd_parts.append(f"-fs_licence {fs_licence}")
    
    cmd_parts.extend([
        f"-threads {threads}",
        process_flags,
        f"-freesurfer {'TRUE' if freesurfer else 'FALSE'}",
    ])
    
    # 로그 디렉토리 생성 명령
    mkdir_cmd = f"mkdir -p {log_base}/fin {log_base}/error"
    
    # 최종 명령어 (로그 리다이렉션 포함)
    full_cmd = f"{mkdir_cmd} && {' '.join(cmd_parts)} > {log_file} 2> {error_log_file}"
    
    print(f"Generated command:")
    print(full_cmd)
    
    # XCom에 저장
    ti.xcom_push(key='docker_command', value=full_cmd)
    ti.xcom_push(key='container_name', value=container_name)
    ti.xcom_push(key='log_file', value=log_file)
    ti.xcom_push(key='error_log_file', value=error_log_file)
    
    return full_cmd

def log_completion(**context):
    """작업 완료 로그 및 에러 검증"""
    from pathlib import Path
    
    ti = context['ti']
    container_name = ti.xcom_pull(key='container_name', task_ids='build_command')
    log_file = ti.xcom_pull(key='log_file', task_ids='build_command')
    
    print(f"=" * 80)
    print(f"MICA Pipeline 완료")
    print(f"Container: {container_name}")
    
    # 로그 파일에서 에러 확인 (MICA Pipeline은 exit 0으로 종료해도 에러 발생 가능)
    log_path = Path(log_file)
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
            if "[ ERROR ]" in log_content:
                error_lines = [line for line in log_content.split('\n') if 'ERROR' in line]
                print(f"\n{'!' * 80}")
                print(f"WARNING: Errors found in log file!")
                print(f"{'!' * 80}")
                for line in error_lines[-5:]:  # 마지막 5개 에러 라인
                    print(line)
                print(f"{'!' * 80}\n")
                raise Exception("MICA Pipeline completed with errors. Check log file for details.")
    
    print(f"=" * 80)

default_args = {
    "owner": "mica_pipeline",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,  # 실패 시 1번 재시도
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=6),  # 최대 6시간
}

with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    default_args=default_args,
    tags=["mica", "neuroimaging", "production"],
    max_active_runs=5,  # 최대 5개의 DAG 동시 실행
    concurrency=10,  # 최대 10개의 task 동시 실행
    description="MICA Pipeline - Multi-user neuroimaging processing pipeline",
) as dag:

    # Task 1: 시작 로그
    start_task = PythonOperator(
        task_id="log_start",
        python_callable=log_start,
    )
    
    # Task 2: Docker 명령어 생성
    build_command_task = PythonOperator(
        task_id="build_command",
        python_callable=build_docker_command,
    )
    
    # Task 3: MICA Pipeline 실행
    # 주의: Airflow 컨테이너에서 호스트의 Docker를 사용하려면 Docker socket 마운트 필요
    run_micapipe_task = BashOperator(
        task_id="run_micapipe",
        bash_command="{{ ti.xcom_pull(key='docker_command', task_ids='build_command') }}",
        execution_timeout=timedelta(hours=6),
    )
    
    # Task 4: 완료 로그
    complete_task = PythonOperator(
        task_id="log_completion",
        python_callable=log_completion,
    )
    
    # Task 의존성 설정
    start_task >> build_command_task >> run_micapipe_task >> complete_task

