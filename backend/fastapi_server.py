import os
import uuid
import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import shutil
import json
from typing import List
import zipfile
import tarfile
# tokenize for shell command 안전 처리
import shlex
# db 관련
# --- DB 관련 import 수정 ---
from database import SessionLocal
from models import JobLog, CommandLog, MicaPipelineJob
import models
from database import engine
from sqlalchemy.orm import Session
from fastapi import Depends

# ===== 환경변수 기본값 =====
AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://airflow:8080")
#AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
AIRFLOW_API  = f"{AIRFLOW_BASE}/api/v1"
AIRFLOW_DAG  = os.getenv("AIRFLOW_DAG_ID", "mica_pipeline")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASS = os.getenv("AIRFLOW_PASSWORD", "admin")

# --- 서버 시작 시 DB 테이블 생성 ---
# 이미 있으면 별 작업 안함
models.Base.metadata.create_all(bind=engine)
# --------------------------------
app = FastAPI(title="AIMed Pipeline Backend")

# Streamlit(별도 컨테이너)에서 호출하므로 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def _auth():
    return (AIRFLOW_USER, AIRFLOW_PASS)

# db session 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    models.Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"ok": True, "airflow": AIRFLOW_BASE, "dag": AIRFLOW_DAG}

@app.post("/run-job")
def run_job(job_type: str = "MRI 분석", db: Session = Depends(get_db)):
    run_id = f"ui_{uuid.uuid4().hex[:8]}"
    payload = {"dag_run_id": run_id, "conf": {"job_type": job_type}}
    # Airflow mock (실제 Airflow 없이)
    try:
        r = requests.post(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns", json=payload, auth=_auth(), timeout=2)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text)
    except Exception as e:
        print(f"[Mock] Airflow 호출 실패, 테스트용으로 무시: {e}")
        
    # ---- 로그 DB에 저장 ----
    log = JobLog(
        job_id=run_id,
        job_type=job_type,
        status="requested",
        log="Job requested (mock)"
    )
    db.add(log)
    db.commit()
    return {"job_id": run_id, "note": "Airflow 미연동 mock"}

@app.get("/job-status/{job_id}")
def job_status(job_id: str):
    try:
        # 실제 Airflow REST API 호출 부분
        dr = requests.get(f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}", auth=_auth(), timeout=2)
        if dr.status_code != 200:
            raise HTTPException(status_code=dr.status_code, detail=dr.text)
        drj = dr.json()
        state = drj.get("state", "unknown")

        tis = requests.get(
            f"{AIRFLOW_API}/dags/{AIRFLOW_DAG}/dagRuns/{job_id}/taskInstances",
            auth=_auth(), timeout=2
        )
        if tis.status_code != 200:
            raise HTTPException(status_code=tis.status_code, detail=tis.text)
        tasks = []
        for ti in tis.json().get("task_instances", []):
            tasks.append({
                "task_id": ti["task_id"],
                "state": ti["state"],
                "start_date": ti.get("start_date"),
                "end_date": ti.get("end_date"),
                "try_number": ti.get("try_number"),
            })

        total = max(len(tasks), 1)
        success = sum(1 for t in tasks if (t["state"] or "").lower() == "success")
        running = sum(1 for t in tasks if (t["state"] or "").lower() in ("queued", "running"))
        progress = int((success/total)*100 + (running/total)*25)
        progress = min(progress, 99 if state.lower() not in ("success", "failed") else 100)

        ui_url = f"{AIRFLOW_BASE}/dag/{AIRFLOW_DAG}/grid?dag_run_id={job_id}"
        return {
            "status": state, "tasks": tasks, "progress": progress,
            "airflow_ui": ui_url, "log": f"DagRun {job_id} is {state}"
        }
    except Exception as e:
        # Airflow 요청 실패 시 mock 데이터 반환 (에러 안 나게 함)
        print(f"[Mock] Airflow 상태조회 실패, 더미값 반환: {e}")
        return {
            "status": "mocked",
            "tasks": [{"task_id": "mocked_task", "state": "success"}],
            "progress": 100,
            "airflow_ui": "mock_url",
            "log": f"Mock DagRun {job_id} is mocked"
        }
    
@app.post("/run-command")
async def run_command(data: dict):
    """서버에서 명령어를 실행하고 결과를 반환합니다."""
    cmd = data.get("cmd")
    if not cmd:
        raise HTTPException(status_code=400, detail="Command is required")
    
    # 작업 디렉토리 설정 (볼륨 마운트된 경로 사용)
    work_dir = data.get("work_dir", "/app/workspace")
    work_dir = os.path.abspath(work_dir) if not work_dir.startswith("/") else work_dir
    
    # 작업 디렉토리가 없으면 생성
    os.makedirs(work_dir, exist_ok=True)
    
    start_time = datetime.now()
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=work_dir,
            timeout=data.get("timeout", 300)  # 기본 5분 타임아웃
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # DB에 로그 저장
        session = SessionLocal()
        try:
            log = CommandLog(
                command=cmd,
                output=result.stdout,
                error=result.stderr
            )
            session.add(log)
            session.commit()
        finally:
            session.close()
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
            "work_dir": work_dir,
            "duration": f"{duration:.2f}s",
            "timestamp": datetime.now().isoformat()
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Command timeout after {data.get('timeout', 300)} seconds",
            "returncode": -1,
            "work_dir": work_dir,
            "duration": None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "returncode": -1,
            "work_dir": work_dir,
            "duration": None,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/list-files")
async def list_files(path: str = "/app/workspace"):
    """지정된 경로의 파일 목록을 반환합니다."""
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        
        files = []
        for item in path_obj.iterdir():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:]
                })
            except PermissionError:
                continue
        
        # 이름순 정렬
        files.sort(key=lambda x: (x["type"] == "file", x["name"]))
        
        return {
            "path": path,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/create-file")
async def create_file(data: dict):
    """파일을 생성합니다."""
    file_path = data.get("file_path")
    content = data.get("content", "")
    work_dir = data.get("work_dir", "/app/workspace")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    # 절대 경로가 아니면 work_dir 기준으로 상대 경로 처리
    if not file_path.startswith("/"):
        file_path = os.path.join(work_dir, file_path)
    
    try:
        path_obj = Path(file_path)
        # 디렉토리가 없으면 생성
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 생성
        path_obj.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "file_path": str(path_obj),
            "size": path_obj.stat().st_size,
            "message": f"File created: {file_path}"
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.delete("/delete-file")
async def delete_file(file_path: str, work_dir: str = "/app/workspace"):
    """파일 또는 디렉토리를 삭제합니다."""
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    # 절대 경로가 아니면 work_dir 기준으로 상대 경로 처리
    if not file_path.startswith("/"):
        file_path = os.path.join(work_dir, file_path)
    
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {file_path}")
        
        # 안전장치: 작업 디렉토리 외부 삭제 방지
        if not str(path_obj.resolve()).startswith("/app"):
            raise HTTPException(status_code=403, detail="Cannot delete files outside /app directory")
        
        if path_obj.is_dir():
            import shutil
            shutil.rmtree(path_obj)
            item_type = "directory"
        else:
            path_obj.unlink()
            item_type = "file"
        
        return {
            "success": True,
            "file_path": str(path_obj),
            "type": item_type,
            "message": f"{item_type.capitalize()} deleted: {file_path}"
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/read-file")
async def read_file(file_path: str, work_dir: str = "/app/workspace"):
    """파일 내용을 읽습니다."""
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    # 절대 경로가 아니면 work_dir 기준으로 상대 경로 처리
    if not file_path.startswith("/"):
        file_path = os.path.join(work_dir, file_path)
    
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        if not path_obj.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {file_path}")
        
        # 안전장치: 작업 디렉토리 외부 파일 읽기 방지
        if not str(path_obj.resolve()).startswith("/app"):
            raise HTTPException(status_code=403, detail="Cannot read files outside /app directory")
        
        content = path_obj.read_text(encoding="utf-8")
        stat = path_obj.stat()
        
        return {
            "file_path": str(path_obj),
            "content": content,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/upload-file")
async def upload_file(
    files: List[UploadFile] = File(...),
    destination: str = Form("/app/data"),
    extract_archives: bool = Form(True)
):
    """
    파일을 서버에 업로드합니다.
    압축 파일(.zip, .tar.gz, .tgz)은 자동으로 압축 해제할 수 있습니다.
    """
    try:
        # 목적지 디렉토리 생성
        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        extracted_files = []
        total_size = 0
        
        for file in files:
            # 파일 저장
            file_path = dest_path / file.filename
            
            # 파일 쓰기
            with file_path.open("wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            file_size = file_path.stat().st_size
            total_size += file_size
            
            file_info = {
                "filename": file.filename,
                "path": str(file_path),
                "size": file_size,
                "content_type": file.content_type,
                "extracted": False
            }
            
            # 압축 파일 자동 압축 해제
            if extract_archives:
                extracted = False
                
                # ZIP 파일 처리
                if file.filename.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(dest_path)
                        extracted = True
                        extracted_files.extend(zip_ref.namelist())
                        file_info["extracted"] = True
                        file_info["archive_type"] = "zip"
                    except Exception as e:
                        file_info["extraction_error"] = str(e)
                
                # TAR.GZ 또는 TGZ 파일 처리
                elif file.filename.lower().endswith(('.tar.gz', '.tgz', '.tar')):
                    try:
                        with tarfile.open(file_path, 'r:*') as tar_ref:
                            tar_ref.extractall(dest_path)
                        extracted = True
                        extracted_files.extend([m.name for m in tar_ref.getmembers()])
                        file_info["extracted"] = True
                        file_info["archive_type"] = "tar"
                    except Exception as e:
                        file_info["extraction_error"] = str(e)
                
                # 압축 해제 성공 시 원본 압축 파일 삭제 (선택사항)
                if extracted:
                    file_path.unlink()
                    file_info["original_removed"] = True
            
            uploaded_files.append(file_info)
        
        response = {
            "success": True,
            "uploaded_files": uploaded_files,
            "count": len(uploaded_files),
            "total_size": total_size,
            "destination": destination,
            "message": f"{len(uploaded_files)} file(s) uploaded successfully"
        }
        
        if extracted_files:
            response["extracted_files_count"] = len(extracted_files)
            response["extracted_files_sample"] = extracted_files[:10]  # 처음 10개만 표시
        
        return response
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/validate-bids")
async def validate_bids(directory: str = "/app/data/bids"):
    """BIDS 포맷 검증을 수행합니다."""
    try:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        
        # 무시할 시스템 폴더/파일
        ignore_list = {"__MACOSX", ".DS_Store", "Thumbs.db", ".git", ".gitignore"}
        
        # BIDS 검증 결과
        validation_result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "directory": directory,
            "structure": {},
            "details": []
        }
        
        # 필수 파일/폴더 체크
        required_items = {
            "dataset_description.json": False,
            "README": False,
            "participants.tsv": False
        }
        
        # 디렉토리 구조 분석
        all_items = []
        subject_dirs = []
        
        for item in dir_path.iterdir():
            # 시스템 폴더/파일 무시
            if item.name in ignore_list:
                validation_result["warnings"].append(f"Ignored system file/folder: {item.name}")
                continue
            
            all_items.append(item.name)
            
            if item.name in required_items:
                required_items[item.name] = True
                validation_result["structure"][item.name] = "found"
                validation_result["details"].append(f"✓ {item.name}")
            elif item.is_dir() and item.name.startswith("sub-"):
                subject_dirs.append(item.name)
                validation_result["structure"][item.name] = "subject_directory"
                
                # Subject 폴더 내부 확인
                sub_folders = [f.name for f in item.iterdir() if f.is_dir() and f.name not in ignore_list]
                if sub_folders:
                    validation_result["details"].append(f"✓ {item.name}/ → {', '.join(sub_folders)}")
                else:
                    validation_result["warnings"].append(f"{item.name} folder is empty")
        
        # 필수 항목 검사
        missing_items = [k for k, v in required_items.items() if not v]
        
        if missing_items:
            for item in missing_items:
                validation_result["errors"].append(f"✗ Missing required file: {item}")
                validation_result["details"].append(f"✗ {item} (missing)")
        
        # subject 폴더 개수 확인
        validation_result["subject_count"] = len(subject_dirs)
        validation_result["subject_list"] = subject_dirs[:10]  # 처음 10개만
        
        if len(subject_dirs) == 0:
            validation_result["errors"].append("No subject directories found (sub-*)")
        else:
            validation_result["details"].append(f"✓ Found {len(subject_dirs)} subject(s)")
        
        # dataset_description.json 검증
        desc_file = dir_path / "dataset_description.json"
        if desc_file.exists():
            try:
                with desc_file.open("r", encoding="utf-8") as f:
                    desc_data = json.load(f)
                    required_fields = ["Name", "BIDSVersion"]
                    missing_fields = [f for f in required_fields if f not in desc_data]
                    
                    if missing_fields:
                        validation_result["errors"].append(
                            f"dataset_description.json missing fields: {', '.join(missing_fields)}"
                        )
                    else:
                        validation_result["dataset_info"] = {
                            "name": desc_data.get("Name"),
                            "version": desc_data.get("BIDSVersion"),
                            "dataset_type": desc_data.get("DatasetType", "unknown")
                        }
                        validation_result["details"].append(
                            f"✓ Dataset: {desc_data.get('Name')} (BIDS {desc_data.get('BIDSVersion')})"
                        )
            except json.JSONDecodeError as e:
                validation_result["errors"].append(f"dataset_description.json is not valid JSON: {str(e)}")
            except Exception as e:
                validation_result["errors"].append(f"Error reading dataset_description.json: {str(e)}")
        
        # README 파일 확인
        readme_file = dir_path / "README"
        if readme_file.exists():
            try:
                readme_size = readme_file.stat().st_size
                validation_result["details"].append(f"✓ README ({readme_size} bytes)")
            except:
                pass
        
        # participants.tsv 확인
        participants_file = dir_path / "participants.tsv"
        if participants_file.exists():
            try:
                with participants_file.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
                    validation_result["details"].append(f"✓ participants.tsv ({len(lines)} lines)")
                    validation_result["participants_count"] = len(lines) - 1  # 헤더 제외
            except:
                pass
        
        # 최종 검증 결과
        if not validation_result["errors"]:
            validation_result["is_valid"] = True
            validation_result["message"] = "✅ Valid BIDS dataset!"
        else:
            validation_result["is_valid"] = False
            validation_result["message"] = f"❌ Invalid BIDS dataset ({len(validation_result['errors'])} error(s))"
        
        return validation_result
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/get-sessions")
async def get_sessions(subject_id: str, bids_dir: str = "/app/data/bids"):
    """특정 Subject의 Session 목록을 가져옵니다."""
    try:
        # 호스트 데이터 디렉토리 확인
        host_data_dir = os.getenv("HOST_DATA_DIR", "/home/admin1/Documents/aimedpipeline/data")
        
        # Subject 디렉토리 경로 구성
        sub_dirname = subject_id if subject_id.startswith("sub-") else f"sub-{subject_id}"
        
        # 여러 경로 시도 (컨테이너 내부 경로 우선, 호스트 경로는 백업)
        possible_paths = []
        
        # 1. 컨테이너 내부 경로 (마운트된 경로)
        if bids_dir.startswith('/app/data/'):
            possible_paths.append(Path(bids_dir) / sub_dirname)
            possible_paths.append(Path(bids_dir) / subject_id)
        
        # 2. 직접 컨테이너 경로 시도
        possible_paths.append(Path("/app/data/bids") / sub_dirname)
        possible_paths.append(Path("/app/data/bids") / subject_id)
        
        # 3. 호스트 경로 (Backend가 호스트에서 실행 중인 경우)
        possible_paths.append(Path(host_data_dir) / "bids" / sub_dirname)
        possible_paths.append(Path(host_data_dir) / "bids" / subject_id)
        
        # 4. 상대 경로도 시도 (Backend가 프로젝트 루트에서 실행 중인 경우)
        possible_paths.append(Path("./data/bids") / sub_dirname)
        possible_paths.append(Path("./data/bids") / subject_id)
        
        found_path = None
        for path in possible_paths:
            try:
                if path.exists():
                    found_path = path
                    break
            except Exception:
                continue
        
        if not found_path:
            # 에러 메시지에 시도한 경로들 포함
            tried_paths = [str(p) for p in possible_paths[:4]]  # 처음 4개만 표시
            return {
                "success": False,
                "sessions": [],
                "message": f"Subject directory not found. Tried: {', '.join(tried_paths)}"
            }
        
        # Session 디렉토리 찾기
        session_dirs = []
        try:
            for item in found_path.iterdir():
                if item.is_dir() and item.name.startswith("ses-"):
                    session_id = item.name.replace("ses-", "")
                    session_dirs.append({
                        "session_id": session_id,
                        "display_name": item.name,  # ses-M126
                        "full_name": item.name      # ses-M126
                    })
        except Exception as e:
            return {
                "success": False,
                "sessions": [],
                "message": f"Error reading directory {found_path}: {str(e)}"
            }
        
        # Session ID로 정렬
        session_dirs.sort(key=lambda x: x["session_id"])
        
        return {
            "success": True,
            "subject_id": subject_id,
            "sessions": session_dirs,
            "count": len(session_dirs),
            "message": f"Found {len(session_dirs)} session(s) for {subject_id}",
            "debug_path": str(found_path)  # 디버깅용
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "sessions": [],
            "message": f"Error: {str(e)}",
            "traceback": traceback.format_exc()
        }

async def run_mica_via_airflow(
    subject_id: str,
    session_id: str,
    processes: list,
    bids_dir: str,
    output_dir: str,
    fs_licence: str,
    threads: int,
    freesurfer: bool,
    user: str,
    proc_structural_flags: list | None = None,
    proc_surf_flags: list | None = None,
    post_structural_flags: list | None = None,
    proc_func_flags: list | None = None,
    dwi_flags: list | None = None,
    sc_flags: list | None = None,
):
    """Airflow DAG를 트리거하여 MICA Pipeline을 실행합니다."""
    try:
        # DAG Run ID 생성
        run_id = f"mica_{subject_id.replace('sub-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Airflow API 페이로드
        payload = {
            "dag_run_id": run_id,
            "conf": {
                "subject_id": subject_id,
                "session_id": session_id,
                "processes": processes,
                "bids_dir": bids_dir,
                "output_dir": output_dir,
                "fs_licence": fs_licence,
                "threads": threads,
                "freesurfer": freesurfer,
                "user": user,
                "proc_structural_flags": proc_structural_flags or [],
                "proc_surf_flags": proc_surf_flags or [],
                "post_structural_flags": post_structural_flags or [],
                "proc_func_flags": proc_func_flags or [],
                "dwi_flags": dwi_flags or [],
                "sc_flags": sc_flags or [],
            }
        }
        
        # Airflow API 호출
        response = requests.post(
            f"{AIRFLOW_API}/dags/mica_pipeline/dagRuns",
            json=payload,
            auth=_auth(),
            timeout=10
        )
        
        if response.status_code in (200, 201):
            airflow_data = response.json()
            
            # DB에 저장
            session = SessionLocal()
            try:
                container_name = f"{subject_id}"
                if session_id:
                    container_name += f"_ses-{session_id}"
                if processes:
                    container_name += f"_{processes[0]}"
                
                mica_job = MicaPipelineJob(
                    job_id=run_id,
                    subject_id=subject_id,
                    session_id=session_id,
                    processes=",".join(processes),
                    container_name=container_name,
                    pid=None,  # Airflow가 관리
                    status="processing",
                    progress=0.0,
                    log_file=f"{output_dir}/logs/{processes[0]}/fin/{container_name}.log",
                    error_log_file=f"{output_dir}/logs/{processes[0]}/error/{container_name}_error.log"
                )
                session.add(mica_job)
                session.commit()
            finally:
                session.close()
            
            return {
                "success": True,
                "mode": "airflow",
                "dag_run_id": run_id,
                "subject_id": subject_id,
                "session_id": session_id,
                "processes": processes,
                "user": user,
                "airflow_url": f"{AIRFLOW_BASE}/dags/mica_pipeline/grid?dag_run_id={run_id}",
                "message": f"✅ MICA Pipeline이 Airflow를 통해 시작되었습니다.\n\n"
                          f"DAG Run ID: {run_id}\n"
                          f"User: {user}\n"
                          f"Subject: {subject_id}\n\n"
                          f"💡 Airflow UI에서 실행 상태를 확인하세요: http://localhost:8080",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Airflow API failed: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Airflow: {str(e)}"
        )


@app.post("/run-mica-pipeline")
async def run_mica_pipeline(data: dict):
    """mica-pipeline docker 명령을 실행합니다. (직접 실행 또는 Airflow 통해 실행)"""
    try:
        # 실행 방식 선택
        use_airflow = data.get("use_airflow", False)
        user = data.get("user", "anonymous")
        
        # 호스트의 실제 데이터 경로 (환경 변수에서 가져오기)
        host_data_dir = os.getenv("HOST_DATA_DIR", "/home/admin1/Documents/aimedpipeline/data")
        
        # 필수 파라미터 확인 (컨테이너 내부 경로)
        bids_dir = data.get("bids_dir", "./data/bids")
        output_dir = data.get("output_dir", "./data/derivatives")
        subject_id = data.get("subject_id")
        processes = data.get("processes", [])

        # ✅ proc_structural 단독 선택 여부 (미니멀 모드 스위치)
        simple_structural = (processes == ["proc_structural"])
        
        # 추가 파라미터
        session_id = data.get("session_id", "")
        # session_id에서 "ses-" 접두사 제거 (사용자가 "ses-01" 형식으로 입력할 수 있음)
        if session_id:
            session_id = session_id.replace("ses-", "").strip()
        fs_licence = data.get("fs_licence", "./home/admin1/Documents/aimedpipeline/data/license.txt")
        threads = data.get("threads", 4)
        freesurfer = data.get("freesurfer", True)
    
        # 프로세스별 세부 플래그
        # (요구사항: proc_structural/proc_surf는 옵션 미사용. post_structural만 atlas 허용)
        proc_structural_flags = data.get("proc_structural_flags", [])
        proc_surf_flags = data.get("proc_surf_flags", [])
        post_structural_flags = data.get("post_structural_flags", [])
        proc_func_flags = data.get("proc_func_flags", [])
        dwi_flags = data.get("dwi_flags", [])
        sc_flags = data.get("sc_flags", [])

        # 유틸 함수들 -----------------------------------------------------------
        def join_tokens(tokens: list[str]) -> str:
            # 각 토큰을 shlex.quote로 감싸 안전하게 공백/특수문자 처리
            return " ".join(shlex.quote(t) for t in tokens if t is not None and str(t) != "")

        def normalize_flags(tokens: list[str]) -> list[str]:
            """
            - 값 동반 옵션은 '마지막 값 우선'으로 1회만 남김
            - 토글형 플래그는 중복 제거
            - -freesurfer/-fs_licence 는 여기서 제거(전역에서 1회만 삽입)
            """
            with_val = {
                "-T1wStr", "-fs_licence", "-surf_dir", "-T1", "-atlas",
                "-mainScanStr", "-func_pe", "-func_rpe", "-mainScanRun",
                "-phaseReversalRun", "-topupConfig", "-icafixTraining",
                "-sesAnat"
            }
            kv = {}               # option -> value (마지막 값이 덮어씀)
            toggles = set()       # 토글형 모음
            passthrough = []      # 기타(값 없는) 토큰 보관

            it = iter(tokens)
            for t in it:
                if t in with_val:
                    v = next(it, None)
                    if v is None or (isinstance(v, str) and v.startswith("-")):
                        continue
                    kv[t] = v
                else:
                    # -freesurfer/-fs_licence 는 전역에서만 넣기: 여기서 제거
                    if t in ("-freesurfer",):
                        continue
                    if t == "-fs_licence":
                        _ = next(it, None)  # 값 소모만 하고 버림
                        continue
                    toggles.add(t) if t.startswith("-") else passthrough.append(t)

            out = []
            for k, v in kv.items():
                if k == "-fs_licence":
                    continue
                out += [k, v]

            out += sorted(t for t in toggles if t not in ("-freesurfer",))
            out += passthrough
            return out

        def convert_to_host_path(container_path: str) -> str:
            """컨테이너 경로를 호스트 경로로 변환"""
            if container_path.startswith("/app/data"):
                return container_path.replace("/app/data", host_data_dir)
            return container_path
        # ---------------------------------------------------------------------

        # 호스트 경로로 변환
        host_bids_dir = convert_to_host_path(bids_dir)
        host_output_dir = convert_to_host_path(output_dir)
        host_fs_licence = convert_to_host_path(fs_licence)
        
        if not subject_id:
            raise HTTPException(status_code=400, detail="subject_id is required")
        if not processes:
            raise HTTPException(status_code=400, detail="At least one process must be selected")
        
        # 출력 디렉토리 생성 (컨테이너 내부 경로)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Airflow로 넘기는 경우는 기존 그대로 유지
        if use_airflow:
            return await run_mica_via_airflow(
                subject_id=subject_id,
                session_id=session_id,
                processes=processes,
                bids_dir=host_data_dir + "/bids",
                output_dir=host_data_dir + "/derivatives",
                fs_licence=host_data_dir + "/license.txt",
                threads=threads,
                freesurfer=freesurfer,
                user=user,
                # 아래 두 플래그는 무시되지만 인터페이스 유지
                proc_structural_flags=proc_structural_flags,
                proc_surf_flags=proc_surf_flags,
                post_structural_flags=post_structural_flags,
                proc_func_flags=proc_func_flags,
                dwi_flags=dwi_flags,
                sc_flags=sc_flags,
            )

        # =========================
        # 전체 Subject 실행 (ALL)
        # =========================
        if subject_id.lower() == "all":
            bids_path = Path(bids_dir)
            if not bids_path.exists():
                raise HTTPException(status_code=404, detail=f"BIDS directory not found: {bids_dir}")
            
            subjects = [d.name for d in bids_path.iterdir() 
                        if d.is_dir() and d.name.startswith("sub-") and d.name != "__MACOSX"]
            if not subjects:
                raise HTTPException(status_code=400, detail="No subjects found in BIDS directory")
            
            all_results, total_success, total_failed = [], 0, 0
            
            for sub in subjects:
                try:
                    sub_id = sub.replace("sub-", "")
                    
                    # 세션 목록 수집
                    if session_id:
                        sessions_to_process = [session_id]
                    else:
                        # bids_dir가 컨테이너 경로인지 호스트 경로인지 확인
                        if bids_dir.startswith('/app/data/'):
                            check_bids_dir = bids_dir.replace('/app/data/', f'{host_data_dir}/')
                        else:
                            check_bids_dir = bids_dir
                        
                        subject_path = Path(check_bids_dir) / sub
                        if subject_path.exists():
                            session_dirs = [d.name.replace("ses-", "") for d in subject_path.iterdir() 
                                            if d.is_dir() and d.name.startswith("ses-")]
                            sessions_to_process = session_dirs if session_dirs else [""]
                        else:
                            sessions_to_process = [""]

                    for ses in sessions_to_process:
                        container_name = f"{sub}" + (f"_ses-{ses}" if ses else "")
                        if processes:
                            container_name += f"_{processes[0]}"

                        container_log_dir = Path(output_dir) / "logs" / (processes[0] if processes else "")
                        container_log_dir.mkdir(parents=True, exist_ok=True)
                        (container_log_dir / "fin").mkdir(exist_ok=True)
                        (container_log_dir / "error").mkdir(exist_ok=True)

                        container_log_file = container_log_dir / "fin" / f"{container_name}.log"
                        container_error_log_file = container_log_dir / "error" / f"{container_name}_error.log"

                        # ---- 분기: 미니멀 vs 일반 ----
                        if simple_structural:
                            use_fs_licence_min = Path(fs_licence).exists() and ('proc_structural' in processes)

                            # docker run 볼륨 마운트
                            cmd = (
                                f"docker run --rm --name {container_name} "
                                f"-v {host_bids_dir}:{host_bids_dir} "
                                f"-v {host_output_dir}:{host_output_dir} "
                            )
                            if use_fs_licence_min:
                                cmd += f"-v {host_fs_licence}:{host_fs_licence} "

                            cmd += (
                                "micalab/micapipe:v0.2.3 "
                                f"-bids {host_bids_dir} "
                                f"-out {host_output_dir} "
                                f"-sub {sub_id} "
                            )
                            if ses:  # ses 변수 사용
                                cmd += f"-ses {ses} "

                            cmd += "-proc_structural "
                            if use_fs_licence_min:
                                cmd += f"-fs_licence {host_fs_licence} "

                            cmd += f"> {container_log_file} 2> {container_error_log_file}"
                        else:
                            # 일반: 여러 프로세스 조합
                            base_switches = [f"-{p}" for p in processes]

                            # 옵션 플래그: post_structural + func + dwi + sc (struct/surf 옵션은 생략)
                            extra_tokens = (
                                #(proc_structural_flags or []) + 
                                #(proc_surf_flags or []) + 
                                (post_structural_flags or []) +
                                (proc_func_flags or []) +
                                (dwi_flags or []) +
                                (sc_flags or [])
                            )
                            normalized = normalize_flags(extra_tokens)
                            process_flags = join_tokens(base_switches + normalized)

                            use_fs_licence = Path(fs_licence).exists() and (
                                ('proc_structural' in processes) or
                                ('proc_surf' in processes and freesurfer)
                            )

                            fs_licence_mount = ""
                            if use_fs_licence:
                                fs_licence_mount = f"-v {host_fs_licence}:{host_fs_licence}"

                            cmd = (
                                f"docker run --rm --name {container_name} "
                                f"-v {host_bids_dir}:{host_bids_dir} "
                                f"-v {host_output_dir}:{host_output_dir} "
                            )
                            if fs_licence_mount:
                                cmd += f"{fs_licence_mount} "

                            cmd += (
                                "micalab/micapipe:v0.2.3 "
                                f"-bids {host_bids_dir} "
                                f"-out {host_output_dir} "
                                f"-sub {sub_id} "
                            )
                            if ses:
                                cmd += f"-ses {ses} "

                            cmd += f"-threads {threads} {process_flags} "

                            if 'proc_surf' in processes:
                                cmd += f"-freesurfer {'TRUE' if freesurfer else 'FALSE'} "

                            # 라이선스는 위 조건(use_fs_licence)일 때 항상 넘김
                            if use_fs_licence:
                                cmd += f"-fs_licence {host_fs_licence} "

                            cmd += f"> {container_log_file} 2> {container_error_log_file}"

                        # 실행
                        process = subprocess.Popen(
                            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                        )

                        # DB 기록
                        db_session = SessionLocal()
                        try:
                            log = CommandLog(
                                command=cmd,
                                output=f"Container started: {container_name} (PID: {process.pid})",
                                error=""
                            )
                            db_session.add(log)
                            mica_job = MicaPipelineJob(
                                job_id=container_name,
                                subject_id=sub,
                                session_id=ses if ses else None,
                                processes=",".join(processes),
                                container_name=container_name,
                                pid=process.pid,
                                status="processing",
                                progress=0.0,
                                log_file=str(container_log_file),
                                error_log_file=str(container_error_log_file)
                            )
                            db_session.add(mica_job)
                            db_session.commit()
                        finally:
                            db_session.close()

                        total_success += 1
                        subject_with_session = f"{sub}" + (f"_ses-{ses}" if ses else "")
                        all_results.append({
                            "subject": subject_with_session,
                            "success": True,
                            "container_name": container_name,
                            "pid": process.pid,
                            "job_id": container_name,
                            "message": "백그라운드에서 시작됨"
                        })

                except Exception as e:
                    total_failed += 1
                    all_results.append({
                        "subject": sub,
                        "success": False,
                        "message": f"시작 실패: {str(e)}"
                    })
            
            return {
                "success": True,
                "mode": "all_subjects",
                "total_subjects": len(subjects),
                "successful": total_success,
                "failed": total_failed,
                "results": all_results,
                "processes": processes,
                "timestamp": datetime.now().isoformat(),
                "message": f"✅ {total_success}개의 컨테이너가 백그라운드에서 시작되었습니다. (실패: {total_failed}개)\n\n💡 '로그 확인' 탭에서 실행 상태를 확인하세요."
            }

        # =========================
        # 단일 Subject 실행
        # =========================
        else:
            sub_id = subject_id.replace("sub-", "")
            
            # 세션 자동 감지
            actual_session = session_id
            if not session_id:
                # bids_dir가 컨테이너 경로인지 호스트 경로인지 확인
                # 컨테이너 경로(/app/data)면 호스트 경로로 변환
                if bids_dir.startswith('/app/data/'):
                    check_bids_dir = bids_dir.replace('/app/data/', f'{host_data_dir}/')
                else:
                    # 이미 호스트 경로인 경우 그대로 사용
                    check_bids_dir = bids_dir
                
                subject_path = Path(check_bids_dir) / subject_id
                print(f"[Backend] Checking for sessions in: {subject_path}")
                
                if subject_path.exists():
                    session_dirs = [d.name.replace("ses-", "") for d in subject_path.iterdir() 
                                    if d.is_dir() and d.name.startswith("ses-")]
                    if session_dirs:
                        actual_session = session_dirs[0]
                        print(f"[Backend] ✅ Auto-detected session: {actual_session}")
                    else:
                        print(f"[Backend] ⚠️ No session directories found in: {subject_path}")
                else:
                    print(f"[Backend] ⚠️ Warning: Subject path not found: {subject_path}")
            
            container_name = f"{subject_id}" + (f"_ses-{actual_session}" if actual_session else "")
            if processes:
                container_name += f"_{processes[0]}"

            container_log_dir = Path(output_dir) / "logs" / (processes[0] if processes else "")
            container_log_dir.mkdir(parents=True, exist_ok=True)
            (container_log_dir / "fin").mkdir(exist_ok=True)
            (container_log_dir / "error").mkdir(exist_ok=True)

            container_log_file = container_log_dir / "fin" / f"{container_name}.log"
            container_error_log_file = container_log_dir / "error" / f"{container_name}_error.log"

            # ---- 분기: 미니멀 vs 일반 ----
            if simple_structural:
                use_fs_licence_min = Path(fs_licence).exists() and ('proc_structural' in processes)

                # docker run 볼륨 마운트
                cmd = (
                    f"docker run --rm --name {container_name} "
                    f"-v {host_bids_dir}:{host_bids_dir} "
                    f"-v {host_output_dir}:{host_output_dir} "
                )
                if use_fs_licence_min:
                    cmd += f"-v {host_fs_licence}:{host_fs_licence} "

                cmd += (
                    "micalab/micapipe:v0.2.3 "
                    f"-bids {host_bids_dir} "
                    f"-out {host_output_dir} "
                    f"-sub {sub_id} "
                )
                if actual_session:  # 또는 ses
                    cmd += f"-ses {actual_session} "

                cmd += "-proc_structural "
                if use_fs_licence_min:
                    cmd += f"-fs_licence {host_fs_licence} "

                cmd += f"> {container_log_file} 2> {container_error_log_file}"
            else:
                # 일반
                base_switches = [f"-{p}" for p in processes]

                extra_tokens = (
                    #(proc_structural_flags or []) + 
                    #(proc_surf_flags or []) + 
                    (post_structural_flags or []) +
                    (proc_func_flags or []) +
                    (dwi_flags or []) +
                    (sc_flags or [])
                )
                normalized = normalize_flags(extra_tokens)
                process_flags = join_tokens(base_switches + normalized)

                use_fs_licence = Path(fs_licence).exists() and (
                    ('proc_structural' in processes) or
                    ('proc_surf' in processes and freesurfer)
                )

                fs_licence_mount = ""
                if use_fs_licence:
                    fs_licence_mount = f"-v {host_fs_licence}:{host_fs_licence}"

                cmd = (
                    f"docker run --rm --name {container_name} "
                    f"-v {host_bids_dir}:{host_bids_dir} "
                    f"-v {host_output_dir}:{host_output_dir} "
                )
                if fs_licence_mount:
                    cmd += f"{fs_licence_mount} "

                cmd += (
                    "micalab/micapipe:v0.2.3 "
                    f"-bids {host_bids_dir} "
                    f"-out {host_output_dir} "
                    f"-sub {sub_id} "
                )
                if actual_session:
                    cmd += f"-ses {actual_session} "

                cmd += f"-threads {threads} {process_flags} "

                if 'proc_surf' in processes:
                    cmd += f"-freesurfer {'TRUE' if freesurfer else 'FALSE'} "

                # 라이선스는 위 조건(use_fs_licence)일 때 항상 넘김
                if use_fs_licence:
                    cmd += f"-fs_licence {host_fs_licence} "

                cmd += f"> {container_log_file} 2> {container_error_log_file}"

            # 실행
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            
            # DB 기록
            session = SessionLocal()
            try:
                log = CommandLog(
                    command=cmd,
                    output=f"Container started: {container_name} (PID: {process.pid})",
                    error=""
                )
                session.add(log)
                mica_job = MicaPipelineJob(
                    job_id=container_name,
                    subject_id=subject_id,
                    session_id=actual_session,
                    processes=",".join(processes),
                    container_name=container_name,
                    pid=process.pid,
                    status="processing",
                    progress=0.0,
                    log_file=str(container_log_file),
                    error_log_file=str(container_error_log_file)
                )
                session.add(mica_job)
                session.commit()
            finally:
                session.close()
            
            return {
                "success": True,
                "mode": "single_subject",
                "command": cmd,
                "output": f"✅ MICA Pipeline이 백그라운드에서 시작되었습니다.\n\n컨테이너: {container_name}\nPID: {process.pid}\n\n💡 '로그 확인' 탭 또는 'Download Results'에서 실행 상태를 확인하세요.",
                "error": "",
                "returncode": 0,
                "subject_id": subject_id,
                "session_id": actual_session,
                "session_auto_detected": bool(actual_session and not session_id),
                "processes": processes,
                "container_name": container_name,
                "pid": process.pid,
                "job_id": container_name,
                "timestamp": datetime.now().isoformat()
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timeout after {data.get('timeout', 3600)} seconds",
            "returncode": -1
        }
    except HTTPException:
        # HTTPException은 그대로 전달
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/mica-logs")
async def get_mica_logs(output_dir: str = "/app/data/derivatives"):
    """MICA Pipeline 로그 목록을 가져옵니다."""
    try:
        logs_dir = Path(output_dir) / "logs"
        
        if not logs_dir.exists():
            return {
                "success": True,
                "logs": [],
                "message": "로그 디렉토리가 아직 생성되지 않았습니다."
            }
        
        logs = []
        
        # 각 프로세스 디렉토리 순회
        for process_dir in logs_dir.iterdir():
            if not process_dir.is_dir():
                continue
            
            process_name = process_dir.name
            
            # fin 디렉토리의 로그 파일
            fin_dir = process_dir / "fin"
            error_dir = process_dir / "error"
            
            if fin_dir.exists():
                for log_file in fin_dir.iterdir():
                    if log_file.is_file() and log_file.suffix == ".log":
                        error_file = error_dir / f"{log_file.stem}_error.log"
                        
                        logs.append({
                            "process": process_name,
                            "subject": log_file.stem,
                            "log_file": str(log_file),
                            "error_file": str(error_file) if error_file.exists() else None,
                            "size": log_file.stat().st_size,
                            "modified": log_file.stat().st_mtime,
                            "has_error": error_file.exists() and error_file.stat().st_size > 0
                        })
        
        # 수정 시간 기준 내림차순 정렬
        logs.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "success": True,
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/mica-log-content")
async def get_mica_log_content(log_file: str, lines: int = 100):
    """MICA Pipeline 로그 파일 내용을 읽습니다."""
    try:
        log_path = Path(log_file)
        
        # 보안: /app/data 외부 경로 접근 차단
        if not str(log_path).startswith("/app/data"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not log_path.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        # 파일 크기 확인
        file_size = log_path.stat().st_size
        
        # 마지막 N줄 읽기
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            content_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "success": True,
            "file": str(log_path),
            "size": file_size,
            "total_lines": len(all_lines),
            "returned_lines": len(content_lines),
            "content": "".join(content_lines)
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/mica-containers")
async def get_mica_containers():
    """실행 중인 micapipe 컨테이너 목록을 가져옵니다."""
    try:
        # docker ps 명령 실행
        result = subprocess.run(
            "docker ps --filter 'name=sub-' --format '{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.RunningFor}}'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        containers = []
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 4:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "image": parts[2],
                        "running_for": parts[3]
                    })
        
        return {
            "success": True,
            "containers": containers,
            "count": len(containers)
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/mica-container-stop")
async def stop_mica_container(container_name: str):
    """micapipe 컨테이너를 종료합니다."""
    try:
        # 보안: sub- 로 시작하는 컨테이너만 종료 가능
        if not container_name.startswith("sub-"):
            raise HTTPException(status_code=403, detail="Only sub-* containers can be stopped")
        
        # docker stop 명령 실행
        result = subprocess.run(
            f"docker stop {container_name}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "container": container_name,
            "message": f"Container {container_name} stopped" if result.returncode == 0 else "Failed to stop container",
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout while stopping container"
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/mica-jobs")
async def get_mica_jobs(status: str = None):
    """MICA Pipeline Job 목록을 조회합니다."""
    try:
        db = SessionLocal()
        try:
            query = db.query(MicaPipelineJob)
            
            # 상태 필터링
            if status:
                query = query.filter(MicaPipelineJob.status == status)
            
            jobs = query.order_by(MicaPipelineJob.started_at.desc()).all()
            
            # 실시간으로 컨테이너/Airflow 상태 확인 및 업데이트
            for job in jobs:
                if job.status == "processing":
                    # Airflow로 실행된 job인지 확인 (job_id가 "mica_"로 시작)
                    if job.job_id.startswith("mica_"):
                        # Airflow DAG Run 상태 확인
                        try:
                            airflow_response = requests.get(
                                f"{AIRFLOW_API}/dags/mica_pipeline/dagRuns/{job.job_id}",
                                auth=_auth(),
                                timeout=5
                            )
                            if airflow_response.status_code == 200:
                                airflow_data = airflow_response.json()
                                airflow_state = airflow_data.get("state")
                                
                                if airflow_state in ["success", "failed"]:
                                    job.status = "completed" if airflow_state == "success" else "failed"
                                    job.completed_at = datetime.utcnow()
                                    job.progress = 100.0
                                    
                                    if airflow_state == "failed":
                                        # Airflow 로그에서 에러 메시지 추출 (간단히 처리)
                                        job.error_message = "Airflow DAG execution failed. Check Airflow UI for details."
                                    
                                    db.commit()
                        except Exception as e:
                            print(f"Failed to check Airflow status: {e}")
                    
                    # 직접 실행된 job의 경우 Docker 컨테이너 확인
                    else:
                        result = subprocess.run(
                            f"docker inspect {job.container_name}",
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if result.returncode != 0:
                            # 컨테이너가 없음 = 완료 또는 실패
                            # 로그 파일에서 에러 확인
                            has_error = False
                            error_message = None
                            
                            # 1. 에러 로그 파일 확인
                            error_log_path = Path(job.error_log_file) if job.error_log_file else None
                            if error_log_path and error_log_path.exists():
                                error_size = error_log_path.stat().st_size
                                if error_size > 0:
                                    has_error = True
                                    with open(error_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        error_message = f.read()[-500:]
                            
                            # 2. 표준 출력 로그에서 "[ ERROR ]" 확인 (MICA Pipeline은 exit 0로 종료해도 에러 발생 가능)
                            if not has_error:
                                log_path = Path(job.log_file) if job.log_file else None
                                if log_path and log_path.exists():
                                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        log_content = f.read()
                                        if "[ ERROR ]" in log_content or "ERROR" in log_content:
                                            has_error = True
                                            # 에러 부분 추출
                                            error_lines = [line for line in log_content.split('\n') if 'ERROR' in line]
                                            error_message = '\n'.join(error_lines[-5:]) if error_lines else log_content[-500:]
                            
                            # 상태 업데이트
                            job.status = "failed" if has_error else "completed"
                            job.completed_at = datetime.utcnow()
                            job.progress = 100.0
                            if has_error:
                                job.error_message = error_message
                            db.commit()
            
            # JSON 형식으로 변환
            jobs_data = []
            for job in jobs:
                jobs_data.append({
                    "id": job.id,
                    "job_id": job.job_id,
                    "subject_id": job.subject_id,
                    "session_id": job.session_id,
                    "processes": job.processes,
                    "container_name": job.container_name,
                    "pid": job.pid,
                    "status": job.status,
                    "progress": job.progress,
                    "log_file": job.log_file,
                    "error_log_file": job.error_log_file,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message,
                    "duration": (job.completed_at - job.started_at).total_seconds() if job.completed_at else None
                })
            
            return {
                "success": True,
                "jobs": jobs_data,
                "count": len(jobs_data),
                "summary": {
                    "processing": sum(1 for j in jobs if j.status == "processing"),
                    "completed": sum(1 for j in jobs if j.status == "completed"),
                    "failed": sum(1 for j in jobs if j.status == "failed")
                }
            }
        finally:
            db.close()
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/mica-job-update")
async def update_mica_job_status(data: dict):
    """MICA Pipeline Job 상태를 수동으로 업데이트합니다."""
    try:
        job_id = data.get("job_id")
        status = data.get("status")
        progress = data.get("progress")
        error_message = data.get("error_message")
        
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        
        db = SessionLocal()
        try:
            job = db.query(MicaPipelineJob).filter(MicaPipelineJob.job_id == job_id).first()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            if status:
                job.status = status
                if status in ["completed", "failed"]:
                    job.completed_at = datetime.utcnow()
                    job.progress = 100.0
            
            if progress is not None:
                job.progress = progress
            
            if error_message:
                job.error_message = error_message
            
            db.commit()
            
            return {
                "success": True,
                "job_id": job_id,
                "status": job.status,
                "message": "Job status updated"
            }
        finally:
            db.close()
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"ERROR in /run-mica-pipeline: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

# --- 유틸: 데이터 루트 결정 (/app/data 기본) ---
def pick_existing_data_root() -> Path:
    # 여러 경로 시도 (컨테이너 내부 경로 우선)
    possible_roots = [
        Path("/app/data"),  # 컨테이너 내부 경로 (마운트됨)
        Path(os.getenv("HOST_DATA_DIR", "/home/admin1/Documents/aimedpipeline/data")),  # 호스트 경로
    ]
    
    for root in possible_roots:
        derivatives_path = root / "derivatives"
        if derivatives_path.exists():
            return root
    
    # 모든 경로가 실패한 경우
    tried_paths = [str(r / "derivatives") for r in possible_roots]
    raise HTTPException(
        status_code=404, 
        detail=f"Derivatives not found. Tried: {', '.join(tried_paths)}"
    )

# --- 보안용: derivatives 바깥 접근 방지 ---
def _ensure_inside(root: Path, target: Path) -> Path:
    root_r = root.resolve()
    target_r = target.resolve()
    if not str(target_r).startswith(str(root_r)):
        raise HTTPException(status_code=403, detail="Path traversal detected")
    return target_r

# --- 전체 derivatives를 ZIP으로 반환 ---
@app.get("/download-derivatives")
def download_derivatives():
    data_root = pick_existing_data_root()
    derivatives_root = (data_root / "derivatives").resolve()

    if not derivatives_root.exists():
        raise HTTPException(status_code=404, detail=f"Target not found: {derivatives_root}")

    # ZIP 파일 경로 준비
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"derivatives_all_{ts}.zip"
    tmp_dir = Path("/app/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / zip_name

    # ZIP 생성
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in derivatives_root.rglob("*"):
            if p.is_file():
                arcname = p.relative_to(derivatives_root)
                zf.write(p, arcname=str(arcname))

    return FileResponse(
        path=str(zip_path),
        filename=zip_name,
        media_type="application/zip",
    )