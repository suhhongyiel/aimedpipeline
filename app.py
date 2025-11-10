"""
AI Medical Pipeline - 메인 애플리케이션
페이지 라우팅 및 전역 설정을 담당하는 메인 모듈
"""
import streamlit as st
import time

# 모듈 임포트
from utils.common import set_page_config, init_session_state, render_sidebar
from utils.styles import get_custom_css
from app_pages import home, download_results, mica_pipeline, login

def main():
    """메인 애플리케이션 함수"""
    # 페이지 기본 설정
    set_page_config()
    
    # 커스텀 CSS 적용
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # 세션 상태 초기화
    init_session_state()
    
    # 인증 확인 - 로그인되지 않은 경우 로그인 페이지로 리다이렉트
    if not st.session_state.get("authenticated", False):
        login.render()
        return
    
    # 사이드바 렌더링 (로그인된 경우만)
    render_sidebar()
    
    # 메인 콘텐츠 영역 - 선택된 메뉴에 따라 페이지 라우팅
    current_menu = st.session_state.selected_menu
    
    if current_menu == 'Home':
        home.render()
    elif current_menu == 'MICA Pipeline':
        mica_pipeline.render()
    elif current_menu == 'Download Results':
        download_results.render()
    else:
        # 기본값: Home 페이지
        st.session_state.selected_menu = 'Home'
        home.render()

if __name__ == "__main__":
    main()