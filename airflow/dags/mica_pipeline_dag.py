"""
MICA Pipeline Airflow DAG
여러 사용자가 동시에 MICA Pipeline을 실행할 때 중앙 집중식 관리를 위한 DAG
리소스 기반 스케줄링을 통해 시스템 리소스(CPU, 메모리)에 따라 동적으로 작업 할당량을 조절합니다.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import os
from pathlib import Path
import re

# 리소스 관리 모듈 import
try:
    from resource_manager import check_system_resources, get_resource_pool_slots
except ImportError:
    # 리소스 관리 모듈이 없는 경우 기본 함수 정의
    def check_system_resources():
        return {"success": True, "recommended_max_tasks": 5, "can_run_more": True}
    def get_resource_pool_slots():
        return 5

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

    # 세부 플래그 입력 (struct/surf는 옵션 사용 안 함)
    proc_structural_flags = conf.get('proc_structural_flags', [])
    proc_surf_flags = conf.get('proc_surf_flags', [])
    post_structural_flags = conf.get('post_structural_flags', [])
    proc_func_flags = conf.get('proc_func_flags', [])
    dwi_flags = conf.get('dwi_flags', [])
    sc_flags = conf.get('sc_flags', [])

    # 호스트 경로 (Docker-in-Docker를 위한 절대 경로)
    host_data_dir = os.getenv('HOST_DATA_DIR', '/home/admin1/Documents/aimedpipeline/data')

    # 파라미터 추출
    subject_id = conf.get('subject_id', 'sub-001')
    session_id = conf.get('session_id', '')
    processes = conf.get('processes', ['proc_structural'])
    bids_dir = conf.get('bids_dir', '/data/bids')
    output_dir = conf.get('output_dir', '/data/derivatives')
    fs_licence = conf.get('fs_licence', '/home/admin1/Documents/aimedpipeline/data/license.txt')
    threads = conf.get('threads', 4)
    freesurfer = conf.get('freesurfer', True)

    must_mount_fs_licence = bool(fs_licence)

    # 디버깅: conf에서 받은 값 확인
    print(f"🔍 DEBUG - Received from Airflow conf:")
    print(f"  subject_id: {subject_id}")
    print(f"  session_id (raw): '{session_id}' (type: {type(session_id)})")
    print(f"  processes: {processes}")

    # ✅ proc_structural 단독 여부
    simple_structural = (processes == ['proc_structural'])
    
    # subject ID에서 "sub-" 제거
    sub_id = subject_id.replace("sub-", "")
    
    # session_id에서 "ses-" 접두사 제거 (사용자가 "ses-01" 형식으로 입력할 수 있음)
    original_session_id = session_id
    if session_id:
        session_id = session_id.replace("ses-", "").strip()
        print(f"🔍 DEBUG - session_id after processing: '{session_id}' (original: '{original_session_id}')")
    else:
        print(f"🔍 DEBUG - session_id is empty or falsy: '{session_id}'")

    # --- flags 정리 유틸 ---
    def normalize_flags(tokens: list[str]) -> list[str]:
        with_val = {"-T1wStr", "-fs_licence", "-surf_dir", "-T1", "-atlas",
                    "-mainScanStr", "-func_pe", "-func_rpe", "-mainScanRun",
                    "-phaseReversalRun", "-topupConfig", "-icafixTraining",
                    "-sesAnat"}
        kv, toggles, passthrough = {}, set(), []
        it = iter(tokens)
        for t in it:
            if t in with_val:
                v = next(it, None)
                if v is None or (isinstance(v, str) and v.startswith("-")):
                    continue
                kv[t] = v
            else:
                if t in ("-freesurfer",):
                    continue
                if t == "-fs_licence":
                    _ = next(it, None)
                    continue
                toggles.add(t) if t.startswith("-") else passthrough.append(t)
        out = []
        for k, v in kv.items():
            if k == "-fs_licence":
                continue
            out += [k, v]
        out += sorted(t for t in toggles if t not in ("-freesurfer",))
        out += passthrough
        return out

    sub_dirname = subject_id if subject_id.startswith("sub-") else f"sub-{subject_id}"
    
    # Session 자동 감지 (session_id가 없을 때 = 전체 세션 처리)
    # session_id가 빈 문자열이면 -ses 옵션을 추가하지 않아 전체 세션이 처리됨
    # 따라서 여기서는 session_id를 설정하지 않고 그대로 빈 문자열로 유지
    if not session_id:
        print(f"ℹ️ No session_id specified - will process all sessions for {subject_id}")
        # session_id를 빈 문자열로 유지하여 전체 세션 처리
        # micapipe는 -ses 옵션이 없으면 자동으로 모든 세션을 처리함
    
    # 컨테이너 이름
    container_name = f"{subject_id}"
    if session_id:
        container_name += f"_ses-{session_id}"
    if processes:
        container_name += f"_{processes[0]}"
    
    # 로그 경로
    log_base = f"{output_dir}/logs/{processes[0] if processes else 'default'}"
    log_file = f"{log_base}/fin/{container_name}.log"
    error_log_file = f"{log_base}/error/{container_name}_error.log"

    # 컨테이너에서 보이는 로그 경로(/data로 치환)
    container_log_base = log_base.replace(host_data_dir, '/data')
    container_log_file = log_file.replace(host_data_dir, '/data')
    container_error_log_file = error_log_file.replace(host_data_dir, '/data')

    # 기본 프로세스 스위치들(-proc_structural, -proc_surf, -post_structural, -proc_func, -dwi, -SC ...)
    process_switches = [f"-{p}" for p in processes]

    # 세부 플래그(허용된 것만): post_structural/func/dwi/sc
    # (struct/surf 옵션은 사용하지 않으므로 제외)
    extra_flags = []
    #extra_flags += proc_structural_flags
    #extra_flags += proc_surf_flags  
    extra_flags += post_structural_flags
    extra_flags += proc_func_flags
    extra_flags += dwi_flags
    extra_flags += sc_flags
    normalized = normalize_flags(extra_flags)
   
    # ✅ 순서 고정 및 중복 제거
    ordered_flags = []
    if "-proc_structural" in process_switches:
        ordered_flags.append("-proc_structural")
    if "-proc_func" in process_switches:
        ordered_flags.append("-proc_func")
        # func 관련 옵션은 -proc_func 바로 뒤에 붙임
        ordered_flags += [f for f in normalized if f in ("-NSR", "-dropTR", "-noFIX")]
    if "-proc_dwi" in process_switches:
        ordered_flags.append("-proc_dwi")
    if "-SC" in process_switches:
        ordered_flags.append("-SC")  
    ordered_flags += [f for f in normalized if f not in ("-NSR", "-dropTR", "-noFIX")]
    process_flags = " ".join(ordered_flags)
  

    # -------------------------
    # Docker 명령어 구성 분기
    # -------------------------
    cmd_parts = [
        "docker run --rm",
        f"--name {container_name}",
        f"-v {bids_dir}:{bids_dir}",
        f"-v {output_dir}:{output_dir}",
    ]

    if simple_structural:
        if must_mount_fs_licence:
            cmd_parts.append(f"-v {fs_licence}:{fs_licence}")

        cmd_parts += [
            "micalab/micapipe:v0.2.3",
            f"-bids {bids_dir}",
            f"-out {output_dir}",
            f"-sub {sub_id}",
        ]
        if session_id:
            cmd_parts.append(f"-ses {session_id}")
            print(f"✅ DEBUG (simple_structural) - Added -ses {session_id} to command")
        else:
            print(f"⚠️ DEBUG (simple_structural) - session_id is empty, NOT adding -ses option")
        cmd_parts.append("-proc_structural")

        if must_mount_fs_licence:
            cmd_parts.append(f"-v {fs_licence}:{fs_licence}")
    else:
        if must_mount_fs_licence:
            cmd_parts.append(f"-v {fs_licence}:{fs_licence}")

        cmd_parts += [
            "micalab/micapipe:v0.2.3",
            f"-bids {bids_dir}",
            f"-out {output_dir}",
            f"-sub {sub_id}",
        ]
        if session_id:
            cmd_parts.append(f"-ses {session_id}")
            print(f"✅ DEBUG (general) - Added -ses {session_id} to command")
        else:
            print(f"⚠️ DEBUG (general) - session_id is empty, NOT adding -ses option")

        cmd_parts += [
            f"-threads {threads}",
            process_flags,
        ]

        if 'proc_surf' in processes:
            cmd_parts.append(f"-freesurfer {'TRUE' if freesurfer else 'FALSE'}")

        # 라이선스 인자는 항상 추가
        if must_mount_fs_licence:
            cmd_parts.append(f"-fs_licence {fs_licence}")

    # 로그 디렉토리 생성 (Airflow 컨테이너 내부 경로)
    mkdir_cmd = f"mkdir -p {container_log_base}/fin {container_log_base}/error"

    # Docker 실행 (로그 리다이렉션 포함 - Airflow 컨테이너 내부 경로)
    docker_cmd = f"{' '.join(cmd_parts)} > {container_log_file} 2> {container_error_log_file}"

    # docker wait로 종료 대기 및 오류 탐지(필요시 강화)
    full_cmd = f"""
    {mkdir_cmd} && \\
    ({docker_cmd} &) && \\
    sleep 2 && \\
    docker wait {container_name} || \\
    (echo "Container {container_name} failed" && exit 1)
    """.strip()

    print("Generated command:")
    print(full_cmd)

    # XCom push
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
    
    # 호스트 데이터 디렉토리 (환경 변수에서 가져오기)
    host_data_dir = os.getenv('HOST_DATA_DIR', '/home/admin1/Documents/aimedpipeline/data')
    
    # 로그 경로 목록 (fin / error 디렉토리 모두 확인)
    log_dirs = [
        Path(f"{host_data_dir}/derivatives/logs/proc_func/error"),
        Path(f"{host_data_dir}/derivatives/logs/proc_func/fin"),
        Path(f"{host_data_dir}/derivatives/logs/proc_structural/error"),
        Path(f"{host_data_dir}/derivatives/logs/proc_structural/fin"),
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

# 시스템 리소스에 기반한 동적 concurrency 계산
# 리소스가 충분하면 더 많은 작업 실행, 부족하면 제한
try:
    resource_info = check_system_resources()
    if resource_info.get("success"):
        # 리소스 기반 동적 concurrency 설정
        # CPU와 메모리 중 작은 값 사용, 최소 2개는 보장
        dynamic_concurrency = max(2, resource_info.get("recommended_max_tasks", 5))
        # 최대 10개로 제한 (과도한 리소스 사용 방지)
        dynamic_concurrency = min(dynamic_concurrency, 10)
        print(f"🔍 System resources check: Recommended concurrency = {dynamic_concurrency}")
    else:
        dynamic_concurrency = 5  # 기본값
except Exception as e:
    print(f"⚠️ Failed to check system resources: {e}, using default concurrency")
    dynamic_concurrency = 5  # 기본값

with DAG(
    dag_id=DAG_ID,
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    default_args=default_args,
    tags=["mica", "neuroimaging", "production"],
    max_active_runs=5,  # 최대 5개의 DAG 동시 실행
    concurrency=dynamic_concurrency,  # 시스템 리소스에 기반한 동적 동시 실행 수
    description="MICA Pipeline - Multi-user neuroimaging processing pipeline with resource-based scheduling",
) as dag:

    # Task 0: 리소스 확인 (선택적, 리소스 체크 실패해도 계속 진행)
    def check_resources(**context):
        """시스템 리소스를 확인하고 로그에 기록합니다."""
        try:
            resources = check_system_resources()
            if resources.get("success"):
                print(f"📊 System Resources:")
                print(f"  CPU: {resources['cpu']['percent']}% used ({resources['cpu']['available']:.1f} cores available)")
                print(f"  Memory: {resources['memory']['percent']}% used ({resources['memory']['available_gb']:.2f} GB available)")
                print(f"  Running containers: {resources['running_containers']}")
                print(f"  Recommended max tasks: {resources['recommended_max_tasks']}")
                print(f"  Can run more: {resources['can_run_more']}")
            else:
                print(f"⚠️ Resource check failed: {resources.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"⚠️ Resource check error: {e}")
    
    resource_check_task = PythonOperator(
        task_id="check_resources",
        python_callable=check_resources,
        pool="default_pool",  # 리소스 풀 사용 (선택적)
    )
    
    # Task 1: 시작 로그
    start_task = PythonOperator(
        task_id="log_start",
        python_callable=log_start,
        pool="default_pool",  # 리소스 풀 사용
    )
    
    # Task 2: Docker 명령어 생성
    build_command_task = PythonOperator(
        task_id="build_command",
        python_callable=build_docker_command,
        pool="default_pool",  # 리소스 풀 사용
    )
    
    # Task 3: MICA Pipeline 실행
    # 주의: Airflow 컨테이너에서 호스트의 Docker를 사용하려면 Docker socket 마운트 필요
    run_micapipe_task = BashOperator(
        task_id="run_micapipe",
        bash_command="{{ ti.xcom_pull(key='docker_command', task_ids='build_command') }}",
        execution_timeout=timedelta(hours=6),
        pool="default_pool",  # 리소스 풀 사용 (가장 리소스 집약적인 작업)
    )
    
    # Task 4: 완료 로그
    complete_task = PythonOperator(
        task_id="log_completion",
        python_callable=log_completion,
        pool="default_pool",  # 리소스 풀 사용
    )
    
    # Task 의존성 설정
    # 리소스 확인 -> 시작 로그 -> 명령어 생성 -> 실행 -> 완료 로그
    resource_check_task >> start_task >> build_command_task >> run_micapipe_task >> complete_task

