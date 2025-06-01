# app/comparator.py

from typing import List
from models import Product
from logger import get_logger

log = get_logger(__name__)

def sort_products(products: List[Product], sort_by: str = "price", ascending: bool = False) -> List[Product]:
  """
  Compare and sort a list of products based on the selected criteria.

  Args:
    products (List[Product]): List of product objects.
    sort_by (str): Attribute to sort by ('price' or 'rating').
    descending (bool): Sort in descending order if True.

  Returns:
    List[Product]: Sorted list of products.
  """
  if sort_by=="price":
    key_func = lambda p: p.price if p.price is not None else float("inf")
  elif sort_by == "rating":
    key_func = lambda p: p.rating if p.rating is not None else 0.0
  elif sort_by == "review_count":
    key_func = lambda p: p.review_count if p.review_count is not None else 0
  else:
    raise ValueError("Invalid sort_by value. Use 'price', 'rating', or 'review_count'.")
  
  return sorted(products, key=key_func, reverse=ascending)

def filter_products(products: List[Product], min_price: float = None, max_price: float = None, min_rating: int = None) -> List[Product]:
  if min_price is not None and max_price is not None and min_rating is not None:
    if min_price==0.0 and max_price==0.0 and min_rating==0.0:
      pass
    else:
      products = [p for p in products if p.price is not None and p.price >= min_price]
      if max_price!=0.0:
        products = [p for p in products if p.price is not None and p.price <= max_price]
      products = [p for p in products if p.rating is not None and p.rating >= min_rating]
  else:
    log.error(f"Invalid filter values. None values accured.")
    raise ValueError("Invalid filter values. None values accured.")

  # if min_price is not None:
    # products = [p for p in products if p.price is not None and p.price >= min_price]
  # if max_price is not None and max_price!=0.0:
  #   products = [p for p in products if p.price is not None and p.price <= max_price]
  # if min_rating is not None:
  #   products = [p for p in products if p.rating is not None and p.rating >= min_rating]


  # if min_price is not None and max_price is not None and min_rating is not None:
  #   if min_price==0.0 and max_price==0.0 and min_rating==0.0:
  #     for p in products:
  #       products_list.append(p)
  #   else:
  #     for p in products:
  #       if p.price is not None:
  #         if p.price >= min_price and p.price <= max_price and p.rating >= min_rating:
  #           products_list.append(p)
  # else:
  #   log.error(f"Invalid filter values. None values accured.")
  #   raise ValueError("Invalid filter values. None values accured.")
  return products