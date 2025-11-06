# 🧠 AI Medical Pipeline Platform

Streamlit, FastAPI, Airflow를 활용한 **다중 사용자 지원** 의료 영상 분석 파이프라인 플랫폼

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Airflow](https://img.shields.io/badge/Airflow-2.9.1-orange.svg)](https://airflow.apache.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [MICA Pipeline 사용법](#-mica-pipeline-사용법)
- [로그 및 결과 확인](#-로그-및-결과-확인)
- [API 문서](#-api-문서)
- [Troubleshooting](#-troubleshooting)
- [변경 이력](#-변경-이력)

---

## 🚀 Features

### 🎯 핵심 기능

#### **1. 🧠 MICA Pipeline - 뇌영상 분석 (NEW!)**
- ✅ **BIDS 포맷 검증**: 업로드된 데이터의 BIDS 표준 준수 여부 자동 확인
- ✅ **자동 Session 감지**: BIDS 구조에서 session 정보 자동 추출
- ✅ **다중 실행 모드**:
  - 단일 Subject 실행
  - 전체 Subject 일괄 실행
- ✅ **실행 방식 선택**:
  - **직접 실행**: 즉시 실행 (테스트/개발용)
  - **Airflow 실행**: 큐 관리, 리소스 제한 (프로덕션/다중 사용자 환경)
- ✅ **실시간 모니터링**:
  - Streamlit UI에서 실행 상태 확인
  - Airflow UI에서 상세 로그 확인
  - Download Results에서 통합 관리
- ✅ **에러 감지**:
  - 표준 출력 로그에서 자동 에러 감지
  - Airflow DAG 레벨 에러 검증
  - 실패 시 자동 재시도 (1회)

#### **2. 📊 Download Results & Pipeline Status**
- ✅ **통합 대시보드**: Processing, Completed, Failed 상태 한눈에 확인
- ✅ **필터링**: Status, Process, Subject별 필터링
- ✅ **로그 뷰어**: UI에서 직접 로그 확인 (Standard Output & Error)
- ✅ **Airflow 연동**: Airflow 실행 상태 자동 반영
- ✅ **컨테이너 관리**: 실행 중인 컨테이너 목록 및 중지 기능

#### **3. 🔄 Airflow 중앙 관리 시스템**
- ✅ **작업 큐 관리**: 최대 5개 DAG 동시 실행
- ✅ **리소스 제한**: Task 동시 실행 10개 제한
- ✅ **사용자 추적**: 누가, 언제, 무엇을 실행했는지 기록
- ✅ **자동 재시도**: 실패 시 5분 후 1회 재시도
- ✅ **알림 설정**: Email 알림 가능 (설정 필요)
- ✅ **상세 로그**: Task별 실행 로그 및 에러 추적

#### **4. 🖥️ 서버 명령 실행 & 파일 관리**
- ✅ Shell 명령 실행 (working directory, timeout 설정)
- ✅ 파일/폴더 업로드, 생성, 삭제, 읽기
- ✅ ZIP/TAR.GZ 자동 압축 해제

---

## 🏗️ Architecture

### 시스템 구성도

```
┌──────────────────────────────────────────────────────────────┐
│                         User Browser                          │
│                    http://localhost:8502                      │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Container                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │  • Home Dashboard                                   │     │
│  │  • MICA Pipeline (파일 업로드, BIDS 검증, 실행)    │     │
│  │  • Select Pipeline                                  │     │
│  │  • Run Pipeline                                     │     │
│  │  • Download Results (로그, 상태 확인)              │     │
│  └────────────────┬───────────────────────────────────┘     │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend Container                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  API Endpoints:                                     │     │
│  │  • /run-mica-pipeline (직접 실행 or Airflow)       │     │
│  │  • /mica-jobs (상태 조회, Airflow 연동)            │     │
│  │  • /validate-bids (BIDS 검증)                      │     │
│  │  • /upload-file, /list-files                       │     │
│  └────────────────┬───────────────────────────────────┘     │
└───────────────────┼─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌─────────────────┐   ┌────────────────────────────────┐
│ SQLite Database │   │   Airflow Container            │
│                 │   │  ┌──────────────────────────┐  │
│ • MicaPipeline  │   │  │ DAG: mica_pipeline       │  │
│   Job 상태      │   │  │                          │  │
│ • CommandLog    │   │  │ Task 1: log_start        │  │
│ • JobLog        │   │  │ Task 2: build_command    │  │
└─────────────────┘   │  │        └─ Session 자동감지│  │
                      │  │ Task 3: run_micapipe     │  │
                      │  │        └─ Docker 실행     │  │
                      │  │ Task 4: log_completion   │  │
                      │  │        └─ 에러 검증       │  │
                      │  └────────┬─────────────────┘  │
                      └───────────┼────────────────────┘
                                  │
                    /var/run/docker.sock (마운트)
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                   Host Docker Engine                          │
│                                                               │
│  ┌────────────────────────────────────────────────────┐      │
│  │  MICA Pipeline Container (실제 뇌영상 처리)        │      │
│  │  Image: micalab/micapipe:v0.2.3                    │      │
│  │                                                     │      │
│  │  • FreeSurfer (뇌 구조 분석)                        │      │
│  │  • proc_structural (구조적 처리)                   │      │
│  │  • proc_dwi (확산강조영상)                          │      │
│  │  • proc_func (기능적 MRI)                          │      │
│  │                                                     │      │
│  │  Volume Mounts:                                     │      │
│  │  • /private/.../data/bids → BIDS 데이터           │      │
│  │  • /private/.../data/derivatives → 결과 저장      │      │
│  └────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### Docker-in-Docker 구조

```
Airflow Container에서 docker run 실행
    ↓
호스트의 /var/run/docker.sock 사용
    ↓
호스트 Docker Engine이 새 컨테이너 생성
    ↓
MICA Pipeline 컨테이너가 호스트에서 실행
    ↓
호스트 리소스(GPU, CPU) 직접 사용
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# 필수 요구사항
- Docker Engine 20.10+
- Docker Compose 2.0+
- 최소 8GB RAM (MICA Pipeline 실행 시 16GB+ 권장)
- 최소 100GB 디스크 (뇌영상 데이터 및 결과)

# 권장 사항
- GPU (CUDA 지원) - FreeSurfer 가속
- 멀티코어 CPU (8+ cores)
```

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/suhhongyiel/aimedpipeline.git
cd aimedpipeline

# 2. 환경 설정 (중요!)
# docker-compose.yml 파일에서 다음 두 곳의 경로를 현재 서버의 절대 경로로 변경:
# 
#   backend:
#     environment:
#       HOST_DATA_DIR: /home/admin1/Documents/aimedpipeline/data  # ← 현재 서버의 절대 경로로 변경
#   
#   airflow:
#     environment:
#       HOST_DATA_DIR: /home/admin1/Documents/aimedpipeline/data  # ← 현재 서버의 절대 경로로 변경
#       PROJECT_ROOT: /home/admin1/Documents/aimedpipeline        # ← 프로젝트 루트 절대 경로로 변경
#
# 예시:
#   서버 A: /home/user/aimedpipeline/data
#   서버 B: /data/projects/pipeline/data
#   서버 C: /opt/medical_imaging/aimedpipeline/data

# 현재 경로 확인:
pwd
# 출력 예: /home/admin1/Documents/aimedpipeline

# 절대 경로 복사:
CURRENT_DIR=$(pwd)
echo "현재 디렉토리: $CURRENT_DIR"
echo "docker-compose.yml에 다음 경로로 설정하세요:"
echo "  HOST_DATA_DIR: $CURRENT_DIR/data"
echo "  PROJECT_ROOT: $CURRENT_DIR"

# 3. MICA Pipeline Docker 이미지 준비
docker pull micalab/micapipe:v0.2.3

# 4. 데이터 디렉토리 생성 및 권한 설정
mkdir -p ./data/bids ./data/derivatives
chmod -R 777 ./data

# 5. FreeSurfer 라이센스 파일 복사 (필요한 경우)
cp /path/to/your/license.txt ./data/license.txt

# 6. Docker Compose로 모든 서비스 시작
docker compose up -d --build

# 7. 서비스 상태 확인
docker compose ps
# 모든 서비스가 "Up" 또는 "healthy" 상태여야 함

# 8. 로그 확인 (문제 발생 시)
docker compose logs -f airflow
docker compose logs -f backend
```

### ⚠️ 다른 서버에서 사용 시 주의사항

이 프로젝트는 Docker-in-Docker 방식을 사용하므로, **호스트의 절대 경로**를 사용해야 합니다.

#### 필수 설정 변경

`docker-compose.yml` 파일에서 다음 2곳을 **반드시** 수정하세요:

```yaml
# 1. Backend 서비스
backend:
  environment:
    HOST_DATA_DIR: /현재/서버의/절대/경로/aimedpipeline/data

# 2. Airflow 서비스  
airflow:
  environment:
    HOST_DATA_DIR: /현재/서버의/절대/경로/aimedpipeline/data
    PROJECT_ROOT: /현재/서버의/절대/경로/aimedpipeline
```

#### 경로 확인 방법

```bash
# 프로젝트 루트에서 실행
cd /path/to/aimedpipeline
pwd  # 출력된 경로를 복사하여 PROJECT_ROOT에 입력
realpath ./data  # 출력된 경로를 복사하여 HOST_DATA_DIR에 입력
```

#### 예시

**서버 A (현재 서버):**
```yaml
HOST_DATA_DIR: /home/admin1/Documents/aimedpipeline/data
PROJECT_ROOT: /home/admin1/Documents/aimedpipeline
```

**서버 B:**
```yaml
HOST_DATA_DIR: /home/researcher/projects/aimedpipeline/data
PROJECT_ROOT: /home/researcher/projects/aimedpipeline
```

**서버 C:**
```yaml
HOST_DATA_DIR: /data/medical_imaging/aimedpipeline/data
PROJECT_ROOT: /data/medical_imaging/aimedpipeline
```

### 서비스 접속 URL

| 서비스 | URL | 계정 |
|--------|-----|------|
| **Streamlit UI** | http://localhost:8502 | - |
| **Airflow UI** | http://localhost:8080 | admin / admin |
| **FastAPI Docs** | http://localhost:8003/docs | - |
| **PostgreSQL** | localhost:5433 | airflow / airflow |

---

## 🧠 MICA Pipeline 사용법

### 1. BIDS 데이터 준비

MICA Pipeline은 [BIDS (Brain Imaging Data Structure)](https://bids.neuroimaging.io/) 표준 포맷을 사용합니다.

#### BIDS 디렉토리 구조 예시

```
bids/
├── dataset_description.json
├── participants.tsv
├── README
└── sub-ADNI002S1155/
    ├── sub-ADNI002S1155_sessions.tsv
    └── ses-M126/
        └── anat/
            ├── sub-ADNI002S1155_ses-M126_T1w.nii.gz
            └── sub-ADNI002S1155_ses-M126_T1w.json
```

#### 필수 파일
- `dataset_description.json`: 데이터셋 메타데이터
- `participants.tsv`: Subject 목록
- `sub-<ID>/ses-<SESSION>/anat/`: T1 MRI 영상 파일

---

### 2. Streamlit UI에서 실행

#### **Step 1: 데이터 업로드**

1. Streamlit UI 접속: http://localhost:8502
2. 사이드바에서 **"🧠 MICA Pipeline"** 클릭
3. **"📁 1. 파일 업로드"** 탭:
   - ZIP 파일 업로드 (전체 BIDS 디렉토리 압축)
   - 또는 개별 파일/폴더 업로드
   - "자동으로 압축 파일 해제" 체크

#### **Step 2: BIDS 검증**

4. **"✅ 2. BIDS 검증"** 탭:
   - 업로드된 디렉토리 선택
   - "🔍 검증" 버튼 클릭
   - 검증 결과 확인:
     - ✅ 필수 파일 존재 여부
     - 📊 Subject 수, Session 수
     - ⚠️ 경고 메시지

#### **Step 3: Process 선택**

5. **"🎯 3. 프로세스 선택 및 실행 설정"** 탭:
   
   **Subject 선택:**
   - ☑️ "🔄 전체 Subject 실행" (모든 subject 처리)
   - 또는 드롭다운에서 단일 Subject 선택
   
   **Process 선택 (다중 선택 가능):**
   - ☑️ `proc_structural`: 구조적 영상 처리 (필수)
   - ☑️ `proc_surf`: Surface 재구성
   - ☑️ `post_structural`: 후처리
   - ☑️ `proc_func`: 기능적 MRI
   - ☑️ `proc_dwi`: 확산강조영상
   
   **고급 설정:**
   - FreeSurfer 라이센스 경로: `/app/data/license.txt`
   - 스레드 수: `4` (CPU 코어 수에 맞게 조정)
   - ☑️ FreeSurfer 사용
   
   **⚙️ 실행 방식 선택:**
   
   **Option A: 직접 실행 (테스트/개발용)**
   ```
   ✅ 장점:
   • 즉시 실행 (큐 없음)
   • 간단한 사용법
   
   ⚠️ 단점:
   • 리소스 제한 없음 (과부하 위험)
   • 작업 관리 없음
   • Download Results에서만 모니터링
   
   권장: 단일 사용자, 테스트 환경
   ```
   
   **Option B: Airflow 실행 (프로덕션/다중 사용자)** ⭐ 권장
   ```
   ☑️ Airflow를 통해 실행 (권장: 다중 사용자 환경)
   
   ✅ 장점:
   • 작업 큐 관리 (최대 5개 동시 실행)
   • 리소스 제한 및 모니터링
   • 사용자별 작업 추적
   • 자동 재시도 (실패 시 1회)
   • 관리자가 Airflow UI에서 중앙 관리
   • Email 알림 가능
   
   ⚠️ 참고:
   • 큐 대기 시간 발생 가능 (다른 작업 실행 중일 때)
   • Airflow UI에서 실시간 로그 확인: http://localhost:8080
   
   권장: 다중 사용자, 프로덕션 환경
   ```
   
   **사용자 이름 입력** (Airflow 모드 시):
   - 작업 추적을 위한 사용자 이름
   - 예: `hong_suyeon`

#### **Step 4: 실행**

6. **"▶️ 4. 실행"** 탭:
   - 설정 요약 확인
   - **"▶️ 실행"** 버튼 클릭
   
   **직접 실행 시:**
   ```
   ✅ MICA Pipeline이 백그라운드에서 시작되었습니다.
   
   컨테이너: sub-ADNI002S1155_ses-M126_proc_structural
   PID: 12345
   
   💡 '로그 확인' 탭 또는 'Download Results'에서 실행 상태를 확인하세요.
   ```
   
   **Airflow 실행 시:**
   ```
   ✅ MICA Pipeline이 Airflow를 통해 시작되었습니다.
   
   DAG Run ID: mica_ADNI002S1155_20251103_171124
   User: hong_suyeon
   Subject: sub-ADNI002S1155
   
   💡 Airflow UI에서 실행 상태를 확인하세요: http://localhost:8080
   ```

#### **Step 5: 모니터링**

7. **"📊 5. 로그 확인"** 탭:
   
   **실행 중인 컨테이너:**
   ```
   sub-ADNI002S1155_ses-M126_proc_structural  [실행 중]  [🛑 중지]
   ```
   
   **완료된 로그:**
   ```
   ✅ sub-ADNI002S1155_ses-M126_proc_structural.log
      • Process: proc_structural
      • Size: 1.2 MB
      • Modified: 2025-11-03 17:30
      
      📄 Standard Output (Last 100 lines)
      📄 Error Output (Last 100 lines)
   ```

---

### 3. Download Results에서 상태 확인

1. 사이드바에서 **"📥 Download Results"** 클릭

2. **📊 MICA Pipeline Status Overview:**
   ```
   Total Jobs: 5
   ⏳ Processing: 2
   ✅ Completed: 2
   ❌ Failed: 1
   ```

3. **🔍 Filter Jobs:**
   - Status Filter: `All` / `Processing` / `Completed` / `Failed`
   - Process Filter: `proc_structural` / `proc_dwi` / ...
   - Subject Filter: `sub-ADNI002S1155` / `sub-ADNI002S4229` / ...

4. **📋 Job Results 테이블:**
   | Status | Subject | Session | Process | Started | Duration | Progress | Job ID |
   |--------|---------|---------|---------|---------|----------|----------|--------|
   | ✅ Completed | sub-ADNI002S1155 | M126 | proc_structural | 2025-11-03 17:00 | 45m | 100% | mica_... |
   | ⏳ Processing | sub-ADNI002S4229 | M01 | proc_structural | 2025-11-03 17:30 | 10m | 30% | mica_... |
   | ❌ Failed | sub-ADNI003S1234 | M126 | proc_structural | 2025-11-03 17:15 | 5m | 100% | mica_... |

5. **💾 Download Completed Results:**
   - Job 선택
   - 실행 정보 확인
   - "📖 View Standard Log" 또는 "⚠️ View Error Log" 버튼 클릭
   - 로그 내용 확인

6. **❌ Failed Jobs:**
   - 실패한 작업의 에러 메시지 확인
   - Airflow UI에서 상세 로그 확인
   - 문제 해결 후 재실행

---

### 4. Airflow UI에서 상세 모니터링

#### 접속 및 로그인
```
URL: http://localhost:8080
Username: admin
Password: admin
```

#### DAG 확인
1. **DAGs** 메뉴 클릭
2. **mica_pipeline** 검색 또는 클릭
3. **Grid** 또는 **Graph** 뷰 선택

#### 실행 중인 작업 확인
```
Task 상태:
• 초록색 테두리: 실행 중 (running)
• 초록색: 완료 (success)
• 빨간색: 실패 (failed)
• 노란색: 재시도 대기 (up_for_retry)
• 회색: 대기 중 (queued)
```

#### Task별 로그 확인
1. Task 클릭 (예: `run_micapipe`)
2. **"Log"** 버튼 클릭
3. 실시간 로그 확인:
   ```
   [2025-11-03 17:11:28] Running command: docker run ...
   [2025-11-03 17:11:30] Auto-detected session: M126
   [2025-11-03 17:11:32] Starting MICA Pipeline...
   ```

#### 작업 관리
- **Pause**: DAG 일시 중지 (새 실행 차단)
- **Trigger**: 수동 실행
- **Clear**: Task 상태 초기화 및 재실행
- **Mark Success/Failed**: 수동으로 상태 변경

---

## 📂 로그 및 결과 확인

### 로그 파일 위치

#### 1. Airflow 실행 로그
```bash
위치: Airflow 컨테이너 내부
경로: /opt/airflow/logs/dag_id=mica_pipeline/run_id=<JOB_ID>/task_id=<TASK>/

확인 방법:
• Airflow UI → DAG → Run → Task → "Log" 버튼
• 터미널: docker exec aimedpipeline_airflow cat /opt/airflow/logs/...

내용:
• DAG 실행 시작/종료
• Session 자동 감지 결과
• Docker 명령어 생성 및 실행
• 에러 검증 결과
```

#### 2. MICA Pipeline 실행 로그
```bash
위치: 호스트 및 모든 컨테이너
경로: /private/hysuh/07-pipeline/data/derivatives/logs/<PROCESS>/

구조:
data/derivatives/logs/
  proc_structural/
    fin/
      sub-ADNI002S1155_ses-M126_proc_structural.log      # 표준 출력
    error/
      sub-ADNI002S1155_ses-M126_proc_structural_error.log  # 에러 출력

확인 방법:
• Streamlit UI → MICA Pipeline → "로그 확인" 탭
• Download Results → Job 선택 → "View Log" 버튼
• 터미널: tail -f /private/.../logs/proc_structural/fin/*.log

내용:
• MICA Pipeline 버전 정보
• Subject, Session 정보
• 처리 단계별 진행 상황
• FreeSurfer 실행 로그
• 에러 메시지 (있을 경우)
```

#### 3. MICA Pipeline 결과 파일
```bash
위치: 호스트 및 모든 컨테이너
경로: /private/hysuh/07-pipeline/data/derivatives/micapipe_v*/

구조:
data/derivatives/
  micapipe_v0.2.0/
    sub-ADNI002S1155/
      anat/                 # 해부학적 영상 처리 결과
        ├── sub-ADNI002S1155_T1w_brain.nii.gz
        └── sub-ADNI002S1155_T1w_brain_mask.nii.gz
      surf/                 # Surface 재구성 결과
        ├── lh.pial
        ├── rh.pial
        └── ...
      xfm/                  # 변환 행렬
      QC/                   # 품질 관리 리포트
        ├── sub-ADNI002S1155_QC.html
        └── screenshots/
      logs/                 # 프로세스별 상세 로그
        └── proc_structural.log
      parc/                 # Parcellation 결과
      maps/                 # Connectivity maps
      dwi/                  # DWI 처리 결과 (선택)
      func/                 # fMRI 처리 결과 (선택)

확인 방법:
• 서버 터미널: ls -la /private/.../derivatives/micapipe_v0.2.0/
• 컨테이너 내부: ls -la /app/data/derivatives/micapipe_v0.2.0/
```

### 실시간 모니터링

#### Option 1: Streamlit UI
```
1. "🧠 MICA Pipeline" → "📊 5. 로그 확인" 탭
   • 실행 중인 컨테이너 목록
   • 로그 파일 목록 (자동 갱신)
   • 로그 내용 뷰어

2. "📥 Download Results"
   • Processing/Completed/Failed 요약
   • Job별 상세 정보
   • 필터링 및 검색
```

#### Option 2: Airflow UI
```
http://localhost:8080

1. "mica_pipeline" DAG 클릭
2. "Grid" 또는 "Graph" 뷰
3. Task 클릭 → "Log" 버튼
4. 실시간 로그 스트리밍
```

#### Option 3: 터미널 (고급 사용자)
```bash
# 실행 중인 컨테이너 확인
docker ps --filter "name=sub-"

# 실시간 Docker 로그
docker logs -f sub-ADNI002S1155_ses-M126_proc_structural

# 실시간 파일 로그
tail -f /private/hysuh/07-pipeline/data/derivatives/logs/proc_structural/fin/sub-ADNI002S1155_ses-M126_proc_structural.log

# 에러 로그 확인
cat /private/hysuh/07-pipeline/data/derivatives/logs/proc_structural/error/*.log
```

---

## 📚 API 문서

FastAPI 자동 생성 문서: http://localhost:8003/docs

### 주요 API Endpoints

#### MICA Pipeline 관련

##### POST `/run-mica-pipeline`
MICA Pipeline 실행 (직접 또는 Airflow)

**Request Body:**
```json
{
  "bids_dir": "/app/data/bids",
  "output_dir": "/app/data/derivatives",
  "subject_id": "sub-ADNI002S1155",
  "session_id": "",
  "processes": ["proc_structural"],
  "fs_licence": "/app/data/license.txt",
  "threads": 4,
  "freesurfer": true,
  "use_airflow": true,
  "user": "hong_suyeon",
  "timeout": 3600
}
```

**Response (Airflow 모드):**
```json
{
  "success": true,
  "mode": "airflow",
  "dag_run_id": "mica_ADNI002S1155_20251103_171124",
  "subject_id": "sub-ADNI002S1155",
  "session_id": "M126",
  "processes": ["proc_structural"],
  "user": "hong_suyeon",
  "airflow_url": "http://localhost:8080/dags/mica_pipeline/grid?dag_run_id=...",
  "message": "✅ MICA Pipeline이 Airflow를 통해 시작되었습니다.",
  "timestamp": "2025-11-03T17:11:24.753875"
}
```

##### GET `/mica-jobs?status=processing`
MICA Pipeline Job 목록 조회 (Airflow 상태 자동 연동)

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "id": 1,
      "job_id": "mica_ADNI002S1155_20251103_171124",
      "subject_id": "sub-ADNI002S1155",
      "session_id": "M126",
      "processes": "proc_structural",
      "container_name": "sub-ADNI002S1155_ses-M126_proc_structural",
      "pid": null,
      "status": "processing",
      "progress": 30.0,
      "log_file": "/private/.../logs/proc_structural/fin/sub-ADNI002S1155_ses-M126_proc_structural.log",
      "error_log_file": "/private/.../logs/proc_structural/error/sub-ADNI002S1155_ses-M126_proc_structural_error.log",
      "started_at": "2025-11-03T17:11:24.773396",
      "completed_at": null,
      "error_message": null,
      "duration": null
    }
  ],
  "count": 1,
  "summary": {
    "processing": 1,
    "completed": 0,
    "failed": 0
  }
}
```

##### POST `/mica-job-update`
MICA Pipeline Job 상태 수동 업데이트

**Request Body:**
```json
{
  "job_id": "mica_ADNI002S1155_20251103_171124",
  "status": "completed",
  "progress": 100.0,
  "error_message": null
}
```

##### GET `/mica-logs?output_dir=/app/data/derivatives`
MICA Pipeline 로그 파일 목록 조회

**Response:**
```json
{
  "success": true,
  "logs": [
    {
      "process": "proc_structural",
      "subject": "sub-ADNI002S1155_ses-M126_proc_structural",
      "log_file": "/app/data/derivatives/logs/proc_structural/fin/sub-ADNI002S1155_ses-M126_proc_structural.log",
      "error_file": "/app/data/derivatives/logs/proc_structural/error/sub-ADNI002S1155_ses-M126_proc_structural_error.log",
      "size": 1234567,
      "modified": 1730650000.0,
      "has_error": false
    }
  ],
  "count": 1
}
```

##### GET `/mica-log-content?log_file=<PATH>&lines=100`
MICA Pipeline 로그 파일 내용 조회

**Response:**
```json
{
  "success": true,
  "file": "/app/data/derivatives/logs/proc_structural/fin/sub-ADNI002S1155_ses-M126_proc_structural.log",
  "size": 1234567,
  "total_lines": 5000,
  "returned_lines": 100,
  "content": "MICA pipeline v0.2.3\n..."
}
```

##### GET `/mica-containers`
실행 중인 MICA Pipeline 컨테이너 목록 조회

**Response:**
```json
{
  "success": true,
  "containers": [
    {
      "name": "sub-ADNI002S1155_ses-M126_proc_structural",
      "status": "Up 10 minutes",
      "image": "micalab/micapipe:v0.2.3",
      "running_for": "10 minutes ago"
    }
  ],
  "count": 1
}
```

##### POST `/mica-container-stop`
MICA Pipeline 컨테이너 중지

**Request Body:**
```json
{
  "container_name": "sub-ADNI002S1155_ses-M126_proc_structural"
}
```

#### BIDS 검증 관련

##### POST `/validate-bids`
BIDS 포맷 검증

**Request Body:**
```json
{
  "bids_dir": "/app/data/bids"
}
```

**Response:**
```json
{
  "is_valid": true,
  "subject_count": 5,
  "subject_list": ["sub-ADNI002S1155", "sub-ADNI002S4229", ...],
  "participants_count": 5,
  "dataset_info": {
    "name": "ADNI Dataset",
    "version": "1.7.0",
    "dataset_type": "raw"
  },
  "details": [
    "✓ dataset_description.json found",
    "✓ participants.tsv found",
    "✓ 5 subjects found"
  ],
  "errors": [],
  "warnings": []
}
```

#### 파일 관리 관련

##### POST `/upload-file`
파일 업로드 (ZIP/TAR.GZ 자동 압축 해제 지원)

**Form Data:**
```
file: (binary)
destination: /app/data/bids
extract_archives: true
```

##### GET `/list-files?path=/app/data`
파일/디렉토리 목록 조회

##### POST `/create-file`
파일 생성

##### DELETE `/delete-file?file_path=/app/data/test.txt`
파일 삭제

##### GET `/read-file?file_path=/app/data/test.txt`
파일 읽기

#### Airflow 연동 관련

##### POST `/run-job`
Airflow DAG 수동 트리거 (일반 파이프라인용)

##### GET `/job-status/<job_id>`
Airflow Job 상태 조회

---

## 🛠️ Troubleshooting

### 1. Airflow DAG 실패 - "Directory nonexistent"

**증상:**
```
/bin/sh: cannot create /private/hysuh/.../logs/...: Directory nonexistent
```

**원인:**
Airflow 컨테이너에서 호스트 경로에 접근할 수 없음

**해결:**
```bash
# 1. docker-compose.yml 확인
# airflow 서비스의 volumes에 절대 경로로 마운트되어 있는지 확인

# 2. Airflow 컨테이너 재생성 (restart로는 볼륨 업데이트 안 됨)
docker compose stop airflow
docker compose rm -f airflow
docker compose up -d airflow

# 3. 마운트 확인
docker exec aimedpipeline_airflow ls -la /private/hysuh/07-pipeline/data/
```

### 2. MICA Pipeline "[ ERROR ] doesn't have T1"

**증상:**
```
[ ERROR ] Subject ADNI002S1155 doesn't have T1 on:
          /private/hysuh/07-pipeline/data/bids/sub-ADNI002S1155/anat
```

**원인:**
Session 정보가 누락되어 잘못된 경로 참조

**해결:**
```bash
# 1. BIDS 구조 확인
ls -la /private/hysuh/07-pipeline/data/bids/sub-ADNI002S1155/

# ses-* 디렉토리가 있는지 확인
# 예: ses-M126/anat/sub-ADNI002S1155_ses-M126_T1w.nii.gz

# 2. 최신 코드에는 자동 감지 기능이 있으므로 Airflow/Backend 재시작
docker compose restart airflow backend

# 3. 재실행
```

### 3. 에러인데 "Completed"로 표시

**증상:**
MICA Pipeline이 에러를 발생시켰는데 Download Results에 "Completed"로 표시

**원인:**
MICA Pipeline이 exit code 0으로 종료해도 로그에 에러 발생 가능

**해결:**
```bash
# 최신 코드에는 로그 기반 에러 감지가 있으므로 업데이트

# 1. 코드 업데이트
git pull origin main

# 2. 재시작
docker compose restart backend airflow

# 3. 기존 job 상태 강제 재검증
curl -X POST http://localhost:8003/mica-job-update \
  -H "Content-Type: application/json" \
  -d '{"job_id": "mica_...", "status": "processing"}'

# 4. /mica-jobs API 호출로 자동 재검증
curl http://localhost:8003/mica-jobs
```

### 4. Docker Permission Denied

**증상:**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**원인:**
Docker 소켓 권한 문제

**해결:**
```bash
# 1. Docker 소켓 권한 확인
ls -la /var/run/docker.sock

# 2. 권한 부여
sudo chmod 666 /var/run/docker.sock

# 3. 또는 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# 4. 서비스 재시작
docker compose restart
```

### 5. Airflow UI 접속 안 됨

**증상:**
http://localhost:8080 접속 불가

**원인:**
Airflow 초기화 진행 중 또는 에러

**해결:**
```bash
# 1. Airflow 상태 확인
docker compose ps airflow
docker compose logs airflow --tail 50

# 2. 초기화 대기 (30초~1분)
# "Uvicorn running on http://0.0.0.0:8080" 로그 확인

# 3. Health check 확인
docker inspect aimedpipeline_airflow | grep -A 10 Health

# 4. 재시작
docker compose restart airflow
```

### 6. BIDS 검증 실패

**증상:**
업로드한 데이터가 BIDS 포맷인데 검증 실패

**해결:**
```bash
# 1. 필수 파일 확인
# - dataset_description.json
# - participants.tsv
# - README

# 2. Subject 디렉토리 구조 확인
# bids/sub-<ID>/ses-<SESSION>/anat/

# 3. 파일명 규칙 확인
# sub-<ID>_ses-<SESSION>_T1w.nii.gz

# 4. 시스템 파일 제거 (__MACOSX, .DS_Store)
find /path/to/bids -name "__MACOSX" -type d -exec rm -rf {} +
find /path/to/bids -name ".DS_Store" -delete

# 5. 권한 확인
chmod -R 755 /path/to/bids
```

### 7. Disk Full

**증상:**
```
No space left on device
```

**원인:**
MICA Pipeline 결과 파일이 매우 큼 (Subject당 1-5GB)

**해결:**
```bash
# 1. 디스크 사용량 확인
df -h /

# 2. Docker 시스템 정리
docker system prune -af --volumes
docker image prune -a

# 3. 오래된 결과 파일 삭제
rm -rf /private/hysuh/07-pipeline/data/derivatives/micapipe_v0.2.0/sub-OLD*/

# 4. 로그 파일 정리
rm -rf /private/hysuh/07-pipeline/data/derivatives/logs/*/fin/*.log
```

### 8. 컨테이너가 즉시 종료됨

**증상:**
Docker 컨테이너가 시작하자마자 종료

**해결:**
```bash
# 1. 로그 확인
docker logs <container_name>

# 2. 공통 원인
# - 볼륨 마운트 경로 오류
# - 권한 문제
# - 이미지 손상

# 3. 볼륨 마운트 확인
docker inspect <container_name> | grep -A 20 Mounts

# 4. 이미지 재다운로드
docker rmi micalab/micapipe:v0.2.3
docker pull micalab/micapipe:v0.2.3
```

---

## 🔧 Configuration

### 환경 변수

#### `docker-compose.yml`

```yaml
services:
  backend:
    environment:
      AIRFLOW_BASE_URL: http://airflow:8080
      AIRFLOW_DAG_ID: mica_pipeline
      AIRFLOW_USER: admin
      AIRFLOW_PASSWORD: admin
      HOST_DATA_DIR: /private/hysuh/07-pipeline/data  # 호스트의 실제 데이터 경로
  
  airflow:
    environment:
      AIRFLOW__CORE__LOAD_EXAMPLES: "False"
      AIRFLOW__API__AUTH_BACKENDS: airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
```

### Docker 볼륨

```yaml
volumes:
  # Backend
  - ./data:/app/data                                    # 데이터 디렉토리
  - /var/run/docker.sock:/var/run/docker.sock          # Docker-in-Docker

  # Airflow
  - ./airflow/dags:/opt/airflow/dags                    # DAG 파일
  - /private/hysuh/07-pipeline/data:/private/hysuh/07-pipeline/data  # 절대 경로 마운트
  - /var/run/docker.sock:/var/run/docker.sock          # Docker-in-Docker
```

### MICA Pipeline 이미지

```bash
# 기본 이미지
micalab/micapipe:v0.2.3

# 변경 방법 (airflow/dags/mica_pipeline_dag.py)
cmd_parts.extend([
    "micalab/micapipe:v0.2.3",  # ← 여기 변경
    f"-bids {bids_dir}",
    ...
])
```

---

## 📝 변경 이력

### v2.1.0 (2025-11-03) - 에러 감지 및 Session 자동 감지 개선

#### ✨ 새 기능
- ✅ **Airflow DAG Session 자동 감지**: BIDS 디렉토리에서 ses-* 폴더 자동 탐색
- ✅ **에러 감지 로직 개선**:
  - Airflow DAG `log_completion` task에 로그 검증 추가
  - Backend에서 표준 출력 로그의 "[ ERROR ]" 패턴 검색
  - MICA Pipeline이 exit 0으로 종료해도 에러 정확히 감지
- ✅ **Airflow 상태 연동**: Download Results에 Airflow DAG 상태 실시간 반영

#### 🔧 개선
- 📊 Download Results 상태 정확도 향상 (에러를 Completed로 잘못 표시하던 문제 해결)
- 🔍 로그 기반 에러 메시지 자동 추출
- ⚡ Session 정보 없을 때 경로 오류 자동 해결

#### 🐛 버그 수정
- ❌ Airflow DAG에서 Session 누락으로 인한 "T1 not found" 에러 해결
- ❌ MICA Pipeline 에러인데 "Completed"로 표시되던 문제 해결
- ❌ Airflow 볼륨 마운트 경로 문제 해결 (재시작으로는 적용 안 되던 문제)

---

### v2.0.0 (2025-11-03) - Airflow 통합 및 다중 사용자 지원

#### ✨ 새 기능
- ✅ **Airflow 중앙 관리 시스템**: 다중 사용자 환경에서 작업 큐, 리소스 제한, 재시도
- ✅ **실행 방식 선택**: 직접 실행 vs Airflow 실행 (UI에서 선택 가능)
- ✅ **사용자 추적**: Airflow 실행 시 사용자 이름 기록
- ✅ **Download Results 페이지 완전 재작성**: 
  - MICA Pipeline Job 통합 표시
  - Airflow 상태 자동 연동
  - 로그 뷰어 내장
  - 실행 중인 컨테이너 관리
- ✅ **Docker-in-Docker**: Airflow 컨테이너에서 호스트 Docker 사용
- ✅ **백그라운드 실행**: 즉시 응답 반환, 로그에서 진행 상황 확인

#### 🔧 개선
- 📊 MICA Pipeline 실행 상태를 데이터베이스에 저장 (MicaPipelineJob 모델)
- 🔍 실시간 컨테이너 상태 확인 및 자동 업데이트
- ⚡ 에러 로그 파일 크기 기반 실패 감지
- 🎯 Session 자동 감지 (Backend에서만, v2.1.0에서 Airflow에도 추가)

#### 📚 API 추가
- `GET /mica-jobs`: Job 목록 조회 (Airflow 상태 자동 연동)
- `POST /mica-job-update`: Job 상태 수동 업데이트
- `GET /mica-logs`: 로그 파일 목록 조회
- `GET /mica-log-content`: 로그 파일 내용 조회
- `GET /mica-containers`: 실행 중인 컨테이너 목록
- `POST /mica-container-stop`: 컨테이너 중지

---

### v1.0.0 (2025-10-11) - 초기 릴리스

#### ✨ 기능
- ✅ Streamlit 기반 웹 UI
- ✅ FastAPI 백엔드
- ✅ Apache Airflow 워크플로우 관리
- ✅ MICA Pipeline 실행 (직접 실행 모드만)
- ✅ BIDS 포맷 검증
- ✅ 파일 업로드/다운로드
- ✅ 서버 명령 실행

---

## 👥 Contributors

- **Hong Suyeon** ([@suhhongyiel](https://github.com/suhhongyiel))

---

## 📄 License

이 프로젝트는 MIT 라이센스를 따릅니다.

---

## 🙏 Acknowledgments

- [MICA Lab](https://github.com/MICA-MNI) - MICA Pipeline
- [Apache Airflow](https://airflow.apache.org/)
- [Streamlit](https://streamlit.io/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

## 📧 Contact

문제가 발생하거나 질문이 있으시면 [GitHub Issues](https://github.com/suhhongyiel/aimedpipeline/issues)에 등록해주세요.
