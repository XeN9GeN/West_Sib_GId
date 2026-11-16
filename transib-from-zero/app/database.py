from sqlalchemy import create_engine
import os
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://transsib:transsib@localhost:5434/transsib"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()
SessionLocal  = sessionmaker(bind=engine, autoflush=False, autocommit=False)