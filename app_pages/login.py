"""
로그인 페이지 모듈
"""
import streamlit as st
import time
from utils.styles import get_custom_css

def render():
    """로그인 페이지 렌더링"""
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # 이미 로그인된 경우 메인 페이지로 리다이렉트
    if st.session_state.get("authenticated", False):
        st.session_state.selected_menu = 'Home'
        st.rerun()
    
    # 중앙 정렬을 위한 컨테이너
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 로그인")
        st.markdown("---")
        
        # 로그인 폼
        with st.form("login_form"):
            username = st.text_input("사용자명", placeholder="아이디를 입력하세요", key="login_username")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", key="login_password")
            
            submit_button = st.form_submit_button("로그인", type="primary", use_container_width=True)
            
            if submit_button:
                # 간단한 인증 (실제로는 DB나 외부 인증 시스템 사용 권장)
                if username == "hysuh" and password == "hysuh":
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_id = username
                    st.success("✅ 로그인 성공!")
                    st.balloons()
                    time.sleep(1)
                    st.session_state.selected_menu = 'Home'
                    st.rerun()
                else:
                    st.error("❌ 사용자명 또는 비밀번호가 올바르지 않습니다.")
        
        st.markdown("---")
        st.info("💡 기본 계정: **hysuh** / **hysuh**")

