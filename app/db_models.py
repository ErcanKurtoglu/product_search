# app/db_models.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class BaseSearchRecord(SQLModel):
  """Base model for records with common fields"""
  # __tablename__= "specific_table_name" # Give manual table name
  __table_args__ = {"extend_existing": True}

  id: Optional[int] = Field(default=None, primary_key=True)
  query: str
  title: Optional[str] = None
  price: Optional[float] = None
  rating: Optional[float] = None
  review_count: Optional[int] = None
  product_url: Optional[str] = None
  image_url: Optional[str] = None
  valid: Optional[bool] = None
  # timestamp: datetime = Field(default_factory=datetime.utcnow)
  timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True) # Index for sorting


# Permanent Model for app.db
class SearchRecord(BaseSearchRecord, table=True):
  """Model for permanent storage in app.db"""
  __tablename__ = "searchrecord"


# Live Search Temporary Model for temp_app.db
class TempAppSearchRecord(BaseSearchRecord, table=True):
  """Model for live search temporary storage in temp_app.db"""
  __tablename__ = "temp_app_searchrecord"


# Historical Search Temporary Model for temp_hist.db
class TempHistSearchRecord(BaseSearchRecord, table=True):
  """Model for historical search temporary storage in temp_hist.db"""
  __tablename__ = "temp_hist_searchrecord"