# app/models.py

from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
  title: str
  price: Optional[float] = None
  rating: Optional[float] = None
  review_count: Optional[int] = None
  product_url: Optional[str] = None
  image_url: Optional[str] = None
  valid: Optional[bool] = None