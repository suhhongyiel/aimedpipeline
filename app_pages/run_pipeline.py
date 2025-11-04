"""
파이프라인 실행 페이지 모듈
"""
import streamlit as st
import time
import requests
from utils.common import show_progress_simulation
from utils.job_log_mock import get_mock_log

#####여기 교체함 FASTAPI_SERVER_URL 부분 교체!!!!###########
# 맨 위 import 근처에 추가
import os
import pandas as pd
from utils.styles import get_custom_css
from datetime import datetime


# FastAPI 서버 주소 (도커/로컬 모두 지원)
FASTAPI_SERVER_URL = os.getenv(
    "FASTAPI_SERVER_URL",
    st.secrets.get("api", {}).get("fastapi_base_url", "http://localhost:8000")
)
##############################################################
def _fmt_time_short(s: str, to_local: bool = True) -> str:
    """ISO 문자열 → HH:MM:SS (로컬시간)"""
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if to_local:
            dt = dt.astimezone()
        return dt.strftime("%H:%M:%S")          # 원하면 "%m-%d %H:%M:%S"
    except Exception:
        # 실패해도 대충 시:분:초만
        try:
            return str(s).split("T", 1)[1][:8]
        except Exception:
            return str(s)

def render():
    """파이프라인 실행 페이지 렌더링"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    st.title("🚀 Run Pipeline")
    st.markdown("---")
    
    # 선택된 파이프라인이 있는지 확인
    if 'selected_pipeline' not in st.session_state or not st.session_state.selected_pipeline:
        st.warning("⚠️ Please select a pipeline first from the 'Select Pipeline' menu.")
        if st.button("🔧 Go to Select Pipeline"):
            st.session_state.selected_menu = 'Select Pipeline'
            st.rerun()
        return
    
    st.markdown(f"### Selected Pipeline: **{st.session_state.selected_pipeline}**")
    
    # 파일 업로드 섹션
    st.markdown("#### 📁 Data Upload")
    
    # 파이프라인에 따라 다른 파일 타입 허용
    pipeline_formats = {
        "MRI 분석": ['dicom', 'nii', 'nrrd', 'gz']
    }
    
    allowed_types = pipeline_formats.get(st.session_state.selected_pipeline, ['jpg', 'png', 'csv'])
    # allowed_types = pipeline_formats.get(st.session_state.selected_pipeline, [])
    
    uploaded_files = st.file_uploader(
        f"Upload your {st.session_state.selected_pipeline} data files",
        type=allowed_types,
        accept_multiple_files=True,
        help=f"Supported formats: {', '.join(allowed_types)}"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
        
        # 업로드된 파일 목록 표시
        with st.expander("📋 View uploaded files"):
            for i, file in enumerate(uploaded_files, 1):
                st.markdown(f"{i}. **{file.name}** ({file.size:,} bytes)")
    
    # 파라미터 설정 섹션
    st.markdown("#### ⚙️ Pipeline Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        confidence_threshold = st.slider(
            "Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.05,
            help="Minimum confidence score for predictions"
        )
        
        batch_size = st.selectbox(
            "Batch Size",
            options=[1, 4, 8, 16, 32],
            index=2,
            help="Number of files to process simultaneously"
        )
    
    with col2:
        output_format = st.selectbox(
            "Output Format",
            options=['JSON', 'CSV', 'Excel'],
            index=0,
            help="Format for the analysis results"
        )
        
        enable_visualization = st.checkbox(
            "Enable Visualization", 
            value=True,
            help="Generate visual outputs and charts"
        )
    
    # 고급 설정
    with st.expander("🔧 Advanced Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            preprocessing = st.checkbox("Apply Preprocessing", value=True)
            noise_reduction = st.checkbox("Noise Reduction", value=False)
        
        with col2:
            quality_check = st.checkbox("Quality Check", value=True)
            detailed_report = st.checkbox("Detailed Report", value=False)
    
    # 실행 버튼 섹션
    st.markdown("---")
    st.markdown("#### 🎯 Run Configuration Summary")
    
    # 설정 요약 표시
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **📋 Pipeline Settings:**
        - Pipeline: {st.session_state.selected_pipeline}
        - Files: {len(uploaded_files) if uploaded_files else 0}
        - Confidence: {confidence_threshold}
        - Batch Size: {batch_size}
        """)
    
    with col2:
        st.markdown(f"""
        **🎛️ Output Settings:**
        - Format: {output_format}
        - Visualization: {'Enabled' if enable_visualization else 'Disabled'}
        - Preprocessing: {'Enabled' if preprocessing else 'Disabled'}
        - Quality Check: {'Enabled' if quality_check else 'Disabled'}
        """)
    
    # 실행 버튼
    col1, col2, col3 = st.columns([1, 1, 1])
    

    if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
        if not uploaded_files:
            st.error("❌ Please upload data files first!")
        else:

