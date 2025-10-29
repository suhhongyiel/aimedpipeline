# # backend/fastapi_mock_server.py
# from fastapi import FastAPI
# from pydantic import BaseModel
# import random

# app = FastAPI()
# jobs = {}

# @app.get("/")
# def read_root():
#     return {"message": "Welcome to the AIMed Pipeline Mock API!"}

# class JobRequest(BaseModel):
#     job_type: str

# @app.post("/run-job-with-upload")
# async def run_job_with_upload(
#     files: List[UploadFile] = File(...), 
#     job_type: str = Form(...)
# ):
#     # 1. 각 작업별 고유 디렉토리 생성
#     job_dir_id = str(uuid.uuid4())
#     job_path = os.path.join(SHARED_STORAGE_PATH, job_dir_id)
#     input_path = os.path.join(job_path, "input")
#     output_path = os.path.join(job_path, "output")
#     os.makedirs(input_path, exist_ok=True)
#     os.makedirs(output_path, exist_ok=True)

#     # 2. 업로드된 파일을 공유 스토리지에 저장
#     for file in files:
#         file_location = os.path.join(input_path, file.filename)
#         with open(file_location, "wb+") as f:
#             f.write(file.file.read())

#     # 3. Slurm 작업 제출 (sbatch 명령어 실행)
#     # 실제로는 sbatch 스크립트 파일을 생성하고 제출합니다.
#     sbatch_script_content = f"""#!/bin/bash
# #SBATCH --job-name=mri-preprocess-{job_dir_id}
# #SBATCH --output={output_path}/job.log
# #SBATCH --error={output_path}/job.err
# #SBATCH --ntasks=1

# echo "Starting MRI preprocessing job..."
# # 이 부분이 실제 전처리 스크립트를 실행하는 부분입니다.
# python /path/to/your/preprocess_mri.py --input-dir {input_path} --output-dir {output_path}
# echo "Job finished."
# """
#     script_path = os.path.join(job_path, "submit.slurm")
#     with open(script_path, "w") as f:
#         f.write(sbatch_script_content)

#     try:
#         # sbatch 명령어 실행
#         result = subprocess.run(["sbatch", script_path], capture_output=True, text=True, check=True)
#         # 예시 출력: "Submitted batch job 12345"
#         slurm_job_id = result.stdout.strip().split()[-1]
#     except (subprocess.CalledProcessError, FileNotFoundError) as e:
#         raise HTTPException(status_code=500, detail=f"Failed to submit job to Slurm: {e}")

#     # 4. FastAPI 내부의 jobs 딕셔너리에 실제 Slurm Job ID 저장
#     # 실제 앱에서는 DB에 저장해야 합니다.
#     internal_job_id = job_dir_id # Streamlit은 이 ID를 사용
#     jobs[job_id] = {
#         "slurm_id": slurm_job_id,
#         "status": "Queued", # Slurm 상태와 동기화 필요
#         "log_path": f"{output_path}/job.log"
#     }
#     return {"job_id": internal_job_id}

# @app.get("/job-status/{job_id}")
# def job_status(job_id: str):
#     job = jobs.get(job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")

#     # Slurm의 상태를 조회 (squeue 명령어)
#     slurm_id = job['slurm_id']
#     result = subprocess.run(["squeue", "-j", slurm_id], capture_output=True, text=True)
    
#     # squeue 결과 파싱하여 상태 업데이트 (여기서는 단순화)
#     # ... 파싱 로직 ...

#     # 로그 파일 읽기
#     try:
#         with open(job['log_path'], 'r') as f:
#             log_content = f.read()
#     except FileNotFoundError:
#         log_content = "Waiting for job to start..."

#     # 실제 상태와 로그 반환
#     return {"status": "Running", "log": log_content} # 상태는 파싱 결과에 따라 변경
