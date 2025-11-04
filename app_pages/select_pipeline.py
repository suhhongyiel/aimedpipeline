"""
파이프라인 선택 페이지 모듈
"""
import streamlit as st
from utils.common import get_pipeline_categories
import requests
import os
import pandas as pd


def render():
    """파이프라인 선택 페이지 렌더링"""
    st.title("🔧 Select Pipeline")
    st.markdown("---")
    
    st.markdown("""
    ## Available AI Pipelines
    
    다양한 의료 데이터 분석을 위한 파이프라인을 선택하세요.
    """)
    
    # 파이프라인 카테고리
    pipeline_categories = get_pipeline_categories()
    
    for category, pipelines in pipeline_categories.items():
        st.subheader(f"📋 {category}")
        
        for pipeline in pipelines:
            with st.container():
                # 파이프라인 카드 스타일로 표시
                st.markdown(f"""
                <div class="pipeline-card">
                    <h4>{pipeline['name']}</h4>
                    <p><em>{pipeline['description']}</em></p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col2:
                    status_color = {
                        "Available": "🟢",
                        "Beta": "🟡",
                        "New": "🔵"
                    }
                    st.markdown(f"{status_color.get(pipeline['status'], '⚪')} {pipeline['status']}")
                
                with col3:
                    if st.button(f"Select", key=f"select_{pipeline['name']}"):
                        st.session_state.selected_pipeline = pipeline['name']
                        st.success(f"✅ Selected: **{pipeline['name']}**")
                        st.balloons()  # 선택 시 축하 애니메이션
        
        st.markdown("---")
    
    # 명령어 실행 및 파일 관리 섹션
    st.markdown("---")
    st.markdown("### 🛠️ 서버 명령 실행 및 파일 관리")
    
    # FastAPI 서버 URL 설정
    FASTAPI_SERVER_URL = os.getenv(
        "FASTAPI_SERVER_URL",
        st.secrets.get("api", {}).get("fastapi_base_url", "http://localhost:8003")
    )
    
    # 탭으로 구분
    tab1, tab2, tab3 = st.tabs(["🚀 명령 실행", "📁 파일 관리", "📝 파일 생성/삭제"])
    
    with tab1:
        st.markdown("#### 서버에서 명령어 실행")
        st.markdown("명령어는 서버에서 실제로 실행되며, 볼륨에 파일을 생성하거나 삭제할 수 있습니다.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            cmd = st.text_input(
                "명령어 입력", 
                placeholder="예: ls -la, touch test.txt, echo 'Hello' > hello.txt, rm test.txt",
                key="command_input"
            )
        with col2:
            work_dir = st.text_input("작업 디렉토리", value="/app/workspace", key="work_dir_input")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("▶️ 실행", type="primary", use_container_width=True):
                if cmd:
                    try:
                        with st.spinner("명령어 실행 중..."):
                            resp = requests.post(
                                f"{FASTAPI_SERVER_URL}/run-command", 
                                json={"cmd": cmd, "work_dir": work_dir},
                                timeout=310
                            )
                            resp.raise_for_status()
                            result = resp.json()
                            
                            # 결과 표시
                            if result.get("success"):
                                st.success(f"✅ 명령어 실행 성공 (반환 코드: {result.get('returncode', 0)})")
                            else:
                                st.error(f"❌ 명령어 실행 실패 (반환 코드: {result.get('returncode', -1)})")
                            
                            # 메타 정보
                            info_col1, info_col2, info_col3 = st.columns(3)
                            with info_col1:
                                st.metric("작업 디렉토리", result.get("work_dir", "-"))
                            with info_col2:
                                st.metric("실행 시간", result.get("duration", "-"))
                            with info_col3:
                                st.metric("타임스탬프", result.get("timestamp", "-")[:19] if result.get("timestamp") else "-")
                            
                            # 출력 결과
                            if result.get("output"):
                                st.markdown("**📤 표준 출력:**")
                                st.code(result["output"], language="text")
                            
                            # 에러 출력
                            if result.get("error"):
                                st.markdown("**⚠️ 표준 에러:**")
                                st.error(result["error"])
                    except requests.exceptions.ConnectionError:
                        st.error("❌ FastAPI 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
                    except requests.exceptions.Timeout:
                        st.error("❌ 요청 시간 초과 (5분 이상 소요)")
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {str(e)}")
                else:
                    st.warning("⚠️ 명령어를 입력하세요.")
        
        with col2:
            if st.button("🔄 새로고침", use_container_width=True):
                st.rerun()
    
    with tab2:
        st.markdown("#### 파일 및 디렉토리 목록")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            list_path = st.text_input("경로", value="/app/workspace", key="list_path_input")
        with col2:
            if st.button("📂 조회", use_container_width=True):
                try:
                    resp = requests.get(f"{FASTAPI_SERVER_URL}/list-files", params={"path": list_path})
                    resp.raise_for_status()
                    result = resp.json()
                    
                    if result.get("files"):
                        files_data = []
                        for f in result["files"]:
                            files_data.append({
                                "이름": f["name"],
                                "타입": "📁 디렉토리" if f["type"] == "directory" else "📄 파일",
                                "크기": f"{f['size']:,} bytes" if f.get("size") else "-",
                                "수정일": f["modified"][:19] if f.get("modified") else "-",
                                "경로": f["path"]
                            })
                        
                        df = pd.DataFrame(files_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.info(f"총 {result.get('count', 0)}개 항목")
                    else:
                        st.info("빈 디렉토리입니다.")
                except requests.exceptions.ConnectionError:
                    st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
                except Exception as e:
                    st.error(f"❌ 오류: {str(e)}")
    
    with tab3:
        st.markdown("#### 파일 생성 및 삭제")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📝 파일 생성")
            create_file_path = st.text_input("파일 경로", key="create_file_path", placeholder="예: data/test.txt")
            create_file_content = st.text_area("파일 내용", height=150, key="create_file_content")
            
            if st.button("➕ 파일 생성", type="primary", use_container_width=True):
                if create_file_path:
                    try:
                        resp = requests.post(
                            f"{FASTAPI_SERVER_URL}/create-file",
                            json={
                                "file_path": create_file_path,
                                "content": create_file_content,
                                "work_dir": "/app/workspace"
                            }
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        if result.get("success"):
                            st.success(f"✅ {result.get('message')}")
                            st.info(f"파일 크기: {result.get('size', 0)} bytes")
                        else:
                            st.error("파일 생성 실패")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
                    except Exception as e:
                        st.error(f"❌ 오류: {str(e)}")
                else:
                    st.warning("파일 경로를 입력하세요.")
        
        with col2:
            st.markdown("##### 🗑️ 파일/디렉토리 삭제")
            delete_file_path = st.text_input("삭제할 경로", key="delete_file_path", placeholder="예: data/test.txt")
            st.warning("⚠️ 삭제된 파일은 복구할 수 없습니다!")
            
            if st.button("🗑️ 삭제", type="secondary", use_container_width=True):
                if delete_file_path:
                    try:
                        resp = requests.delete(
                            f"{FASTAPI_SERVER_URL}/delete-file",
                            params={"file_path": delete_file_path, "work_dir": "/app/workspace"}
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        if result.get("success"):
                            st.success(f"✅ {result.get('message')}")
                        else:
                            st.error("삭제 실패")
                    except requests.exceptions.ConnectionError:
                        st.error("❌ FastAPI 서버에 연결할 수 없습니다.")
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            st.error("❌ 파일 또는 디렉토리를 찾을 수 없습니다.")
                        elif e.response.status_code == 403:
                            st.error("❌ /app 디렉토리 외부의 파일은 삭제할 수 없습니다.")
                        else:
                            st.error(f"❌ HTTP 오류: {e.response.status_code}")
                    except Exception as e:
                        st.error(f"❌ 오류: {str(e)}")
                else:
                    st.warning("삭제할 경로를 입력하세요.")


    # 선택된 파이프라인 정보 표시
    if 'selected_pipeline' in st.session_state and st.session_state.selected_pipeline:
        st.markdown("### 🎯 Currently Selected Pipeline")
        st.info(f"**{st.session_state.selected_pipeline}**")
        
        if st.button("🚀 Go to Run Pipeline", use_container_width=True):
            st.session_state.selected_menu = 'Run Pipeline'
            st.rerun()
    
    # 파이프라인 비교 섹션
    st.markdown("### 📊 Pipeline Comparison")
    
    comparison_data = {
        "Pipeline": ["MRI 분석"],
        "Processing Time": ["~6.3s"],
        "Accuracy": ["92.8%"],
        "Supported Formats": ["DICOM"]
    }
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