# ===========================================================================================================================
# ====================================================FastAPI============================================================

            # === 실행 버튼 내부의 처리 루프 부분을 이 블록으로 교체 ===
            st.markdown("### 🔄 Processing Status")
            progress_bar = st.progress(0, text="Initializing...")
            log_box = st.empty()
            table_box = st.empty()
            link_box = st.empty()

            try:
                log_box.info("▶️ Sending job request to the server...")
                res = requests.post(f"{FASTAPI_SERVER_URL}/run-job", json={"job_type": st.session_state.selected_pipeline})
                res.raise_for_status()
                job_id = res.json()["job_id"]
                log_box.info(f"✅ Job registered! (Job ID: {job_id})")
                progress_bar.progress(10, text="Job Queued...")

                while True:
                    res = requests.get(f"{FASTAPI_SERVER_URL}/job-status/{job_id}")
                    res.raise_for_status()
                    job_info = res.json()

                    status = (job_info.get("status") or "").upper()
                    progress = job_info.get("progress", 0)
                    tasks = job_info.get("tasks", [])

                    # 테이블 렌더
                    if tasks:
                        df = pd.DataFrame(tasks)

                        # 보기 좋게 정렬
                        order = [
                            "1_bids_conversion", "2_proc_structural", "3_proc_surf",
                            "4_post_structural", "5_proc_func", "6_finalize_results"
                        ]
                        df["order"] = df["task_id"].apply(lambda x: order.index(x) if x in order else 999)
                        df = df.sort_values("order").drop(columns=["order"])

                        # ⬇️ 시간 컬럼 짧게 변환 + try 숫자화 + 컬럼명 간단화
                        if "start_date" in df.columns:
                            df["start_date"] = df["start_date"].apply(_fmt_time_short)
                        if "end_date" in df.columns:
                            df["end_date"] = df["end_date"].apply(_fmt_time_short)
                        if "try_number" in df.columns:
                            df["try_number"] = df["try_number"].fillna(0).astype(int)

                        df = df.rename(columns={
                            "start_date": "start",
                            "end_date": "end",
                            "try_number": "try"
                        })

                        # 상태 컬러링
                        def _style(val):
                            v = (str(val) or "").lower()
                            if v == "success":
                                return 'background-color: #d4edda; color: #155724'
                            if v in ("running", "queued"):
                                return 'background-color: #fff3cd; color: #856404'
                            if v == "failed":
                                return 'background-color: #f8d7da; color: #721c24'
                            return ''

                        styled = df.style.applymap(_style, subset=["state"])
                        table_box.dataframe(styled, use_container_width=True, height=560)


                    link = job_info.get("airflow_ui")
                    if link:
                        link_box.markdown(f"🔗 **Airflow Grid**: [{link}]({link})")

                    # Crash 감지 및 실패한 task 분석
                    failed_tasks = [t for t in tasks if (t.get("state") or "").lower() == "failed"]
                    
                    # 진행바 및 상태 표시
                    if status in ("RUNNING","QUEUED"):
                        progress_bar.progress(min(max(progress, 15), 95), text="Processing...")
                        
                        # 실행 중에도 실패한 task가 있으면 경고
                        if failed_tasks:
                            log_box.warning(f"⚠️ {len(failed_tasks)} task(s) failed during execution")
                            
                    elif status == "SUCCESS":
                        progress_bar.progress(100, text="Completed!")
                        log_box.success("🎉 Job completed successfully!")
                        
                        # 성공했어도 재시도가 있었는지 확인
                        retry_tasks = [t for t in tasks if t.get("try_number", 1) > 1]
                        if retry_tasks:
                            log_box.info(f"ℹ️ {len(retry_tasks)} task(s) required retry")
                        break
                        
                    elif status == "FAILED":
                        progress_bar.progress(100, text="Failed!")
                        log_box.error(f"❌ Job failed with {len(failed_tasks)} failed task(s)")
                        
                        # 실패한 task 상세 정보 표시
                        if failed_tasks:
                            with st.expander("🔍 Failed Tasks Details", expanded=True):
                                for task in failed_tasks:
                                    st.error(f"""
                                    **Task ID:** {task.get('task_id', 'Unknown')}
                                    - **State:** {task.get('state', 'Unknown')}
                                    - **Start:** {_fmt_time_short(task.get('start_date', ''))}
                                    - **End:** {_fmt_time_short(task.get('end_date', ''))}
                                    - **Tries:** {task.get('try_number', 0)}
                                    """)
                                
                                st.markdown("💡 **Troubleshooting Tips:**")
                                st.markdown("""
                                - Check Airflow logs for detailed error messages
                                - Verify input data format and completeness
                                - Check system resources (memory, disk space)
                                - Review task configuration and parameters
                                """)
                        
                        st.markdown(f"🔗 [View detailed logs in Airflow]({link})")
                        break
                        
                    else:
                        progress_bar.progress(min(progress, 95), text=f"{status.title()}...")

                    time.sleep(2)

    # ===========================================================================================================================
    # ===========================================================================================================================

                # 3. 작업 완료 후 결과 표시
                st.markdown("---")
                st.markdown("### 📊 Results Preview")
                
                # 현재는 MRI 분석만 있으므로, 해당 결과만 표시
                if st.session_state.selected_pipeline == "MRI 분석":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("분석된 슬라이스", "128/150", "85.3%")
                    with col2:
                        st.metric("의심 영역", "3", "발견됨")
                
                # 다운로드 링크 제공
                st.markdown("### 📥 Download Results")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        "📄 Download Report",
                        data=f"Analysis report for {st.session_state.selected_pipeline}",
                        file_name="analysis_report.pdf",
                        mime="application/pdf"
                    )
                
                with col2:
                    if st.button("📊 View Full Results"):
                        st.session_state.selected_menu = 'Download Results'
                        st.rerun()
                
                with col3:
                    st.download_button(
                        "💾 Save Configuration",
                        data=f"Pipeline config: {st.session_state.selected_pipeline}",
                        file_name="config.json",
                        mime="application/json"
                    )

        # ===========================================================================================================================
        # ====================================================FastAPI==============================================================
                
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection Error: Could not connect to the FastAPI server. Is it running?")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")

        # ===========================================================================================================================
        # ===========================================================================================================================