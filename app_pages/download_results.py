"""
결과 다운로드 페이지 모듈 - MICA Pipeline 통합
"""
import streamlit as st
import pandas as pd
import requests
import os
import time
from datetime import datetime
from requests.exceptions import Timeout, ConnectionError

# FastAPI 서버 주소
FASTAPI_SERVER_URL = os.getenv(
    "FASTAPI_SERVER_URL",
    st.secrets.get("api", {}).get("fastapi_base_url", "http://localhost:8000")
)

def fetch_mica_jobs(user: str = None):
    """MICA Pipeline Job 목록을 가져옵니다. (로그인한 사용자만)"""
    try:
        params = {}
        if user:
            params["user"] = user
        # 타임아웃을 30초로 증가 (상태 확인에 시간이 걸릴 수 있음)
        response = requests.get(f"{FASTAPI_SERVER_URL}/mica-jobs", params=params, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result is None:
                return {"success": False, "jobs": [], "summary": {"processing": 0, "completed": 0, "failed": 0}}
            return result
        return {"success": False, "jobs": [], "summary": {"processing": 0, "completed": 0, "failed": 0}}
    except requests.exceptions.Timeout:
        return {
            "success": False, 
            "jobs": [], 
            "summary": {"processing": 0, "completed": 0, "failed": 0},
            "error": "요청 시간 초과 (30초). 서버가 처리 중일 수 있습니다. 잠시 후 다시 시도해주세요."
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False, 
            "jobs": [], 
            "summary": {"processing": 0, "completed": 0, "failed": 0},
            "error": "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
        }
    except Exception as e:
        return {
            "success": False, 
            "jobs": [], 
            "summary": {"processing": 0, "completed": 0, "failed": 0},
            "error": f"오류 발생: {str(e)}"
        }

def format_duration(seconds):
    """시간을 읽기 쉬운 형식으로 변환"""
    if seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def status_emoji(status):
    """상태에 따른 이모지 반환"""
    if status == "completed":
        return "✅"
    elif status == "processing":
        return "⏳"
    elif status == "failed":
        return "❌"
    return "❓"

def render():
    """결과 다운로드 페이지 렌더링"""
    st.title("📥 Download Results & Pipeline Status")
    st.markdown("---")
    
    # 자동 새로고침 설정 (30초마다)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    if 'auto_refresh_enabled' not in st.session_state:
        st.session_state.auto_refresh_enabled = True
    
    # 자동 새로고침 체크박스
    auto_refresh_enabled = st.checkbox("🔄 자동 새로고침 (30초)", value=st.session_state.auto_refresh_enabled, key="auto_refresh_checkbox")
    st.session_state.auto_refresh_enabled = auto_refresh_enabled
    
    # 로그인한 사용자 정보 가져오기
    current_user = st.session_state.get("username", "anonymous")
    
    # 시스템 리소스 정보 가져오기 (에러가 발생해도 계속 진행)
    try:
        resources_response = requests.get(f"{FASTAPI_SERVER_URL}/system-resources", timeout=10)
        if resources_response.status_code == 200:
            resources = resources_response.json()
            if resources and isinstance(resources, dict) and resources.get("success"):
                cpu_info = resources.get("cpu", {})
                memory_info = resources.get("memory", {})
                disk_info = resources.get("disk", {})
                docker_info = resources.get("docker", {})
                
                if cpu_info and memory_info and disk_info and docker_info:
                    st.markdown("### 💻 시스템 리소스")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("CPU 사용률", f"{cpu_info.get('percent', 0)}%")
                    with col2:
                        st.metric("메모리 사용률", f"{memory_info.get('percent', 0)}%", 
                                 f"{memory_info.get('used_gb', 0):.1f}GB / {memory_info.get('total_gb', 0):.1f}GB")
                    with col3:
                        st.metric("디스크 사용률", f"{disk_info.get('percent', 0)}%",
                                 f"{disk_info.get('used_gb', 0):.1f}GB / {disk_info.get('total_gb', 0):.1f}GB")
                    with col4:
                        st.metric("실행 중인 컨테이너", docker_info.get('mica_containers', 0),
                                 f"전체: {docker_info.get('total_containers', 0)}")
                    st.markdown("---")
    except requests.exceptions.Timeout:
        # 타임아웃은 조용히 무시 (시스템 리소스는 선택적 정보)
        pass
    except Exception as e:
        # 에러는 조용히 무시 (시스템 리소스는 선택적 정보)
        pass
    
    # MICA Pipeline Job 데이터 가져오기 (로그인한 사용자만)
    with st.spinner("MICA Pipeline 작업 목록을 불러오는 중..."):
        jobs_response = fetch_mica_jobs(user=current_user)
    
    if not jobs_response.get("success"):
        error_msg = jobs_response.get("error", "작업 목록을 불러올 수 없습니다.")
        st.error(f"❌ {error_msg}")
        
        # 재시도 버튼 제공
        if st.button("🔄 다시 시도", key="retry_fetch_jobs"):
            st.rerun()
        
        # 빈 상태로 계속 진행 (에러 메시지만 표시)
        st.info("💡 작업 목록을 불러올 수 없어도 다른 기능은 사용할 수 있습니다.")
        return
    
    jobs = jobs_response.get("jobs", [])
    summary = jobs_response.get("summary", {})
    
    # 통계 정보 표시
    st.markdown("### 📊 MICA Pipeline Status Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Jobs", len(jobs))
    
    with col2:
        st.metric("⏳ Processing", summary.get("processing", 0))
    
    with col3:
        st.metric("✅ Completed", summary.get("completed", 0))
    
    with col4:
        st.metric("❌ Failed", summary.get("failed", 0))
    
    st.markdown("---")
    
    # 새로고침 버튼 및 자동 새로고침 상태 표시 (중복 제거)
    col_refresh, col_auto = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 새로고침", key="refresh_results"):
            st.session_state.last_refresh = time.time()  # 타임스탬프 리셋
            st.rerun()
    
    with col_auto:
        if auto_refresh_enabled:
            elapsed = time.time() - st.session_state.last_refresh
            remaining = max(0, int(30 - elapsed))
            if remaining > 0:
                st.caption(f"⏱️ 자동 새로고침: {remaining}초 후")
            else:
                # 30초가 지났으면 자동 새로고침
                st.session_state.last_refresh = time.time()
                st.rerun()
        else:
            st.caption("⏸️ 자동 새로고침 비활성화됨")
    
    # 필터링 옵션
    st.markdown("### 🔍 Filter Jobs")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            options=['All', 'Processing', 'Completed', 'Failed'],
            index=0
        )
    
    with col2:
        # 프로세스 목록 추출
        all_processes = list(set([job.get("processes", "").split(",")[0] for job in jobs if job.get("processes")]))
        process_filter = st.selectbox(
            "Process Filter",
            options=['All'] + all_processes,
            index=0
        )
    
    with col3:
        # Subject 목록 추출
        all_subjects = list(set([job.get("subject_id", "") for job in jobs if job.get("subject_id")]))
        subject_filter = st.selectbox(
            "Subject Filter",
            options=['All'] + all_subjects,
            index=0
        )
    
    # 필터 적용
    filtered_jobs = jobs
    if status_filter != 'All':
        filtered_jobs = [j for j in filtered_jobs if j.get("status") == status_filter.lower()]
    if process_filter != 'All':
        filtered_jobs = [j for j in filtered_jobs if process_filter in j.get("processes", "")]
    if subject_filter != 'All':
        filtered_jobs = [j for j in filtered_jobs if j.get("subject_id") == subject_filter]
    
    # 결과 테이블
    st.markdown("### 📋 Job Results")
    
    if not filtered_jobs:
        st.info("ℹ️ No jobs found with current filters.")
        st.markdown("""
        **💡 Suggestions:**
        - Try changing the filter settings
        - Run a new pipeline from the '🧠 MICA Pipeline' menu
        """)
        return
    
    # 선택 지우기 버튼
    col_clear, col_spacer = st.columns([1, 4])
    with col_clear:
        if st.button("🗑️ 선택 지우기", key="clear_selection"):
            if 'selected_jobs' in st.session_state:
                del st.session_state['selected_jobs']
            st.rerun()
    
    # DataFrame으로 변환
    df_data = []
    for i, job in enumerate(filtered_jobs):
        df_data.append({
            "Select": False,  # 체크박스
            "Status": status_emoji(job.get("status", "")) + " " + job.get("status", "").capitalize(),
            "Subject": job.get("subject_id", ""),
            "Session": job.get("session_id", "-"),
            "Process": job.get("processes", "").split(",")[0] if job.get("processes") else "-",
            "User": job.get("user", "anonymous"),
            "Started": datetime.fromisoformat(job.get("started_at")).strftime("%Y-%m-%d %H:%M") if job.get("started_at") else "-",
            "Duration": format_duration(job.get("duration")),
            "Progress": f"{job.get('progress', 0):.0f}%",
            "Job ID": job.get("job_id", ""),
            "_job_data": job  # 원본 데이터 저장 (표시 안 됨)
        })
    
    df = pd.DataFrame(df_data)
    
    # 상태별 색상 표시
    def style_status(val):
        if "✅" in str(val):
            return 'background-color: #d4edda; color: #155724'
        elif "⏳" in str(val):
            return 'background-color: #fff3cd; color: #856404'
        elif "❌" in str(val):
            return 'background-color: #f8d7da; color: #721c24'
        return ''
    
    # _job_data 컬럼 제외하고 표시
    display_df = df.drop(columns=['_job_data'])
    styled_df = display_df.style.applymap(style_status, subset=['Status'])
    
    # 데이터 에디터로 표시 (체크박스 기능)
    edited_df = st.data_editor(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select jobs to delete",
                default=False,
            )
        },
        disabled=["Status", "Subject", "Session", "Process", "User", "Started", "Duration", "Progress", "Job ID"],
        key="job_table"
    )
    
    # 선택된 항목 삭제 버튼
    selected_rows = edited_df[edited_df["Select"] == True]
    if len(selected_rows) > 0:
        st.warning(f"⚠️ {len(selected_rows)}개 항목이 선택되었습니다.")
        if st.button(f"🗑️ 선택한 {len(selected_rows)}개 항목 삭제", type="primary"):
            # 선택된 job ID 추출
            selected_job_ids = []
            for idx in selected_rows.index:
                selected_job_ids.append(df.loc[idx, "_job_data"]["id"])
            
            # 삭제 API 호출
            try:
                for job_id in selected_job_ids:
                    response = requests.delete(
                        f"{FASTAPI_SERVER_URL}/mica-jobs/{job_id}",
                        timeout=5
                    )
                    if response.status_code != 200:
                        st.error(f"Failed to delete job {job_id}")
                
                st.success(f"✅ {len(selected_job_ids)}개 항목이 삭제되었습니다.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ 삭제 실패: {str(e)}")
    
    st.markdown("---")
    
    # 상세 정보 및 다운로드
    completed_jobs = [j for j in filtered_jobs if j.get("status") == "completed"]
    
    if completed_jobs:
        st.markdown("### 💾 Download Completed Results")
        
        # 작업 선택
        job_options = {
            f"{job.get('subject_id', '')} - {job.get('processes', '').split(',')[0]} ({datetime.fromisoformat(job.get('started_at')).strftime('%Y-%m-%d %H:%M') if job.get('started_at') else ''})": job
            for job in completed_jobs
        }
        
        selected_job_name = st.selectbox(
            "Select Job to Download",
            options=list(job_options.keys()),
            help="Choose a specific job to download its results"
        )
        
        selected_job = job_options[selected_job_name]
        
        # 선택된 작업 정보 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **📋 Job Details:**
            - **Job ID:** `{selected_job.get('job_id', '')}`
            - **Subject:** `{selected_job.get('subject_id', '')}`
            - **Session:** `{selected_job.get('session_id', '-')}`
            - **Process:** `{selected_job.get('processes', '')}`
            """)
        
        with col2:
            st.markdown(f"""
            **📊 Execution Info:**
            - **Status:** {status_emoji(selected_job.get('status', ''))} {selected_job.get('status', '').capitalize()}
            - **Started:** {datetime.fromisoformat(selected_job.get('started_at')).strftime('%Y-%m-%d %H:%M:%S') if selected_job.get('started_at') else '-'}
            - **Duration:** {format_duration(selected_job.get('duration'))}
            - **Container:** `{selected_job.get('container_name', '')}`
            """)
        
        # 로그 파일 표시
        st.markdown("#### 📄 Log Files")
        
        log_file = selected_job.get("log_file", "")
        error_log_file = selected_job.get("error_log_file", "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if log_file:
                st.text_input("Standard Output Log", value=log_file, disabled=True)
                if st.button("📖 View Standard Log", key="view_std_log"):
                    try:
                        response = requests.get(
                            f"{FASTAPI_SERVER_URL}/mica-log-content",
                            params={"log_file": log_file, "lines": 200},
                            timeout=10
                        )
                        if response.status_code == 200:
                            log_data = response.json()
                            with st.expander("📄 Standard Output", expanded=True):
                                st.code(log_data.get("content", ""), language="log")
                    except Exception as e:
                        st.error(f"Failed to load log: {str(e)}")
        
        with col2:
            if error_log_file:
                st.text_input("Error Log", value=error_log_file, disabled=True)
                if st.button("⚠️ View Error Log", key="view_error_log"):
                    try:
                        response = requests.get(
                            f"{FASTAPI_SERVER_URL}/mica-log-content",
                            params={"log_file": error_log_file, "lines": 200},
                            timeout=10
                        )
                        if response.status_code == 200:
                            log_data = response.json()
                            if log_data.get("content", "").strip():
                                with st.expander("⚠️ Error Output", expanded=True):
                                    st.code(log_data.get("content", ""), language="log")
                            else:
                                st.success("✅ No errors found!")
                    except Exception as e:
                        st.error(f"Failed to load error log: {str(e)}")
        
        st.markdown("---")
        
        # 결과 파일 다운로드 (derivatives 디렉토리 기반)
        st.markdown("#### 📦 Download Results")
        st.markdown("#### ⬇️ Export (ALL)")

        if st.button("📦 Download ALL derivatives as ZIP", key="dl_all_deriv"):
            try:
                r = requests.get(f"{FASTAPI_SERVER_URL}/download-derivatives", timeout=60)
                if r.status_code == 200:
                    zip_bytes = r.content
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="⬇️ Save file",
                        data=zip_bytes,
                        file_name=f"derivatives_all_{ts}.zip",
                        mime="application/zip"
                    )
                else:
                    st.error(f"Download failed: {r.status_code} {r.text}")
            except Exception as e:
                st.error(f"Download error: {str(e)}")

        st.info("💡 Results are saved in `/app/data/derivatives/` directory. Access the files directly on the server or use the file browser below.")
        
    else:
        st.info("""
        ℹ️ No completed jobs available for download.
        
        **💡 Next Steps:**
        - Check the '⏳ Processing' jobs above
        - Run a new pipeline from '🧠 MICA Pipeline' menu
        - Review failed jobs and fix any issues
        """)
    
    # Failed jobs 섹션
    failed_jobs = [j for j in filtered_jobs if j.get("status") == "failed"]
    if failed_jobs:
        st.markdown("---")
        st.markdown("### ❌ Failed Jobs")
        st.warning(f"Found {len(failed_jobs)} failed job(s). Click to view error details:")
        
        for job in failed_jobs:
            with st.expander(f"❌ {job.get('subject_id', '')} - {job.get('processes', '')}"):
                st.markdown(f"""
                **Job ID:** `{job.get('job_id', '')}`  
                **Started:** {datetime.fromisoformat(job.get('started_at')).strftime('%Y-%m-%d %H:%M:%S') if job.get('started_at') else '-'}  
                **Error Message:**
                """)
                if job.get("error_message"):
                    st.code(job.get("error_message", ""), language="log")
                else:
                    st.text("No error message available. Check error log file.")
