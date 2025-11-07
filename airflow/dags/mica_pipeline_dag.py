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
from pathlib import Path
import re

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
    proc_structural_flags = conf.get('proc_structural_flags', [])
    proc_surf_flags = conf.get('proc_surf_flags', [])
    post_structural_flags = conf.get('post_structural_flags', [])
    proc_func_flags = conf.get('proc_func_flags', [])
    dwi_flags = conf.get('dwi_flags', [])
    sc_flags = conf.get('sc_flags', [])

    # 호스트 경로 (Docker-in-Docker를 위한 절대 경로)
    host_data_dir = os.getenv('HOST_DATA_DIR', '/private/boonam/98-dev/aimedpipeline/data')
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

    # 로그 디렉토리 (컨테이너 내부 경로 - 로그 파일 읽기용)
    container_log_base = log_base.replace(host_data_dir, '/data')
    container_log_file = log_file.replace(host_data_dir, '/data')
    container_error_log_file = error_log_file.replace(host_data_dir, '/data')

    # 프로세스 플래그
    # 기본 프로세스 스위치들(-proc_func, -proc_dwi, -SC 등)
    process_switches = [f"-{p}" for p in processes]

    # 세부 플래그(이미 ["-옵션", "값", ...] 형태라고 가정)
    extra_flags = []
    extra_flags += proc_structural_flags
    extra_flags += proc_surf_flags
    extra_flags += post_structural_flags
    extra_flags += proc_func_flags
    extra_flags += dwi_flags
    extra_flags += sc_flags

    process_flags = " ".join(process_switches + extra_flags)


    
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
    
    # 로그 디렉토리 생성 명령 (Airflow 컨테이너 내부 경로)
    mkdir_cmd = f"mkdir -p {container_log_base}/fin {container_log_base}/error"
    # Docker 명령어 (로그 리다이렉션 포함 - Airflow 컨테이너 내부 경로)
    docker_cmd = f"{' '.join(cmd_parts)} > {container_log_file} 2> {container_error_log_file}"

    # docker 완료 후 log에 error 검사 (Airflow fail 유도)
    check_log_cmd = f"""
    if grep -iE 'error|traceback|license|failed|killed|permission denied' {container_log_file} {container_error_log_file} >/dev/null 2>&1; then
        echo '❌ Error detected in logs.';
        tail -n 10 {container_log_file};
        exit 1;
    fi
    """
    # 최종 명령어: docker run 후 컨테이너가 완료될 때까지 대기
    # 1. 로그 디렉토리 생성
    # 2. Docker 실행 (백그라운드)
    # 3. 컨테이너 시작 대기
    # 4. docker wait로 컨테이너 종료 대기
    # 5. exit code 확인하여 에러면 실패 처리
    full_cmd = f"""
    {mkdir_cmd} && \\
    ({docker_cmd} &) && \\
    sleep 2 && \\
    
    docker wait {container_name} || \\
    (echo "Container {container_name} failed" && exit 1)
    """.strip()
    
    
    print(f"Generated command:")
    print(full_cmd)
    
    # XCom에 저장
    ti.xcom_push(key='docker_command', value=full_cmd)
    ti.xcom_push(key='container_name', value=container_name)
    ti.xcom_push(key='log_file', value=container_log_file)
    ti.xcom_push(key='error_log_file', value=container_error_log_file)

    return full_cmd

def log_completion(**context):
    """MICA Pipeline 완료 후 로그 검증 (error 패턴 및 로그 길이 포함)"""
    from pathlib import Path
    import re

    ti = context['ti']
    container_name = ti.xcom_pull(key='container_name', task_ids='build_command')
    main_log_file = ti.xcom_pull(key='log_file', task_ids='build_command')
    error_log_file = ti.xcom_pull(key='error_log_file', task_ids='build_command')

    print("=" * 80)
    print(f"🧠 MICA Pipeline 완료 검증 시작")
    print(f"Container: {container_name}")
    print("=" * 80)

    # 주요 검사 기준
    error_keywords = [
        "error", "traceback", "exception", "license",
        "no such file", "killed", "segmentation fault",
        "failed", "permission denied"
    ]
    #100번 기준으로 /home/admin1/Documents/aimedpipeline 이거로 바꾸긴 해야함
    # 로그 경로 목록 (fin / error 디렉토리 모두 확인)
    log_dirs = [
        Path("/private/boonam/98-dev/aimedpipeline/data/derivatives/logs/proc_func/error"),
        Path("/private/boonam/98-dev/aimedpipeline/data/derivatives/logs/proc_func/fin"),
        Path("/private/boonam/98-dev/aimedpipeline/data/derivatives/logs/proc_structural/error"),
        Path("/private/boonam/98-dev/aimedpipeline/data/derivatives/logs/proc_structural/fin"),
    ]

    # 개별 로그 파일도 직접 추가 (XCom으로 전달된 파일)
    xcom_logs = [Path(main_log_file), Path(error_log_file)]

    found_issues = []
    total_lines = 0

    # 로그 파일들 순회
    for log_source in log_dirs + xcom_logs:
        if not log_source.exists():
            continue

        # 개별 파일 또는 디렉토리 처리
        if log_source.is_dir():
            log_files = list(log_source.glob("*.log"))
        else:
            log_files = [log_source]

        for log_file in log_files:
            try:
                text = log_file.read_text(errors="ignore")
            except Exception as e:
                print(f"⚠️ Failed to read {log_file}: {e}")
                continue

            lines = text.splitlines()
            total_lines += len(lines)

            # 1️⃣ 에러 문자열 검사
            for kw in error_keywords:
                if re.search(kw, text, re.IGNORECASE):
                    found_issues.append((log_file, kw))

            # 2️⃣ 로그 줄 수 너무 짧으면 경고
            if len(lines) < 50:
                found_issues.append((log_file, f"Too short ({len(lines)} lines)"))

    # 3️⃣ 문제 있으면 실패 처리
    if found_issues:
        print("\n❌ Issues found in MICA logs:")
        for f, msg in found_issues:
            print(f"  - {f}: {msg}")
        print("=" * 80)
        raise Exception("Detected errors or insufficient log content in MICA pipeline outputs.")

    # 4️⃣ 로그가 너무 없으면 실패
    if total_lines == 0:
        raise Exception("No log content found — pipeline may have crashed early.")

    print("✅ Log completion check passed successfully.")
    print("=" * 80)


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

