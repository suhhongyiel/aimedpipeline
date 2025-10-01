# backend/fastapi_mock_server.py
from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI()
jobs = {}

@app.get("/")
def read_root():
    return {"message": "Welcome to the AIMed Pipeline Mock API!"}

class JobRequest(BaseModel):
    job_type: str

@app.post("/run-job")
def run_job(req: JobRequest):
    job_id = str(len(jobs)+1)
    jobs[job_id] = {
        "status": "Queued",
        "log": "[INFO] Job registered! Waiting to run..."
    }
    return {"job_id": job_id}

@app.get("/job-status/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"status": "Unknown", "log": "No such job"}
    randval = random.random()
    if randval < 0.3:
        job["status"] = "Running"
        job["log"] = "[INFO] Job is running..."
    elif randval < 0.6:
        job["status"] = "Completed"
        job["log"] = "[SUCCESS] Job done!"
    else:
        job["status"] = "Failed"
        job["log"] = "[ERROR] Job failed. See logs."
    return job
