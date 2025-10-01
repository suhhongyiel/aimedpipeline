"""
파이프라인 실행 페이지 모듈
"""
import streamlit as st
import time
import requests
from utils.common import show_progress_simulation
from utils.job_log_mock import get_mock_log

# FastAPI 서버 주소
FASTAPI_SERVER_URL = "http://localhost:8000"

# 담당 : sjhwang @ 

def render():
    """파이프라인 실행 페이지 렌더링"""
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
        "MRI 분석": ['dicom', 'nii', 'nrrd']
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
    
    with col2:
        if st.button("🚀 Run Pipeline", type="primary", use_container_width=True):
            if not uploaded_files:
                st.error("❌ Please upload data files first!")
            else:
                st.markdown("### 🔄 Processing Status")
                progress_bar = st.progress(0, text="Initializing...")
                log_box = st.empty()

                try:
                    # 1. FastAPI 서버에 작업 실행 요청
                    log_box.info("▶️ Sending job request to the server...")
                    res = requests.post(f"{FASTAPI_SERVER_URL}/run-job", json={"job_type": st.session_state.selected_pipeline})
                    res.raise_for_status()  # HTTP 오류 발생 시 예외 발생
                    job_id = res.json()["job_id"]
                    log_box.info(f"✅ Job registered successfully! (Job ID: {job_id})")
                    progress_bar.progress(10, text="Job Queued...")

                    # 2. 작업 상태를 주기적으로 확인
                    while True:
                        res = requests.get(f"{FASTAPI_SERVER_URL}/job-status/{job_id}")
                        res.raise_for_status()
                        job_info = res.json()
                        
                        status = job_info.get("status", "Unknown")
                        log = job_info.get("log", "")
                        
                        log_box.info(log) # 로그 업데이트

                        if status == "Running":
                            progress_bar.progress(50, text="Processing...")
                        elif status == "Completed":
                            progress_bar.progress(100, text="Completed!")
                            log_box.success("🎉 Job completed successfully!")
                            break
                        elif status == "Failed":
                            progress_bar.progress(100, text="Failed!")
                            log_box.error(f"❌ Job failed. Last log: {log}")
                            break
                        
                        time.sleep(2) # 2초마다 상태 확인

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
                
                except requests.exceptions.ConnectionError:
                    st.error("❌ Connection Error: Could not connect to the FastAPI server. Is it running?")
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
