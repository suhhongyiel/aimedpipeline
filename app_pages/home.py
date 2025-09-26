"""
홈 페이지 모듈
"""
import streamlit as st
import pandas as pd
from utils.common import get_sample_recent_data

def render():
    """홈 페이지 렌더링"""
    st.title("🏥 AI Medical Pipeline Dashboard")
    st.markdown("---")
    
    # 환영 메시지
    st.markdown("""
    ## Welcome to AI Medical Pipeline!
    
    이 플랫폼은 의료 데이터 분석을 위한 AI 파이프라인을 제공합니다.
    왼쪽 사이드바에서 원하는 기능을 선택하여 시작해보세요.
    """)
    
    # 대시보드 개요
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="📊 Available Pipelines",
            value="12",
            delta="3 new"
        )
    
    with col2:
        st.metric(
            label="⚡ Processing Speed",
            value="2.4s",
            delta="-0.3s"
        )
    
    with col3:
        st.metric(
            label="✅ Success Rate",
            value="98.5%",
            delta="1.2%"
        )
    
    # 최근 활동
    st.markdown("### 📈 Recent Activity")
    
    # 샘플 데이터
    recent_data = get_sample_recent_data()
    st.dataframe(recent_data, use_container_width=True)
    
    # 추가 정보 섹션
    st.markdown("### 🔍 Quick Stats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🩺 Top Pipelines
        1. X-Ray 분석 (45%)
        2. 혈액 검사 분석 (28%)
        3. CT 스캔 분석 (18%)
        4. 심전도 분석 (9%)
        """)
    
    with col2:
        st.markdown("""
        #### ⏱️ Average Processing Times
        - X-Ray 분석: ~2.1초
        - CT 스캔 분석: ~4.7초
        - MRI 분석: ~6.3초
        - 혈액 검사 분석: ~1.8초
        """)
