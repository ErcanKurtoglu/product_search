# app/search_service.py

# Configure import path (sys.path) for conflict
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from typing import List, Optional
from sqlmodel import select
from app.db_models import SearchRecord, TempHistSearchRecord, TempAppSearchRecord
from app.database import get_permanent_session, get_temp_hist_session, get_temp_app_session, clear_database
from app.models import Product
from app.logger import get_logger

log = get_logger(__name__)

def search_and_copy_to_hist_temp_db(query:str) -> List[Product]:
  """
  Search for products in permanent database (app.db) and copy matching records to historical temp databese
(temp_hist.db).
  Clears temp_hist.db before copying new data.

  Args:
    query (str): Search term to look for in the permanent database

  Returns:
    List[Product]: List of products found and copied to historical temp database
  """
  log.info(f"Starting historical search and copy operation for query: {query}")

  # Clear historical temp database at the start of each search
  clear_database(selection="temp_hist")

  # Search in permanent database
  permanent_session = get_permanent_session()
  products = list()

  try:
    # Query permanent database for matching records
    statement = (
      select(SearchRecord)
      .where(SearchRecord.query == query)
      .order_by(SearchRecord.timestamp.desc())
    )

    records = permanent_session.exec(statement).all()
    log.info(f"Found {len(records)} records in permanent database for query: '{query}'")

    if records:
      # Copy records to historical temp database
      hist_temp_session = get_temp_hist_session()
      try:
        for record in records:
          hist_temp_record = TempHistSearchRecord(
            query=record.query,
            title=record.title,
            price=record.price,
            rating=record.rating,
            review_count=record.review_count,
            product_url=record.product_url,
            image_url=record.image_url,
            valid=record.valid,
            timestamp=record.timestamp
          )
          hist_temp_session.add(hist_temp_record)

          # Create Product object for return
          product = Product(
            title=record.title,
            price=record.price,
            rating=record.rating,
            review_count=record.review_count,
            product_url=record.product_url,
            image_url=record.image_url,
            valid=record.valid,
            timestamp=record.timestamp
          )
          products.append(product)
        
        hist_temp_session.commit()
        log.info(f"Successfully copied {len(records)} records to historical temporary database")
      
      except Exception as e:
        log.error(f"Error copying records to historical temp database: {e}")
        hist_temp_session.rollback()
        raise
      finally:
        hist_temp_session.close()
  
  except Exception as e:
    log.error(f"Error searching permanent database: {e}")
    raise
  finally:
    permanent_session.close()
  
  log.info(f"Historical search and copy operation completed. Returned {len(products)} products")
  return products


def filter_hist_temp_products(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    sort_by: Optional[str] = "price",
    order: Optional[str] = "asc",
    duplicate: Optional[bool] = False
) -> List[Product]:
  """
  Filter products in historical temp database using SQL WHERE conditions.

  Args:
    min_price (Optional[float]): Minimum price filter
    max_price (Optional[float]): Maximum price filter
    min_rating (Optional[float]): Minimum rating filter
    sort_by

  Returns:
    List[Product]: List of filtered products from temp_hist db
  """
  log.info(f"Filtering historical temp products with min_price={min_price}, max_price={max_price}, min_rating={min_rating}, sort_by={sort_by}, order={order}, duplicate={duplicate}")

  hist_temp_session = get_temp_hist_session()
  products = list()

  try:
    # Build dynamic query with filters
    statement = select(TempHistSearchRecord)

    # Apply price filters
    if min_price is not None and min_price > 0:
      statement = statement.where(TempHistSearchRecord.price >= min_price)

    if max_price is not None and max_price > 0:
      statement = statement.where(TempHistSearchRecord.price <= max_price)
    
    # Apply rating filter
    if min_rating is not None and min_rating > 0:
      statement = statement.where(TempHistSearchRecord.rating >= min_rating)  

    if sort_by not in ["price", "rating", "review_count", "title"]:
      sort_by = "price"

    if duplicate:
      statement = statement.group_by(TempHistSearchRecord.title, TempHistSearchRecord.price)
    
    # Add ordering by selected sort
    sort_attr = getattr(TempHistSearchRecord, sort_by)
    statement = statement.order_by(sort_attr.asc().nullslast() if order == "asc" else sort_attr.desc())

    # Execyte query
    records = hist_temp_session.exec(statement).all()
    log.info(f"Found {len(records)} records matching filter criteria in historical temp DB")

    # Convert to Product objects
    for record in records:
      product = Product(
        title=record.title,
        price=record.price,
        rating=record.rating,
        review_count=record.review_count,
        product_url=record.product_url,
        image_url=record.image_url,
        valid=record.valid,
        timestamp=record.timestamp
      )
      products.append(product)
  
  except Exception as e:
    log.error(f"Error filtering historical temp database: {e}")
    raise
  finally:
    hist_temp_session.close()

  log.info(f"Historical filter operation completed. Returned {len(products)} products.")
  
  return products


