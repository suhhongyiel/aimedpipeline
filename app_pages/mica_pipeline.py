"""
MICA Pipeline 페이지 모듈
파일 업로드, BIDS 검증, 프로세스 선택 및 실행
"""
import streamlit as st
import requests
import os
import pandas as pd
from utils.styles import get_custom_css

# FastAPI 서버 URL 설정
FASTAPI_SERVER_URL = os.getenv(
    "FASTAPI_SERVER_URL",
    st.secrets.get("api", {}).get("fastapi_base_url", "http://localhost:8003")
)

def render():
    """MICA Pipeline 페이지 렌더링"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    st.title("🧠 MICA Pipeline")
    st.markdown("---")
    
    st.markdown("""
    ### MICA Pipeline Workflow
    1. **파일 업로드**: BIDS 포맷 데이터를 업로드합니다
    2. **BIDS 검증**: 업로드된 데이터가 BIDS 표준을 따르는지 확인합니다
    3. **프로세스 선택**: 실행할 프로세스를 선택합니다
    4. **파이프라인 실행**: 선택된 프로세스를 실행하고 결과를 모니터링합니다
    """)
    
    # 탭 생성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 1. 파일 업로드",
        "✅ 2. BIDS 검증",
        "⚙️ 3. 프로세스 선택",
        "🚀 4. 실행 및 모니터링",
        "📊 5. 로그 확인"
    ])
    
    # === 탭 1: 파일 업로드 ===
    with tab1:
        st.markdown("### 📤 데이터 업로드")
        
        # BIDS 폴더 구조 안내
        with st.expander("💡 BIDS 폴더 구조 안내", expanded=False):
            st.markdown("""
            **BIDS (Brain Imaging Data Structure)는 폴더 구조가 중요합니다:**
            
            ```
            bids/
            ├── dataset_description.json
            ├── participants.tsv
            ├── README
            └── sub-001/
                ├── anat/
                │   └── sub-001_T1w.nii.gz
                └── func/
                    └── sub-001_task-rest_bold.nii.gz
            ```
            
            **📦 권장 업로드 방법:**
            1. **ZIP 파일로 압축** (폴더 구조 유지)
            2. **TAR.GZ 파일로 압축** (Linux/Mac)
            3. 압축 파일은 자동으로 압축 해제됩니다
            
            **압축 방법:**
            - Windows: 폴더 선택 → 마우스 우클릭 → "압축"
            - Mac: 폴더 선택 → 마우스 우클릭 → "압축"
            - Linux: `tar -czf bids.tar.gz bids/` 또는 `zip -r bids.zip bids/`
            """)
        
        st.markdown("#### 업로드 설정")
        col1, col2 = st.columns([3, 1])
        with col1:
            destination = st.text_input(
                "업로드 디렉토리",
                value="/app/data/bids",
                key="upload_destination",
                help="BIDS 데이터가 저장될 서버 경로"
            )
        
        with col2:
            extract_archives = st.checkbox(
                "압축 자동 해제",
                value=True,
                help="ZIP, TAR.GZ 파일을 자동으로 압축 해제"
            )
        
        st.markdown("#### 파일 선택")
        uploaded_files = st.file_uploader(
            "파일 선택 (ZIP, TAR.GZ 권장 / 개별 파일도 가능)",
            accept_multiple_files=True,
            type=['zip', 'tar', 'gz', 'tgz', 'nii', 'json', 'tsv', 'txt'],
            help="BIDS 폴더를 압축한 파일(.zip, .tar.gz) 또는 개별 파일"
        )
        
        if uploaded_files:
            st.info(f"📁 {len(uploaded_files)}개 파일 선택됨")
            
            with st.expander("선택된 파일 목록 보기"):
                for i, file in enumerate(uploaded_files, 1):
                    st.markdown(f"{i}. `{file.name}` ({file.size:,} bytes)")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("⬆️ 업로드", type="primary", use_container_width=True):
                    try:
                        with st.spinner("파일 업로드 및 압축 해제 중..."):
                            # multipart/form-data로 전송
                            files_data = [("files", (f.name, f, f.type)) for f in uploaded_files]
                            data = {
                                "destination": destination,
                                "extract_archives": str(extract_archives).lower()
                            }
                            
                            resp = requests.post(
                                f"{FASTAPI_SERVER_URL}/upload-file",
                                files=files_data,
                                data=data,
                                timeout=600  # 압축 해제 시간 고려하여 10분
                            )
                            resp.raise_for_status()
                            result = resp.json()
                            
                            if result.get("success"):
                                st.success(f"✅ {result.get('message')}")
                                st.session_state.bids_directory = destination
                                
                                # 업로드 결과 표시
                                st.markdown("**📊 업로드 결과:**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("업로드한 파일", result.get("count", 0))
                                with col2:
                                    st.metric("총 크기", f"{result.get('total_size', 0):,} bytes")
                                with col3:
                                    extracted_count = result.get("extracted_files_count", 0)
                                    st.metric("압축 해제된 파일", extracted_count if extracted_count else "-")
                                
                                # 압축 해제 정보
                                if result.get("extracted_files_count"):
                                    st.success(f"🎉 압축 해제 완료: {result.get('extracted_files_count')}개 파일")
                                    
                                    if result.get("extracted_files_sample"):
                                        with st.expander("📂 압축 해제된 파일 일부 보기"):
                                            for fname in result["extracted_files_sample"]:
                                                st.text(f"  {fname}")
                                            if result["extracted_files_count"] > 10:
                                                st.info(f"... 외 {result['extracted_files_count'] - 10}개 파일")
                                
                                # 개별 파일 정보
                                with st.expander("📝 업로드된 파일 상세 정보"):
                                    for f in result.get("uploaded_files", []):
                                        if f.get("extracted"):
                                            st.success(f"📦 {f['filename']} → ✅ 압축 해제됨 ({f.get('archive_type', 'unknown')})")
                                        else:
                                            st.info(f"📄 {f['filename']} ({f['size']:,} bytes)")
                                        
                                        if f.get("extraction_error"):
                                            st.error(f"⚠️ 압축 해제 오류: {f['extraction_error']}")
                                
                                st.info(f"💾 저장 경로: {result.get('destination')}")
                            else:
                                st.error("업로드 실패")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
                    except requests.exceptions.Timeout:
                        st.error("❌ 업로드 시간 초과 (10분 이상 소요)")
                    except Exception as e:
                        st.error(f"❌ 오류: {str(e)}")
    
    # === 탭 2: BIDS 검증 ===
    with tab2:
        st.markdown("### ✅ BIDS 포맷 검증")
        st.markdown("업로드된 데이터가 BIDS 표준을 준수하는지 확인합니다.")
        
        validation_dir = st.text_input(
            "검증할 디렉토리",
            value=st.session_state.get("bids_directory", "/app/data/bids"),
            key="validation_dir"
        )
        
        if st.button("🔍 BIDS 검증 실행", type="primary"):
            try:
                with st.spinner("BIDS 포맷 검증 중..."):
                    resp = requests.post(
                        f"{FASTAPI_SERVER_URL}/validate-bids",
                        json={"directory": validation_dir}
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    
                    # 검증 결과 헤더
                    st.markdown("---")
                    st.markdown(f"### {result.get('message', '검증 완료')}")
                    
                    # 검증 결과 표시
                    if result.get("is_valid"):
                        st.balloons()
                        st.success("🎉 이 데이터셋은 유효한 BIDS 포맷입니다!")
                        st.session_state.bids_validated = True
                        st.session_state.bids_directory = validation_dir
                        st.session_state.bids_subject_list = result.get("subject_list", [])
                    else:
                        st.error(f"❌ BIDS 검증 실패: {len(result.get('errors', []))}개 오류 발견")
                        st.session_state.bids_validated = False
                    
                    # Dataset 정보
                    if result.get("dataset_info"):
                        st.markdown("### 📖 Dataset 정보")
                        info_col1, info_col2, info_col3 = st.columns(3)
                        with info_col1:
                            st.metric("Dataset Name", result['dataset_info'].get('name', '-'))
                        with info_col2:
                            st.metric("BIDS Version", result['dataset_info'].get('version', '-'))
                        with info_col3:
                            st.metric("Dataset Type", result['dataset_info'].get('dataset_type', '-'))
                    
                    # 통계 정보
                    st.markdown("### 📊 통계")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("Subject 수", result.get("subject_count", 0))
                    with stat_col2:
                        st.metric("Participant 수", result.get("participants_count", "-"))
                    with stat_col3:
                        st.metric("경고", len(result.get("warnings", [])))
                    
                    # Subject 목록
                    if result.get("subject_list"):
                        with st.expander("📂 Subject 목록", expanded=False):
                            for sub in result["subject_list"]:
                                st.text(f"  • {sub}")
                            if result["subject_count"] > 10:
                                st.info(f"... 외 {result['subject_count'] - 10}개")
                    
                    # 상세 검증 결과
                    if result.get("details"):
                        st.markdown("### ✅ 검증 상세")
                        for detail in result["details"]:
                            if detail.startswith("✓"):
                                st.success(detail)
                            elif detail.startswith("✗"):
                                st.error(detail)
                            else:
                                st.info(detail)
                    
                    # 에러 표시
                    if result.get("errors"):
                        st.markdown("### ❌ 오류")
                        for error in result["errors"]:
                            st.error(error)
                    
                    # 경고 표시
                    if result.get("warnings"):
                        st.markdown("### ⚠️ 경고")
                        for warning in result["warnings"]:
                            st.warning(warning)
                            
            except requests.exceptions.ConnectionError:
                st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
            except Exception as e:
                st.error(f"❌ 오류: {str(e)}")
    
    # === 탭 3: 프로세스 선택 ===
    with tab3:
        st.markdown("### ⚙️ MICA Pipeline 프로세스 선택")
        
        if not st.session_state.get("bids_validated"):
            st.warning("⚠️ 먼저 BIDS 검증을 완료해주세요 (탭 2)")
        
        st.markdown("실행할 프로세스를 선택하세요:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Structural Processing")
            proc_struct = st.checkbox("proc_structural", value=True, help="T1w 구조 영상 처리")
            proc_surf = st.checkbox("proc_surf", value=True, help="Surface 재구성")
            post_structural = st.checkbox("post_structural", value=False, help="구조 영상 후처리")
            
        with col2:
            st.markdown("#### Functional Processing")
            proc_func = st.checkbox("proc_func", value=False, help="기능적 MRI 처리")
            proc_dwi = st.checkbox("proc_dwi", value=False, help="확산 가중 영상 처리")
            
        st.markdown("#### Subject 선택")
        
        # BIDS 검증 결과에서 subject 목록 가져오기
        available_subjects = []
        if st.session_state.get("bids_validated") and st.session_state.get("bids_subject_list"):
            available_subjects = st.session_state.get("bids_subject_list", [])
        
        # 전체 실행 옵션
        run_all_subjects = st.checkbox(
            "🔄 전체 Subject 실행",
            value=False,
            help="모든 Subject를 순차적으로 실행합니다"
        )
        
        if run_all_subjects:
            st.info(f"📋 전체 Subject 실행: {len(available_subjects)}개 Subject 처리 예정")
            if available_subjects:
                with st.expander("실행될 Subject 목록"):
                    for sub in available_subjects:
                        st.text(f"  • {sub}")
            subject_selection = "all"
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                if available_subjects:
                    # Subject 선택 (드롭다운)
                    subject_selection = st.selectbox(
                        "Subject ID 선택",
                        options=[""] + available_subjects,
                        help="처리할 Subject를 선택하세요"
                    )
                else:
                    # 직접 입력
                    subject_selection = st.text_input(
                        "Subject ID",
                        value="",
                        placeholder="예: sub-ADNI002S1155",
                        help="처리할 Subject ID (전체 이름)"
                    )
            
            with col2:
                session_id = st.text_input(
                    "Session ID (선택)",
                    value="",
                    placeholder="예: ses-01",
                    help="특정 세션만 처리 (선택사항)"
                )
        
        # 선택된 프로세스 저장
        selected_processes = []
        if proc_struct:
            selected_processes.append("proc_structural")
        if proc_surf:
            selected_processes.append("proc_surf")
        if post_structural:
            selected_processes.append("post_structural")
        if proc_func:
            selected_processes.append("proc_func")
        if proc_dwi:
            selected_processes.append("proc_dwi")
        
        # === 추가 설정 ===
        st.markdown("---")
        st.markdown("#### 고급 설정")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fs_licence = st.text_input(
                "FreeSurfer 라이센스 경로",
                value="/app/data/license.txt",
                help="FreeSurfer 라이센스 파일의 절대 경로"
            )
        
        with col2:
            threads = st.number_input(
                "스레드 수",
                min_value=1,
                max_value=32,
                value=4,
                help="사용할 CPU 스레드 수"
            )
        
        with col3:
            use_freesurfer = st.checkbox(
                "FreeSurfer 사용",
                value=True,
                help="FreeSurfer를 사용하여 처리"
            )
        
        # === 실행 방식 선택 ===
        st.markdown("---")
        st.markdown("#### ⚙️ 실행 방식")
        
        use_airflow = st.checkbox(
            "🔄 Airflow를 통해 실행 (권장: 다중 사용자 환경)",
            value=False,
            help="""
            ✅ Airflow 사용 시 장점:
            • 작업 큐 관리 (순서대로 실행)
            • 리소스 제한 및 모니터링
            • 사용자별 작업 추적
            • 자동 재시도 및 알림
            • 관리자가 Airflow UI에서 중앙 관리
            
            ⚠️ 직접 실행 시:
            • 즉시 실행 (큐 없음)
            • 리소스 제한 없음
            • Download Results에서만 확인 가능
            """
        )
        
        if use_airflow:
            st.info("💡 Airflow UI에서 실행 상태를 확인하세요: http://localhost:8080 (admin/admin)")
            
            # 사용자 이름 입력
            user_name = st.text_input(
                "사용자 이름",
                value=os.getenv("USER", "anonymous"),
                help="작업 추적을 위한 사용자 이름"
            )
            st.session_state.mica_user = user_name
        else:
            st.session_state.mica_user = "direct_execution"
        
        # 세션 저장
        st.session_state.mica_processes = selected_processes
        st.session_state.mica_subject = subject_selection
        st.session_state.mica_session = session_id if not run_all_subjects else ""
        st.session_state.mica_use_airflow = use_airflow
        st.session_state.mica_run_all = run_all_subjects
        st.session_state.mica_fs_licence = fs_licence
        st.session_state.mica_threads = threads
        st.session_state.mica_freesurfer = use_freesurfer
        
        if selected_processes:
            st.info(f"✅ 선택된 프로세스: {', '.join(selected_processes)}")
        else:
            st.warning("⚠️ 프로세스를 선택해주세요")
    
    # === 탭 4: 실행 및 모니터링 ===
    with tab4:
        st.markdown("### 🚀 MICA Pipeline 실행")
        
        if not st.session_state.get("bids_validated"):
            st.warning("⚠️ 먼저 BIDS 검증을 완료해주세요 (탭 2)")
            return
        
        if not st.session_state.get("mica_processes"):
            st.warning("⚠️ 먼저 프로세스를 선택해주세요 (탭 3)")
            return
        
        if not st.session_state.get("mica_subject") or st.session_state.get("mica_subject") == "":
            st.warning("⚠️ Subject를 선택해주세요 (탭 3)")
            return
        
        # 실행 설정 요약
        st.markdown("#### 📋 실행 설정 요약")
        col1, col2 = st.columns(2)
        
        with col1:
            run_mode = "🔄 전체 Subject" if st.session_state.get('mica_run_all') else f"🎯 단일 Subject"
            subject_info = "전체" if st.session_state.get('mica_run_all') else st.session_state.get('mica_subject', '-')
            st.markdown(f"""
            **데이터 정보:**
            - BIDS 디렉토리: `{st.session_state.get('bids_directory', '-')}`
            - 실행 모드: {run_mode}
            - Subject: `{subject_info}`
            - Session: `{st.session_state.get('mica_session', '-') or '전체'}`
            """)
        
        with col2:
            st.markdown(f"""
            **선택된 프로세스:**
            {chr(10).join(['- ' + p for p in st.session_state.get('mica_processes', [])])}
            """)
        
        # 실행 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("▶️ 실행", type="primary", use_container_width=True):
                try:
                    with st.spinner("MICA Pipeline 실행 중..."):
                        payload = {
                            "bids_dir": st.session_state.get("bids_directory"),
                            "output_dir": "/app/data/derivatives",
                            "subject_id": st.session_state.get("mica_subject"),
                            "processes": st.session_state.get("mica_processes"),
                            "session_id": st.session_state.get("mica_session", ""),
                            "fs_licence": st.session_state.get("mica_fs_licence", "/app/data/license.txt"),
                            "threads": st.session_state.get("mica_threads", 4),
                            "freesurfer": st.session_state.get("mica_freesurfer", True),
                            "use_airflow": st.session_state.get("mica_use_airflow", False),
                            "user": st.session_state.get("mica_user", "anonymous"),
                            "timeout": 3600
                        }
                        
                        resp = requests.post(
                            f"{FASTAPI_SERVER_URL}/run-mica-pipeline",
                            json=payload,
                            timeout=3700
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        # 결과 표시
                        if result.get("mode") == "all_subjects":
                            # 전체 Subject 실행 결과
                            st.markdown("---")
                            st.markdown("### 📊 전체 Subject 실행 결과")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("전체 Subject", result.get("total_subjects", 0))
                            with col2:
                                st.metric("성공", result.get("successful", 0), 
                                         delta=None if result.get("successful", 0) == result.get("total_subjects", 0) else "완료")
                            with col3:
                                st.metric("실패", result.get("failed", 0),
                                         delta=None if result.get("failed", 0) == 0 else "오류")
                            
                            if result.get("success"):
                                st.success(f"✅ 전체 {result.get('total_subjects')}개 Subject 실행 완료!")
                            else:
                                st.error(f"⚠️ {result.get('failed')}개 Subject 실행 실패")
                            
                            # Subject별 상세 결과
                            with st.expander("📋 Subject별 실행 결과 보기", expanded=not result.get("success")):
                                for idx, sub_result in enumerate(result.get("results", []), 1):
                                    if sub_result.get("success"):
                                        st.success(f"{idx}. ✅ {sub_result.get('subject')} - 성공")
                                    else:
                                        st.error(f"{idx}. ❌ {sub_result.get('subject')} - 실패 (코드: {sub_result.get('returncode', -1)})")
                                        if sub_result.get("error_preview"):
                                            st.text(f"   오류: {sub_result['error_preview']}")
                        
                        else:
                            # 단일 Subject 실행 결과
                            if result.get("success"):
                                st.success(result.get("message", "✅ MICA Pipeline이 성공적으로 완료되었습니다!"))
                            else:
                                st.error(f"❌ MICA Pipeline 실행 실패 (코드: {result.get('returncode', -1)})")
                            
                            # Airflow 모드일 경우 링크 표시
                            if result.get("mode") == "airflow":
                                st.info(f"""
                                **🔄 Airflow로 실행됨**
                                
                                - **DAG Run ID:** `{result.get('dag_run_id', '-')}`
                                - **User:** `{result.get('user', '-')}`
                                - **Airflow UI:** [실행 상태 확인하기]({result.get('airflow_url', 'http://localhost:8080')})
                                
                                💡 Airflow UI에서 실시간 로그와 진행 상황을 확인할 수 있습니다.
                                """)
                            
                            # 명령어 표시 (직접 실행 모드일 때만)
                            if result.get("command"):
                                with st.expander("실행된 명령어 보기"):
                                    st.code(result.get("command", ""), language="bash")
                            
                            # 출력 표시
                            if result.get("output"):
                                with st.expander("📤 표준 출력"):
                                    st.code(result["output"], language="text")
                            
                            # 에러 표시
                            if result.get("error"):
                                with st.expander("⚠️ 표준 에러"):
                                    st.code(result["error"], language="text")
                                
                except requests.exceptions.Timeout:
                    st.error("❌ 요청 시간 초과 (1시간 이상 소요)")
                except requests.exceptions.ConnectionError:
                    st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ 오류: {str(e)}")
        
        with col2:
            if st.button("🔄 새로고침", key="refresh_status", use_container_width=True):
                st.rerun()
        
        # Airflow 모니터링 링크
        st.markdown("---")
        st.markdown("### 📊 모니터링")
        st.markdown("""
        **💡 로그 확인 방법:**
        - **탭 5 (로그 확인)**에서 실행 로그를 실시간으로 확인할 수 있습니다
        - Airflow는 MICA Pipeline에서 사용되지 않습니다 (직접 Docker 실행)
        """)
    
    # === 탭 5: 로그 확인 ===
    with tab5:
        st.markdown("### 📊 MICA Pipeline 로그")
        
        # 실행 중인 컨테이너 확인
        st.markdown("#### 🐳 실행 중인 컨테이너")
        try:
            container_resp = requests.get(
                f"{FASTAPI_SERVER_URL}/mica-containers",
                timeout=10
            )
            container_resp.raise_for_status()
            container_result = container_resp.json()
            
            if container_result.get("containers"):
                st.warning(f"⚠️ {container_result.get('count', 0)}개의 컨테이너가 실행 중입니다")
                
                for container in container_result.get("containers", []):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.text(f"🔵 {container.get('name')}")
                    with col2:
                        st.text(f"⏱️ {container.get('running_for')}")
                    with col3:
                        if st.button("🛑 중지", key=f"stop_{container.get('name')}", use_container_width=True):
                            try:
                                stop_resp = requests.post(
                                    f"{FASTAPI_SERVER_URL}/mica-container-stop",
                                    params={"container_name": container.get("name")},
                                    timeout=30
                                )
                                stop_resp.raise_for_status()
                                stop_result = stop_resp.json()
                                
                                if stop_result.get("success"):
                                    st.success(f"✅ {container.get('name')} 종료됨")
                                    st.rerun()
                                else:
                                    st.error(f"❌ 종료 실패: {stop_result.get('error')}")
                            except Exception as e:
                                st.error(f"❌ 오류: {str(e)}")
            else:
                st.info("✅ 실행 중인 컨테이너가 없습니다")
        except Exception as e:
            st.error(f"❌ 컨테이너 정보 조회 실패: {str(e)}")
        
        st.markdown("---")
        st.markdown("#### 📝 실행 로그")
        
        # 새로고침 버튼
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔄 새로고침", key="refresh_logs", use_container_width=True):
                st.rerun()
        
        try:
            # 로그 목록 가져오기
            resp = requests.get(
                f"{FASTAPI_SERVER_URL}/mica-logs",
                params={"output_dir": "/app/data/derivatives"},
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()
            
            if not result.get("logs"):
                st.info("📝 아직 생성된 로그가 없습니다. 먼저 파이프라인을 실행해주세요.")
            else:
                st.success(f"✅ {result.get('count', 0)}개의 로그 파일 발견")
                
                # 로그 목록 표시
                for log in result.get("logs", []):
                    with st.expander(
                        f"{'❌' if log.get('has_error') else '✅'} {log.get('subject')} - {log.get('process')}",
                        expanded=False
                    ):
                        # 로그 정보
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("프로세스", log.get("process"))
                        with col2:
                            st.metric("로그 크기", f"{log.get('size', 0):,} bytes")
                        with col3:
                            from datetime import datetime
                            modified_time = datetime.fromtimestamp(log.get("modified", 0))
                            st.metric("수정 시간", modified_time.strftime("%Y-%m-%d %H:%M:%S"))
                        
                        # 표준 출력 로그
                        st.markdown("#### 📤 표준 출력 (최근 100줄)")
                        try:
                            log_resp = requests.get(
                                f"{FASTAPI_SERVER_URL}/mica-log-content",
                                params={"log_file": log.get("log_file"), "lines": 100},
                                timeout=10
                            )
                            log_resp.raise_for_status()
                            log_content = log_resp.json()
                            
                            if log_content.get("content"):
                                st.code(log_content.get("content"), language="text")
                                st.caption(f"전체 {log_content.get('total_lines', 0)}줄 중 {log_content.get('returned_lines', 0)}줄 표시")
                            else:
                                st.info("로그가 비어있습니다.")
                        except Exception as e:
                            st.error(f"로그 읽기 실패: {str(e)}")
                        
                        # 에러 로그
                        if log.get("has_error"):
                            st.markdown("#### ⚠️ 에러 로그 (최근 100줄)")
                            try:
                                error_resp = requests.get(
                                    f"{FASTAPI_SERVER_URL}/mica-log-content",
                                    params={"log_file": log.get("error_file"), "lines": 100},
                                    timeout=10
                                )
                                error_resp.raise_for_status()
                                error_content = error_resp.json()
                                
                                if error_content.get("content"):
                                    st.code(error_content.get("content"), language="text")
                                    st.caption(f"전체 {error_content.get('total_lines', 0)}줄 중 {error_content.get('returned_lines', 0)}줄 표시")
                                else:
                                    st.info("에러 로그가 비어있습니다.")
                            except Exception as e:
                                st.error(f"에러 로그 읽기 실패: {str(e)}")
        
        except requests.exceptions.ConnectionError:
            st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
        except requests.exceptions.Timeout:
            st.error("❌ 요청 시간 초과")
        except Exception as e:
            st.error(f"❌ 오류: {str(e)}")

