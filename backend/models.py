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
