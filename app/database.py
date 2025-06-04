# app/database.py

from sqlmodel import SQLModel, create_engine, Session
import os

# Parmanent DB
PERMANENT_DB_FILE = "db/app.db"
PERMANENT_DB_URL = f"sqlite:///{PERMANENT_DB_FILE}"

# Temporary DB
TEMP_DB_FILE = "db/temp.db"
TEMP_DB_URL = f"sqlite:///{TEMP_DB_FILE}"

# Create engines
permanent_engine = create_engine(PERMANENT_DB_URL, echo=False, connect_args={"check_same_thread":False})
temp_engine = create_engine(TEMP_DB_URL, echo=False, connect_args={"check_same_thread":False})


def init_parmanent_db():
  from app.db_models import SearchRecord
  """Creates tables on permanent db"""
  os.makedirs(os.path.dirname(PERMANENT_DB_FILE), exist_ok=True)
  SQLModel.metadata.create_all(permanent_engine, tables=[SearchRecord.__table__])


def init_temp_db():
  from app.db_models import TempSearchRecord
  """Creates tables on temp db"""
  os.makedirs(os.path.dirname(TEMP_DB_FILE), exist_ok=True)
  SQLModel.metadata.create_all(temp_engine, tables=[TempSearchRecord.__table__])


def get_permanent_session():
  """Make new session for pemanent db"""
  return Session(permanent_engine)


def get_temp_session():
  """Make new session for temp db"""
  return Session(temp_engine)