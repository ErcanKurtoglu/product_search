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
from app.database import init_permanent_db, init_temp_app_db, init_temp_hist_db
import app.exceptions as ex
from app.search_service import search_and_copy_to_hist_temp_db, clear_database

from app.logger import configure_logging, get_logger
configure_logging()

log = get_logger(__name__)
log.info("FastAPI application is starting...")

@asynccontextmanager
async def lifespan(app:FastAPI):
  # Application startup
  init_permanent_db()
  init_temp_app_db()
  init_temp_hist_db()

  # Clear temp databases
  clear_database("temp_app")
  clear_database("temp_app")

  yield
  # If need can be added here for shutdown


app = FastAPI(title="Smart Web Scraper",
              lifespan=lifespan,
              description="A dynamic web scraper API for collecting and comparing e-commerce product data from Amazon with dual database system.",
              version="1.1.0")


@app.get("/search", response_model=List[Product])
def search_products(
  query: str = Query(..., description="Search term for products"),
  max_pages: int = Query(1, description="Maximum number of pages to scrape (1-10)", ge=1, le=10)
  ):
  
  """
  Scrape Amazon for products based on the given search query and return sorted results.
  Products are automatically saved to the permanent database (app.db) and temp_app.db.
  Suppoerts pagination with configurable page count (1-10 pages).
  """
  log.info(f"/search endpoint called with query='{query}' and max_pages={max_pages}")
  try:
    products = scrape_amazon_products(query, max_pages)
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
  except ex.ScraperParsingError as e:
    log.error(f"[API] ParsingError for query '{query}': {e}")
    raise HTTPException(status_code=500, detail=f"Parsing error: {e}")
  except Exception as e:
    log.error(f"[API] Unexpected error for query '{query}'. {e}")
    raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
  
  if not products:
    raise HTTPException(status_code=404, detail= "No products found for the given query.")
  
  return products


@app.get("/history", response_model=List[Product])
def get_records_for_query(
  query: str = Query(..., description="Search in database")
  ) -> List[Product]:
  """
  Returns List[Product] rows from the permanent database (app.db) for the given 'query' text.
  Order feature can be selected dinamicly.
  """

  try:
    products = search_and_copy_to_hist_temp_db(query)
  except Exception as e:
    log.error(f"[API] Search error: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Database transaction error: {e}")
  if not products:
    raise HTTPException(status_code=404, detail=f"No records found for query '{query}'")
  return products


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
    log.error(f"Global Exeption Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

