"""
공통 함수 및 설정 모듈
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

def init_session_state():
    """세션 상태 초기화"""
    if 'selected_menu' not in st.session_state:
        st.session_state.selected_menu = 'Home'
    if 'selected_pipeline' not in st.session_state:
        st.session_state.selected_pipeline = None

def set_page_config():
    """페이지 기본 설정"""
    st.set_page_config(
        page_title="AI Medical Pipeline",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )

def get_pipeline_categories():
    """파이프라인 카테고리 데이터 반환"""
    return {
        "의료 영상 분석": [
            {"name": "MRI 분석", "description": "MRI 영상 분석을 하는 파이프라인입니다.", "status": "Beta"}
        ],
        "사칙 연산 데모": [
            {"name": "사칙연산 데모", "description": "숫자 2개와 연산자를 받아 Airflow로 계산", "status": "Available"}
        ]
    }

def get_sample_recent_data():
    """샘플 최근 활동 데이터 생성"""
    return pd.DataFrame({
        'Date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'Pipeline': [f'Pipeline_{i%3+1}' for i in range(10)],
        'Status': np.random.choice(['Success', 'Processing', 'Failed'], 10),
        'Processing Time': np.random.randint(1, 60, 10)
    })

def get_sample_results_data():
    """샘플 결과 데이터 생성"""
    return pd.DataFrame({
        'Job ID': [f'JOB_{str(i).zfill(4)}' for i in range(1, 11)],
        'Pipeline': np.random.choice(['sMRI 분석', 'fMRI 분석', 'dMRI 분석'], 10), # 여기 변경
        'Date': pd.date_range('2024-01-01', periods=10, freq='D'),
        'Status': np.random.choice(['Completed', 'Processing', 'Failed'], 10, p=[0.7, 0.2, 0.1]),
        'Files': np.random.randint(1, 20, 10),
        'Accuracy': np.random.uniform(0.85, 0.98, 10).round(3)
    })

def show_progress_simulation():
    """파이프라인 실행 프로그레스 시뮬레이션"""
    import time
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(101):
        progress_bar.progress(i)
        if i < 30:
            status_text.text(f'Loading data... {i}%')
        elif i < 70:
            status_text.text(f'Processing... {i}%')
        else:
            status_text.text(f'Generating results... {i}%')
        time.sleep(0.02)
    
    st.success("✅ Pipeline completed successfully!")
    status_text.text("Pipeline execution completed!")

def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.title("🏥 Menu")
        st.markdown("---")
        
        # 메뉴 버튼들
        menu_options = ['Home', 'Select Pipeline', 'Run Pipeline', 'Download Results']
        
        for menu in menu_options:
            if st.button(menu, key=f"menu_{menu}", use_container_width=True):
                st.session_state.selected_menu = menu
        
        st.markdown("---")
        
        # 추가 정보
        st.markdown("### ℹ️ System Info")
        st.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        st.info(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        
        # 프로젝트 정보
        st.markdown("### 📋 Project Info")
        with st.expander("About"):
            st.markdown("""
            **AI Medical Pipeline v1.0**
            
            Advanced medical data analysis platform powered by AI.
            
            - 🔬 Multiple pipeline support
            - 🚀 Fast processing
            - 📊 Detailed analytics
            - 💾 Easy data export
            """)
# utils/common.py (맨 아래에 추가)
import os, uuid

def save_uploaded_files_to_inbox(files, base_dir="./shared/inbox"):
    """업로드 파일들을 공유 인박스에 저장하고 경로를 반환"""
    job_id = uuid.uuid4().hex[:12]
    inbox_dir = os.path.join(base_dir, job_id)
    os.makedirs(inbox_dir, exist_ok=True)
    saved = []
    for f in files:
        dest = os.path.join(inbox_dir, f.name)
        with open(dest, "wb") as fw:
            fw.write(f.read())
        saved.append(dest)
    return job_id, inbox_dir, saved
