# app/db_models.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class BaseSearchRecord(SQLModel):
  # __tablename__= "specific_table_name" # Give manual table name
  __table_args__ = {"extend_existing": True}
  id: Optional[int] = Field(default=None, primary_key=True)
  query: str
  title: str
  price: Optional[float] = None
  rating: Optional[float] = None
  review_count: Optional[int] = None
  product_url: Optional[str] = None
  image_url: Optional[str] = None
  valid: Optional[bool] = None
  # timestamp: datetime = Field(default_factory=datetime.utcnow)
  timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Permanent Model
class SearchRecord(BaseSearchRecord, table=True):
  __tablename__ = "seachrecord"


# Temporary Model
class TempSearchRecord(BaseSearchRecord, table=True):
  __tablename__ = "temp_seachrecord"