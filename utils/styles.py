"""
CSS 스타일 정의 모듈
"""

def get_custom_css():
    """커스텀 CSS 스타일 반환"""
    return """
<style>
    /* 사이드바 스타일링 */
    .css-1d391kg {
        background-color: #f0f2f6;
    }
    
    /* 메인 콘텐츠 영역 */
    .main .block-container {
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* 사이드바 메뉴 버튼 스타일 */
    .menu-button {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px 15px;
        margin: 5px 0;
        width: 100%;
        text-align: left;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .menu-button:hover {
        background-color: #e8f4f8;
        border-color: #1f77b4;
    }
    
    .menu-button.active {
        background-color: #1f77b4;
        color: white;
        border-color: #1f77b4;
    }
    
    /* 카드 스타일 */
    .pipeline-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }
    
    .pipeline-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* 상태 배지 스타일 */
    .status-badge {
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: bold;
        text-align: center;
    }
    
    .status-available {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-beta {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-new {
        background-color: #cce5ff;
        color: #004085;
    }
</style>
"""
