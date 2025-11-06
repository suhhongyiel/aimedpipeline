"""
결과 다운로드 페이지 모듈 - MICA Pipeline 통합
"""
import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# FastAPI 서버 주소
FASTAPI_SERVER_URL = os.getenv(
    "FASTAPI_SERVER_URL",
    st.secrets.get("api", {}).get("fastapi_base_url", "http://localhost:8000")
)

def fetch_mica_jobs():
    """MICA Pipeline Job 목록을 가져옵니다."""
    try:
        response = requests.get(f"{FASTAPI_SERVER_URL}/mica-jobs", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "jobs": [], "summary": {"processing": 0, "completed": 0, "failed": 0}}
    except Exception as e:
        st.error(f"❌ Failed to fetch MICA jobs: {str(e)}")
        return {"success": False, "jobs": [], "summary": {"processing": 0, "completed": 0, "failed": 0}}

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
    
    # MICA Pipeline Job 데이터 가져오기
    jobs_response = fetch_mica_jobs()
    
    if not jobs_response.get("success"):
        st.warning("⚠️ Failed to load MICA Pipeline jobs")
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
    
    # 새로고침 버튼
    if st.button("🔄 새로고침", key="refresh_results"):
        st.rerun()
    
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
    
    # DataFrame으로 변환
    df_data = []
    for job in filtered_jobs:
        df_data.append({
            "Status": status_emoji(job.get("status", "")) + " " + job.get("status", "").capitalize(),
            "Subject": job.get("subject_id", ""),
            "Session": job.get("session_id", "-"),
            "Process": job.get("processes", "").split(",")[0] if job.get("processes") else "-",
            "Started": datetime.fromisoformat(job.get("started_at")).strftime("%Y-%m-%d %H:%M") if job.get("started_at") else "-",
            "Duration": format_duration(job.get("duration")),
            "Progress": f"{job.get('progress', 0):.0f}%",
            "Job ID": job.get("job_id", "")
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
    
    styled_df = df.style.applymap(style_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
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
