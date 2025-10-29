from sqlalchemy import Column, Integer, String, DateTime
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