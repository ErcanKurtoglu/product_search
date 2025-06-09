# app/database.py

from sqlmodel import SQLModel, create_engine, Session, delete
import os
from app.logger import get_logger

log = get_logger(__name__)

# Parmanent DB (app.db)
PERMANENT_DB_FILE = "db/app.db"
PERMANENT_DB_URL = f"sqlite:///{PERMANENT_DB_FILE}"

# Live Search Temporary DB (temp_app.db)
TEMP_APP_DB_FILE = "db/temp_app.db"
TEMP_APP_DB_URL = f"sqlite:///{TEMP_APP_DB_FILE}"

# Historical Search Temporary DB (temp_hist.db)
TEMP_HIST_DB_FILE = "db/temp_hist.db"
TEMP_HIST_DB_URL = f"sqlite:///{TEMP_HIST_DB_FILE}"

# Create engines
permanent_engine = create_engine(PERMANENT_DB_URL, echo=False, connect_args={"check_same_thread":False})
temp_app_engine = create_engine(TEMP_APP_DB_URL, echo=False, connect_args={"check_same_thread":False})
temp_hist_engine = create_engine(TEMP_HIST_DB_URL, echo=False, connect_args={"check_same_thread":False})


def init_permanent_db():
  """Creates tables on permanent db (app.db)"""
  from app.db_models import SearchRecord

  # Ensure the db director exists
  os.makedirs(os.path.dirname(PERMANENT_DB_FILE), exist_ok=True)

  # Create tables for permanent database
  SQLModel.metadata.create_all(permanent_engine, tables=[SearchRecord.__table__], checkfirst=True)
  log.info("Initialized permanent database (app.db)")


def init_temp_app_db():
  """Creates tables on live search temporary db (temp_app.db)"""
  from app.db_models import TempAppSearchRecord

  # Ensure the db director exists
  os.makedirs(os.path.dirname(TEMP_APP_DB_FILE), exist_ok=True)

  # Create tables for live search temporary database
  SQLModel.metadata.create_all(temp_app_engine, tables=[TempAppSearchRecord.__table__], checkfirst=True)
  log.info("Initialized live search temporary database (temp_app.db)")


def init_temp_hist_db():
  """Creates tables on historical search temporary db (temp_hist.db)"""
  from app.db_models import TempHistSearchRecord

  # Ensure the db director exists
  os.makedirs(os.path.dirname(TEMP_HIST_DB_FILE), exist_ok=True)

  # Create tables for historical search temporary database
  SQLModel.metadata.create_all(temp_hist_engine, tables=[TempHistSearchRecord.__table__], checkfirst=True)
  log.info("Initialized historical search temporary database (temp_hist.db)")


def get_permanent_session():
  """Create new session for pemanent db (app.db)"""
  return Session(permanent_engine)


def get_temp_app_session():
  """Create new session for live search temporary db (temp_app.db)"""
  return Session(temp_app_engine)


def get_temp_hist_session():
  """Create new session for historical search temporary db (temp_hist.db)"""
  return Session(temp_hist_engine)


def _delete_session(session, table, name):
  try:
    # Delete all records from database (according to selected db)
    session.exec(delete(table))
    session.commit()
    log.info(f"Cleared all records from {name}")
  except Exception as e:
    log.error(f"Error clearing {name}: {e}")
    session.rollback()
    raise
  finally:
    session.close()


def clear_database(selection:str):
  """
  Clear all data from desired database
    
  Args:
    selection: str : 'temp_hist', 'temp_app', 'app'
  """
  from app.db_models import TempAppSearchRecord, TempHistSearchRecord, SearchRecord

  if selection=="temp_hist" and os.path.exists(TEMP_HIST_DB_FILE):
    session = get_temp_hist_session()
    _delete_session(session, TempHistSearchRecord, "historical search temp database")
  elif selection=="temp_app" and os.path.exists(TEMP_APP_DB_FILE):
    session = get_temp_app_session()
    _delete_session(session, TempAppSearchRecord, "live search temp database")
  elif selection=="app" and os.path.exists(PERMANENT_DB_FILE):
    session = get_permanent_session()
    _delete_session(session, SearchRecord, "permanent database")
  else:
    log.error("No database selected for delete")
  

