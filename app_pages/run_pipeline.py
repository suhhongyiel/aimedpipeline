"""
파이프라인 실행 페이지 모듈
"""
import streamlit as st
import os
from utils.common import show_progress_simulation, save_uploaded_files_to_inbox
from services import orchestrator

from utils.airflow_client import trigger_dag, get_dag_run, get_task_instances # 데모(사칙연산용)

# 담당 : sjhwang @ 

# Airflow 접속 설정 (Streamlit secrets 사용)
def _af_cfg():
    cfg = st.secrets.get("airflow", {})
    return dict(
        base_url=cfg.get("base_url", "http://localhost:8080"),
        username=cfg.get("username"),
        password=cfg.get("password"),
        bearer_token=cfg.get("bearer_token"),
    )
   
# ------------------------- 사칙연산 데모 ------------------------- #
def _render_arith_demo():
    st.subheader("사칙연산 데모 (Airflow)")

    colL, colR = st.columns(2)
    with colL:
        a = st.number_input("a", value=3.0)
    with colR:
        b = st.number_input("b", value=2.0)

    op = st.selectbox("연산자", ["add", "sub", "mul", "div"], index=0)

    if st.button("▶️ Airflow로 실행", use_container_width=True, key="arith_run"):
        resp = trigger_dag(
            dag_id="arith_pipeline",
            conf={"a": a, "b": b, "op": op},
            **_af_cfg()
        )
        st.session_state["arith_run_id"] = resp.get("dag_run_id") or resp.get("run_id")
        st.success(f"Triggered: {st.session_state['arith_run_id']}")

    run_id = st.session_state.get("arith_run_id")
    if run_id:
        st.markdown("---")
        st.markdown("### 🔄 진행상태")
        _ = st.autorefresh(interval=3000, key="arith_poll")

        run = get_dag_run(dag_id="arith_pipeline", dag_run_id=run_id, **_af_cfg())
        tis = get_task_instances(dag_id="arith_pipeline", dag_run_id=run_id, **_af_cfg())
        total = max(len(tis), 1)
        done = sum(t["state"] in ("success", "skipped") for t in tis)

        st.progress(int(100 * done / total))
        st.write(f"State: **{run.get('state','queued')}**  |  {done}/{total} tasks")

        with st.expander("Tasks"):
            st.table([{"task_id": t["task_id"], "state": t["state"]} for t in tis])

        # 결과 리포트 (Airflow가 작성)
        report = f"./shared/artifacts/arith/{run_id}/report.html"
        if os.path.exists(report):
            st.markdown("### 📊 결과 리포트")
            with open(report, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=320, scrolling=True)
        else:
            st.info("보고서 준비 중…")

