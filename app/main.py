# app/main.py

from fastapi import FastAPI, Query, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import Request
from contextlib import asynccontextmanager
from sqlmodel import select

from typing import List, Optional
from app.scraper import scrape_amazon_products
from app.models import Product
from app.database import init_parmanent_db, get_permanent_session
from app.db_models import SearchRecord
import app.exceptions as ex

import logging
from app.logger import configure_logging, get_logger
configure_logging()

log = get_logger(__name__)
log.info("FastAPI application is starting...")

@asynccontextmanager
async def lifespan(app:FastAPI):
  # Application startup
  init_parmanent_db()
  yield
  # If need can be added here for shutdown


app = FastAPI(title="Smart Web Scraper",
              lifespan=lifespan,
              description="A dynamic web scraper API for collecting and comparing e-commerce product data from Amazon.",
              version="1.0.0")


@app.get("/search", response_model=List[Product])
def search_products(query: str = Query(..., description="Search term for products")):
  
  """
  Scrape Amazon for products based on the given search query and return sorted results.
  """
  log.info(f"/search endpoint called with query='{query}'")
  try:
    products = scrape_amazon_products(query)
  except ex.ScraperTimeoutError as e:
    log.error(f"[API] TimeoutError for query '{query}': {e}")
    raise HTTPException(status_code=408, detail=str(e))
  except ex.ScraperConnectionError as e:
    log.error(f"[API] ConnectionError for query '{query}':{e}")
    raise HTTPException(status_code=502, detail=str(e))
  except ex.ScraperHTTPError as e:
    log.error(f"[API] HTTPError ({e.status_code}) for query '{query}': {e.message}")
    # If 404 page not found, return 404; other HTTP errors 502
    if e.status_code == 404:
      raise HTTPException(status_code=404, detail=f"No products found (HTTP 404) for  '{query}'.")
    else:
      raise HTTPException(status_code=502, detail=f"HTTP {e.status_code}: {e.message}")
  except ex.ScraperParsinError as e:
    log.error(f"[API] ParsingError for query '{query}': {e}")
    raise HTTPException(status_code=500, detail=f"Parsing error: {e}")
  except Exception as e:
    log.error(f"[API] Unexpected error for query '{query}'. {e}")
    raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
  
  if not products:
    raise HTTPException(status_code=404, detail= "No products found for the given query.")
  
  return products


@app.get("/history", response_model=List[SearchRecord])
def get_records_for_query(
  query: str = Query(..., description="Search in database")
  ) -> List[SearchRecord]:
  """
  Returns SearchRecord rows from the DB for the given 'query' text.
  Order feature can be selected dinamicly.
  """

  session_history = get_permanent_session()
  try:
    # Foundational query
    statement = (
      select(SearchRecord)
      .where(SearchRecord.query==query)
      .order_by(SearchRecord.title.asc())
    )

    records = session_history.exec(statement).all()

    if not records:
      raise HTTPException(status_code=404, detail=f"No records found for query '{query}'")
    
    return records
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error fetching records for '{query}': {e}")
  finally:
    session_history.close()


@app.get("/")
def root():
  return {"messages": "Smart Web Scraper API - endpoints: /search?query=..., /history?query=..."}


@app.get("/raise-exception")
def raise_exception():
  raise ValueError("This is a test error.")


@app.get("/health")
def healthcheck():
  return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

