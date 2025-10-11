# AI Medical Pipeline 🏥

Streamlit, FastAPI, Airflow를 활용한 의료 데이터 분석 AI 파이프라인 플랫폼

## 🚀 Features

- **슬라이딩 사이드바**: 직관적인 네비게이션 메뉴
- **Home**: 대시보드 개요 및 최근 활동 현황
- **Select Pipeline**: 다양한 의료 데이터 분석 파이프라인 선택
- **Run Pipeline**: 파이프라인 실행 및 파라미터 설정
- **Download Results**: 분석 결과 다운로드 및 이력 관리

## 🐳 Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose

### Installation & Run

```bash
# 1. 저장소 클론
git clone https://github.com/suhhongyiel/aimedpipeline.git
cd aimedpipeline

# 2. Docker Compose로 모든 서비스 시작
docker compose up -d

# 3. 서비스 확인
docker compose ps
```

### 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Streamlit** | http://localhost:8502 | 메인 웹 인터페이스 |
| **FastAPI** | http://localhost:8003 | Backend API 서버 |
| **Airflow** | http://localhost:8080 | 워크플로우 관리 (admin/admin) |
| **PostgreSQL** | localhost:5433 | 데이터베이스 (airflow/airflow) |

## 📁 Project Structure

```
aimedpipeline/
├── app.py                      # Streamlit 메인 애플리케이션
├── app_pages/                  # Streamlit 페이지 모듈
│   ├── home.py                 # 홈 페이지
│   ├── select_pipeline.py      # 파이프라인 선택
│   ├── run_pipeline.py         # 파이프라인 실행
│   └── download_results.py     # 결과 다운로드
├── backend/                    # FastAPI 백엔드
│   ├── fastapi_server.py       # API 서버
│   ├── database.py             # DB 설정
│   ├── models.py               # DB 모델
│   └── requirements.txt        # Backend 의존성
├── airflow/                    # Airflow 설정
│   └── dags/                   # DAG 파일
│       └── mri_pipeline_dag.py # MRI 분석 워크플로우
├── utils/                      # 공통 유틸리티
│   ├── common.py               # 공통 함수
│   └── styles.py               # CSS 스타일
├── docker-compose.yml          # Docker Compose 설정
├── Dockerfile                  # Streamlit 이미지
└── requirements.txt            # Python 의존성
```

## 🔧 Available Pipelines

### 의료 영상 분석
- **MRI 분석**: MRI 영상 종양 분류
- **CT 스캔 분석**: 뇌 CT 스캔 병변 검출
- **X-Ray 분석**: 흉부 X-Ray 이상 탐지

### 임상 데이터 분석
- **혈액 검사 분석**: 혈액 검사 결과 이상치 탐지
- **심전도 분석**: ECG 신호 부정맥 검출
- **환자 위험도 평가**: 다중 지표 기반 위험도 산출

## 🏗️ Architecture

### 마이크로서비스 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│   Airflow   │
│  (Frontend) │     │  (Backend)  │     │ (Workflow)  │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   SQLite    │     │ PostgreSQL  │
                    │  (Backend)  │     │  (Airflow)  │
                    └─────────────┘     └─────────────┘
```

### 구성 요소

- **Streamlit**: 사용자 인터페이스 및 시각화
- **FastAPI**: REST API 서버, 작업 관리
- **Airflow**: 워크플로우 스케줄링 및 실행
- **PostgreSQL**: Airflow 메타데이터 저장
- **SQLite**: Backend 작업 로그 저장

## 🛠 Tech Stack

- **Frontend**: Streamlit 1.50.0
- **Backend**: FastAPI 0.111.0, Uvicorn 0.30.0
- **Workflow**: Apache Airflow 2.9.1
- **Database**: PostgreSQL 13, SQLite
- **Data Processing**: Pandas, NumPy
- **Containerization**: Docker, Docker Compose

## 📋 Requirements

### Python 패키지
- Python 3.9+ (Streamlit)
- Python 3.11+ (Backend)
- Streamlit >= 1.28.0
- FastAPI == 0.111.0
- Pandas >= 2.0.0
- NumPy >= 1.24.0

### 시스템 요구사항
- Docker Engine 20.10+
- Docker Compose 2.0+
- 최소 4GB RAM

## 🔧 Development

### 로컬 개발 (Docker 없이)

```bash
# Streamlit 실행
pip install -r requirements.txt
streamlit run app.py --server.port 8502

# FastAPI 실행
cd backend
pip install -r requirements.txt
uvicorn fastapi_server:app --reload --port 8003
```

### Docker 명령어

```bash
# 전체 서비스 시작
docker compose up -d

# 특정 서비스만 재시작
docker compose restart streamlit

# 로그 확인
docker compose logs -f streamlit

# 전체 서비스 중지 및 제거
docker compose down

# 볼륨까지 제거
docker compose down -v
```

### 새로운 페이지 추가

1. `app_pages/` 폴더에 새 파일 생성
```python
# app_pages/new_page.py
import streamlit as st

def render():
    st.title("새로운 페이지")
    # 페이지 내용 구현
```

2. `app.py`에 라우팅 추가
```python
from app_pages import new_page

if current_menu == 'New Page':
    new_page.render()
```

## 🐛 Troubleshooting

### 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep -E '8502|8003|8080|5433'

# docker-compose.yml에서 포트 변경
```

### FastAPI 연결 에러
```bash
# Backend 로그 확인
docker logs aimedpipeline_backend

# Backend 재시작
docker compose restart backend
```

### Airflow 접속 불가
```bash
# Airflow 초기화 상태 확인
docker logs aimedpipeline_airflow

# 데이터베이스 재초기화 (주의: 데이터 손실)
docker compose down -v
docker compose up -d
```

## 📝 Configuration

### Environment Variables

```yaml
# Streamlit
STREAMLIT_SERVER_HEADLESS: "true"
STREAMLIT_SERVER_ENABLE_CORS: "false"
FASTAPI_SERVER_URL: http://backend:8000

# FastAPI Backend
AIRFLOW_BASE_URL: http://airflow:8080
AIRFLOW_DAG_ID: mri_pipeline

# Airflow
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
AIRFLOW__CORE__EXECUTOR: LocalExecutor
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👥 Authors

- **suhhongyiel** - [GitHub](https://github.com/suhhongyiel)

## 🙏 Acknowledgments

- Apache Airflow for workflow management
- Streamlit for rapid UI development
- FastAPI for modern API framework
