from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
import datetime
from database import Base

class JobLog(Base):
    __tablename__ = 'job_logs'
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String)
    job_type = Column(String)
    status = Column(String)
    log = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CommandLog(Base):
    __tablename__ = "command_logs"
    id = Column(Integer, primary_key=True, index=True)
    command = Column(String)
    output = Column(String)
    error = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class MicaPipelineJob(Base):
    """MICA Pipeline 실행 상태 추적"""
    __tablename__ = "mica_pipeline_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)  # 예: sub-ADNI002S1155_ses-M126_proc_structural
    subject_id = Column(String)  # 예: sub-ADNI002S1155
    session_id = Column(String, nullable=True)  # 예: M126
    processes = Column(String)  # 예: proc_structural,proc_dwi
    container_name = Column(String)  # Docker 컨테이너 이름
    pid = Column(Integer, nullable=True)  # 프로세스 ID
    status = Column(String)  # processing, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 ~ 100.0
    log_file = Column(String, nullable=True)  # 로그 파일 경로
    error_log_file = Column(String, nullable=True)  # 에러 로그 파일 경로
    user = Column(String, nullable=True)  # 실행한 사용자
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)