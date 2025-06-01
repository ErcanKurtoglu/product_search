# app/main.py

from fastapi import FastAPI, Query, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import Request

from typing import List, Optional
from app.scraper import scrape_amazon_products
from app.models import Product

import logging
from app.logger import configure_logging, get_logger
configure_logging()

log = get_logger(__name__)
log.info("FastAPI application is starting...")

app = FastAPI(title="Smart Web Scraper", 
              description="A dynamic web scraper API for collecting and comparing e-commerce product data from Amazon.",
              version="1.0.0")

@app.get("/search", response_model=List[Product])
def search_products(
  query: str = Query(..., description="Search term for products"),
  ):
  
  """
  Scrape Amazon for products based on the given search query and return sorted results.
  """
  log.info(f"/search endpoint called with query='{query}'")
  try:
    products = scrape_amazon_products(query)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error during scraping: {str(e)}")
  
  if not products:
    raise HTTPException(status_code=404, detail= "No products found for the given query.")
  
  return products

@app.get("/")
def root():
  return {"messages": "Smart Web Scraper API - /search?query=..."}


@app.get("/raise-exception")
def raise_exception():
  raise ValueError("This is a test error.")


@app.get("/health")
def healthcheck():
  return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log = logging.getLogger(__name__)
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

