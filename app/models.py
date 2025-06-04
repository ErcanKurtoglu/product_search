# app/models.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class Product(BaseModel):
  title: str
  price: Optional[float] = None
  rating: Optional[float] = None
  review_count: Optional[int] = None
  product_url: Optional[str] = None
  image_url: Optional[str] = None
  valid: Optional[bool] = None
  timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))