# No more need if get_all_temp_products() runs.
def get_all_hist_temp_products() -> List[Product]:
  """
  Get all products from historical temp database without any filters.

  Returns:
    List[Product]: All products currently in temp_hist db
  """
  log.info("Retrieving all products from historical temp database")

  hist_temp_session = get_temp_hist_session()
  products = list()

  try:
    statement = select(TempHistSearchRecord).order_by(TempHistSearchRecord.timestamp.desc())
    records = hist_temp_session.exec(statement).all()

    log.info(f"Found {len(records)} total records in historical temp database")

    # Convert to Product Objects
    for record in records:
      product = Product(
        title=record.title,
        price=record.price,
        rating=record.rating,
        review_count=record.review_count,
        product_url=record.product_url,
        image_url=record.image_url,
        valid=record.valid,
        timestamp=record.timestamp
      )
      products.append(product)
  
  except Exception as e:
    log.error(f"Error retrieving fromm historical temp datebase: {e}")
    raise
  finally:
    hist_temp_session.close()

  return products


def filter_app_temp_products(
    min_price: Optional[float] = 0.0,
    max_price: Optional[float] = 0.0,
    min_rating: Optional[float] = 0.0,
    sort_by: Optional[str] = "price",
    order: Optional[str] = "asc"
    
) -> List[Product]:
  """
  Filter products in live search temp database using SQL WHERE conditions.

  Args:
    min_price (Optional[float]): Minimum price filter
    max_price (Optional[float]): Maximum price filter
    min_rating (Optional[float]): Minimum rating filter
    sort_by

  Returns:
    List[Product]: List of filtered products from temp_app db
  """
  log.info(f"Filtering historical temp products with min_price={min_price}, max_price={max_price}, min_rating={min_rating}, sort_by={sort_by}, order={order}")

  app_temp_session = get_temp_app_session()
  products = list()

  try:
    # Build dynamic query with filters
    statement = select(TempAppSearchRecord)

    # Apply price filters
    if min_price is not None and min_price > 0:
      statement = statement.where(TempAppSearchRecord.price >= min_price)
    if max_price is not None and max_price > 0:
      statement = statement.where(TempAppSearchRecord.price <= max_price)
    
    # Apply rating filter
    if min_rating is not None and min_rating > 0:
      statement = statement.where(TempAppSearchRecord.rating >= min_rating)

    if sort_by not in ["price", "rating", "review_count", "title"]:
      sort_by = "price"

    # Add ordering by selected sort
    sort_attr = getattr(TempAppSearchRecord, sort_by)
    statement = statement.order_by(sort_attr.asc().nullslast() if order == "asc" else sort_attr.desc())

    # Execyte query
    records = app_temp_session.exec(statement).all()
    log.info(f"Found {len(records)} records matching filter criteria in historical temp DB")

    # Convert to Product objects
    for record in records:
      product = Product(
        title=record.title,
        price=record.price,
        rating=record.rating,
        review_count=record.review_count,
        product_url=record.product_url,
        image_url=record.image_url,
        valid=record.valid,
        timestamp=record.timestamp
      )
      products.append(product)
  
  except Exception as e:
    log.error(f"Error filtering historical temp database: {e}")
    raise
  finally:
    app_temp_session.close()

  log.info(f"Historical filter operation completed. Returned {len(products)} products.")
  return products


def get_all_temp_products(selection:str) -> List[Product]:
  """
  Get all products from selected temp database without any filters.

  Args:
    Selection: (live, hist)

  Returns:
    List[Product]: All products currently in selected temp db
  """
  log.info("Retrieving all products from selected temp database (live, hist)")

  table = None
  if selection == "hist":
    temp_session = get_temp_hist_session()
    table = TempHistSearchRecord
  elif selection == "live":
    temp_session = get_temp_app_session()
    table = TempAppSearchRecord
  else:
    log.error(f"Selected inappropriate database. Selected {selection}, should selected live or hist.")
    raise Exception(f"Get template database failed.")

  products = list()

  try:
    statement = select(table).order_by(table.timestamp.desc())
    records = temp_session.exec(statement).all()

    log.info(f"Found {len(records)} total records in {selection} temp database")

    # Convert to Product Objects
    for record in records:
      product = Product(
        title=record.title,
        price=record.price,
        rating=record.rating,
        review_count=record.review_count,
        product_url=record.product_url,
        image_url=record.image_url,
        valid=record.valid,
        timestamp=record.timestamp
      )
      products.append(product)
  
  except Exception as e:
    log.error(f"Error retrieving fromm historical temp datebase: {e}")
    raise
  finally:
    temp_session.close()

  return products
