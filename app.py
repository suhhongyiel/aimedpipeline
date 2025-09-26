"""
AI Medical Pipeline - 메인 애플리케이션
페이지 라우팅 및 전역 설정을 담당하는 메인 모듈
"""
import streamlit as st

# 모듈 임포트
from utils.common import set_page_config, init_session_state, render_sidebar
from utils.styles import get_custom_css
from app_pages import home, select_pipeline, run_pipeline, download_results

def main():
    """메인 애플리케이션 함수"""
    # 페이지 기본 설정
    set_page_config()
    
    # 커스텀 CSS 적용
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    # 세션 상태 초기화
    init_session_state()
    
    # 사이드바 렌더링
    render_sidebar()
    
    # 메인 콘텐츠 영역 - 선택된 메뉴에 따라 페이지 라우팅
    current_menu = st.session_state.selected_menu
    
    if current_menu == 'Home':
        home.render()
    elif current_menu == 'Select Pipeline':
        select_pipeline.render()
    elif current_menu == 'Run Pipeline':
        run_pipeline.render()
    elif current_menu == 'Download Results':
        download_results.render()
    else:
        # 기본값: Home 페이지
        st.session_state.selected_menu = 'Home'
        home.render()

if __name__ == "__main__":
    main()