# ------------------------- MRI 파이프라인 ------------------------- #
def _render_mri():
    st.subheader("MRI 분석 파이프라인 (Airflow)")
 
    
    # 파일 업로드 섹션
    st.markdown("#### 📁 Data Upload")
    
    # 파이프라인에 따라 다른 파일 타입 허용
    pipeline_formats = {
        "X-Ray 분석": ['jpg', 'jpeg', 'png', 'dicom'],
        "CT 스캔 분석": ['dicom', 'nii', 'nrrd'],
        "MRI 분석": ['dicom', 'nii', 'nrrd'],
        "혈액 검사 분석": ['csv', 'xlsx', 'xls'],
        "심전도 분석": ['csv', 'txt', 'edf'],
        "환자 위험도 평가": ['csv', 'xlsx', 'json']
    }
    
    allowed_types = pipeline_formats.get(st.session_state.selected_pipeline, ['jpg', 'png', 'csv'])
    
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
                with st.container():
                    st.markdown("### 🔄 Processing Status")
                    show_progress_simulation()
                    
                    # 가상의 결과 미리보기
                    st.markdown("### 📊 Results Preview")
                    
                    if st.session_state.selected_pipeline == "X-Ray 분석":
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("이상 소견", "2/5", "검출됨")
                        with col2:
                            st.metric("평균 신뢰도", "94.2%", "+2.1%")
                    
                    elif st.session_state.selected_pipeline == "혈액 검사 분석":
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("정상 범위", "85%", "+5%")
                        with col2:
                            st.metric("주의 필요", "12%", "-2%")
                        with col3:
                            st.metric("이상 수치", "3%", "-1%")
                    
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
  # 실행 백엔드 선택
    backend = st.radio("Execution backend", ["Local (Simulated)", "Airflow"], index=1, horizontal=True)

    # === Local (기존 시뮬레이션) ===========================================
    if backend == "Local (Simulated)":
        if st.button("🚀 Run (Local Simulated)", use_container_width=True, key="mri_local"):
            if not uploaded_files:
                st.error("❌ Please upload data files first!")
            else:
                st.markdown("### 🔄 Processing Status")
                show_progress_simulation()        
                st.markdown("### 📊 Results Preview")
        return

    # === Airflow 실행 =====================================================
    st.markdown("#### ⚙️ Airflow Options")

    colA, colB = st.columns(2)
    with colA:
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.8, 0.05)
        batch_size = st.selectbox("Batch Size", options=[1,4,8,16,32], index=2)
    with colB:
        output_format = st.selectbox("Output Format", options=['JSON','CSV','Excel'], index=0)
        enable_visualization = st.checkbox("Enable Visualization", value=True)

    # 실행 버튼 (Airflow)
    if st.button("▶️ Run with Airflow", use_container_width=True):
        if not uploaded_files:
            st.error("❌ Please upload data files first!")
        else:
            # 1) 업로드 파일을 공유 인박스로 저장
            job_id, inbox_dir, saved = save_uploaded_files_to_inbox(uploaded_files)

            # 2) Airflow DAG 트리거
            conf = {
                "inbox": f"/opt/airflow/shared/inbox/{job_id}",  # Airflow 컨테이너에서 보이는 경로
                "params": {
                    "confidence": confidence_threshold,
                    "batch_size": batch_size,
                    "output_format": output_format,
                    "viz": enable_visualization
                }
            }
            resp = orchestrator.start_mri(conf)
            dag_run_id = resp.get("dag_run_id") or resp.get("run_id")
            st.session_state["mri_dag_run_id"] = dag_run_id
            st.session_state["mri_job_id"] = job_id
            st.success(f"✅ Airflow started: {dag_run_id}")

    # 상태 모니터링
    dag_run_id = st.session_state.get("mri_dag_run_id")
    if dag_run_id:
        st.markdown("---")
        st.markdown("### 🔄 Processing Status")
        _ = st.autorefresh(interval=3000, key="mri_poll")

        status = orchestrator.get_status(dag_run_id)
        st.progress(status["progress"])
        st.write(f"State: **{status['state']}**  (Progress: {status['progress']}%)")

        with st.expander("Task details"):
            st.table(status["tasks"])

        # 실패 리포트
        if status["failed_tasks"]:
            st.error(f"❌ Failed tasks: {', '.join(status['failed_tasks'])}")
            st.link_button("Open in Airflow", status["airflow_url"])

        # 성공 시 결과 리포트 표시
        if status["progress"] == 100 and not status["failed_tasks"]:
            report = orchestrator.artifact_path(dag_run_id)
            if os.path.exists(report):
                st.markdown("### 📊 MRI Report")
                with open(report, "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=600, scrolling=True)
            else:
                st.info("Report is being prepared...")
# ------------------------- 메인 렌더러 ------------------------- #
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
    sel = st.session_state.selected_pipeline
    st.markdown(f"### Selected Pipeline: **{sel}**")

    # 파이프라인 분기
    if sel == "사칙연산 데모":
        _render_arith_demo()
        return

    if sel == "MRI 분석":
        _render_mri()
        return

    # 다른 파이프라인은 필요 시 여기에 분기 추가
    st.info("이 파이프라인은 아직 실행 구성이 준비되지 않았습니다.")