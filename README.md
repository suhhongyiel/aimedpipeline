# AI Medical Pipeline 🏥

Streamlit을 활용한 의료 데이터 분석 AI 파이프라인 플랫폼

## 🚀 Features

- **슬라이딩 사이드바**: 직관적인 네비게이션 메뉴
- **Home**: 대시보드 개요 및 최근 활동 현황
- **Select Pipeline**: 다양한 의료 데이터 분석 파이프라인 선택
- **Run Pipeline**: 파이프라인 실행 및 파라미터 설정
- **Download Results**: 분석 결과 다운로드 및 이력 관리

## 📦 Installation

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 앱 실행:
```bash
streamlit run app.py
```

## 🎯 Usage

1. 웹 브라우저에서 앱이 열리면 왼쪽 사이드바에서 원하는 메뉴를 클릭
2. **Select Pipeline**에서 분석하고 싶은 파이프라인 선택
3. **Run Pipeline**에서 데이터 업로드 및 파라미터 설정 후 실행
4. **Download Results**에서 분석 결과 다운로드

## 🔧 Available Pipelines

### 의료 영상 분석
- X-Ray 분석 (흉부 X-Ray 이상 탐지)
- CT 스캔 분석 (뇌 CT 스캔 병변 검출)  
- MRI 분석 (MRI 영상 종양 분류)

### 임상 데이터 분석
- 혈액 검사 분석 (혈액 검사 결과 이상치 탐지)
- 심전도 분석 (ECG 신호 부정맥 검출)
- 환자 위험도 평가 (다중 지표 기반 위험도 산출)

## 📁 Project Structure

```
aimedpipeline-1/
├── app.py                 # 메인 애플리케이션 (라우팅)
├── requirements.txt       # 의존성 패키지
├── README.md             # 프로젝트 문서
├── pages/                # 각 페이지 모듈
│   ├── __init__.py
│   ├── home.py           # 홈 페이지
│   ├── select_pipeline.py # 파이프라인 선택 페이지
│   ├── run_pipeline.py   # 파이프라인 실행 페이지
│   └── download_results.py # 결과 다운로드 페이지
├── utils/                # 공통 유틸리티
│   ├── __init__.py
│   ├── common.py         # 공통 함수들
│   └── styles.py         # CSS 스타일 정의
└── data/                 # 데이터 모듈 (향후 확장)
    └── __init__.py
```

## 🏗️ Architecture

### 모듈화된 구조
- **`app.py`**: 메인 라우팅 및 전역 설정
- **`pages/`**: 각 페이지별 독립 모듈
- **`utils/`**: 공통 기능 및 스타일
- **`data/`**: 데이터 처리 모듈 (향후 확장)

### 장점
- 📦 **모듈화**: 각 페이지가 독립적으로 관리됨
- 🔧 **유지보수성**: 코드 수정 시 영향 범위 최소화
- 🚀 **확장성**: 새로운 페이지 추가가 용이
- 🎨 **재사용성**: 공통 함수 및 스타일 재활용

## 🛠 Tech Stack

- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Architecture**: Modular Design Pattern
- **Visualization**: Built-in Streamlit components

## 📋 Requirements

- Python 3.8+
- Streamlit 1.28.0+
- Pandas 2.0.0+
- NumPy 1.24.0+

## 🔧 Development

### 새로운 페이지 추가하기

1. `pages/` 폴더에 새로운 페이지 파일 생성
```python
# pages/new_page.py
def render():
    """새 페이지 렌더링"""
    st.title("새로운 페이지")
    # 페이지 내용 구현
```

2. `app.py`에 라우팅 추가
```python
from pages import new_page

# 메뉴에 추가 후 라우팅 로직 구현
elif current_menu == 'New Page':
    new_page.render()
```

3. 사이드바 메뉴에 추가
`utils/common.py`의 `render_sidebar()` 함수에서 `menu_options` 리스트에 메뉴 추가