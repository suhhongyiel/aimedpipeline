from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 개발/테스트용 SQLite 사용
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# PostgreSQL 설정 (필요시 사용)
# SQLALCHEMY_DATABASE_URL = (
#     f"postgresql://{os.getenv('POSTGRES_USER', 'testuser')}:{os.getenv('POSTGRES_PASSWORD', 'testpw')}"
#     f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'testdb')}"
# )

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()