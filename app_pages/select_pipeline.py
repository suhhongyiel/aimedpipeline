"""
파이프라인 선택 페이지 모듈
"""
import streamlit as st
from utils.common import get_pipeline_categories
import requests
import os


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
    
    # 명령어 실행
    st.markdown("### 🚀 명령어 실행 (demo)")
    cmd = st.text_input("명령어 입력 (ex. ls, cd ~, etc)")
    if st.button("실행"):
        # FastAPI 호출해서 명령 실행 결과 받아오기
        resp = requests.post("http://localhost:8003/run-command", json={"cmd": cmd})
        result = resp.json()
        st.code(result["output"]) # 결과 출력
        if result.get("error"):
            st.error(result["error"])


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
        "Pipeline": [ "MRI 분석"],
        "Processing Time": [ "~6.3s"],
        "Accuracy": [ "92.8%"],
        "Supported Formats": [ "DICOM"]
    }
    
    import pandas as pd
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
