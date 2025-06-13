# app/scraper.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List
from app.models import Product
import re
import os
import time
import random
from app.logger import get_logger
from app.database import (get_permanent_session, get_temp_app_session, clear_database)
import app.exceptions as ex
from app.db_models import SearchRecord, TempAppSearchRecord

# Get the logger for this module. Its name will be 'app.scraper'.
log = get_logger(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# Get environment variable
ENV = os.getenv("APP_ENV", "development") # production, development, testing

currency_pattern = r"[$\u20AC\u00A3\u00A5\u20B9\u20BA\s\u00A0]+"

### Retry configurations
# Session object
session = requests.session()
# Retry strategy
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
# HTTP and HTTPS mount
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))


def scrape_amazon_products(query: str, max_pages: int=1) -> List[Product]:
  """
  Scrapes Amazon for products based on a given query with pagination support.
  Handles network requests, HTML parsing, and data extraction across multiple pages.

  Args:
    query (str): Search query for products
    max_pages (int): Maximum number of pages to scrape (1-10)
  
  Returns:
    List[Product]: Combined list of products from all scraped pages
  """
  log.info(f"Initiating product scraping for query: '{query}' with {max_pages} page(s)")

  all_products = list()

  for page_num in range(1, max_pages + 1):
    log.info(f"Scraping page {page_num} of {max_pages} for query: '{query}'")

    # Construct URL for specific page
    if page_num == 1:
      search_url = f"https://www.amazon.com/s?k={query.replace(" ", "+")}"
    else:
      search_url = f"https://www.amazon.com/s?k={query.replace(" ", "+")}&page={page_num}"
    log.debug(f"Constructed search URL for page {page_num}: {search_url}")

    try:
      response = session.get(search_url, headers=headers, timeout=10)
      response.raise_for_status()
      log.info(f"Successfully fetched page {page_num} for query: '{query}' (Status: {response.status_code})")
    except requests.exceptions.Timeout as e:
      log.error(f"[SCRAPE] Timeout error while fetching page {page_num} URL: {search_url}. Exception: {e}")
      if page_num == 1:
        raise ex.ScraperTimeoutError(f"Request timed out while fetching data for query '{query}' page {page_num}.")
      else:
        log.warning(f"Skipping page {page_num} due to timeout, continuing with remaining pages")
        continue
    except requests.exceptions.ConnectionError as e:
      log.error(f"[SCRAPE] Connection error while fetching page {page_num} URL: {search_url}. Exception: {e}")
      if page_num == 1:
        raise ex.ScraperConnectionError(f"Connection error for query '{query}' page {page_num}. Please check your network.")
      else:
        log.warning(f"Skipping page {page_num} due to connection error, continuing with remaining pages")
        continue
    except requests.exceptions.HTTPError as e:
      status_code = response.status_code if "response" in locals() else None
      log.error(f"[SCRAPE] HTTP error {status_code} for page {page_num} URL: {search_url}. Exception {e}")
      if page_num == 1:
        raise ex.ScraperHTTPError(status_code=status_code, message=f"Returned HTTP {status_code} for page {page_num}")
      else:
        log.warning(f"Skipping page {page_num} due to HTTP error {status_code}, continuing with remaining pages")
        continue
    except requests.exceptions.RequestException as e:
      # Catch any other request-related exceptions, including HTTPError from raise_for_status()
      log.error(f"[SCRAPE] Request failed for query: '{query}' page {page_num}. Status: {response.status_code if 'response' in locals() else 'N/A'}. Exception: {e}")
      if page_num == 1:
        # Re-raise a more generic exception for the caller
        raise ex.ScraperException(f"Generic request failure for query '{query}' page {page_num}: {e}")
      else:
        log.warning(f"Skipping page {page_num} due to request failure, continuing with remaining pages")
        continue

    # Parse the HTML content
    try:
      soup = BeautifulSoup(response.content, "html.parser")
      log.debug(f"HTML content parsed with BeautifulSoup for page {page_num}")
    except Exception as e:
      log.error(f"[SCRAPE] BeautifulSoup parsing failed for query: '{query}' page {page_num}. Exception: {e}")
      if page_num == 1:
        raise ex.ScraperParsingError(f"HTML parsing failed for query '{query}' page {page_num}: {e}")
      else:
        log.warning(f"Skipping page {page_num} due to parsing error, continuing with remaining pages")
        continue
    
    # Extract products from current page
    page_products = extract_products_from_page(soup, query, page_num)
    all_products.extend(page_products)

    log.info(f"Successfully extracted {len(page_products)} products from page {page_num}")

    # Add delay between pages
    if page_num < max_pages:
      time_sleep = random.uniform(0.8, 1.8)
      time.sleep(time_sleep)
  
  log.info(f"Completed scraping {max_pages} page(s). Total products found: {len(all_products)}")
  return save_and_return_products(all_products, query)


def extract_products_from_page(soup, query:str, page_num:int) -> List[Product]:
  """
  Extract product information from a single search results page.

  Args:
  soup: BeautifulSoup object of the parsed HTML
  query (str): Search query for logging purposes
  page_num (int): Page number for logging purposes

  Returns:
    List[Product]: List of products extracted from this page
  """

  product_list = list()

  # Select product items using a robust selector
  selector = 'div.s-main-slot div[role="listitem"]'
  results = soup.select(selector) #soup.select(".s-main-slot .s-result-item")
  if not results:
    log.warning(f"No product list items found for query: '{query}'. Selector: {selector}")
    return product_list # Returns empty list

  log.info(f"Found {len(results)} potential product items for query: '{query}'.")
  
  for idx, item in enumerate(results):
    log.debug(f"Processing product item #{idx + 1}")

    try:

      title = safe_extract(item, selector="h2 span", field_name="Title")
      link = safe_extract(item, selector="a", field_name="Link")
      price_whole = safe_extract(item, selector=".a-price .a-offscreen", field_name="Price")
      rating_elem = safe_extract(item, selector="i.a-icon-star-small span", field_name="Rating")
      review_count_elem = safe_extract(item, selector="span[data-component-type='s-client-side-analytics']", field_name="Review Count")
      image_url = safe_extract(item, selector="img.s-image", field_name="Image")
      # price_whole = item.select_one(".a-price-whole") #item.select_one(".a-price .a-offscreen") whole price
      # price_fraction = item.select_one(".a-price-fraction")


      if title and link:
        # Process Link
        url = urljoin("https://www.amazon.com", link)
        log.debug(f"Processed link: {url}")
        
        # Process Price
        price = _process_price(price_whole, idx)
        # Process Rating
        rating = _process_rating(rating_elem, idx)
        # Process Review Count
        review_count = _process_review_count(review_count_elem, idx)
        
        # Determine validity for the product
        valid = all([title, price, rating, review_count, url, image_url])
        if not valid:
            log.warning(f"Product item #{idx + 1} is missing critical data. Title: {bool(title)}, Price: {bool(price)}, Rating: {rating is not None}, Reviews: {bool(review_count)}, URL: {bool(url)}, Image: {bool(image_url)}")
            
        product = Product(
          title = title,
          price = price,
          rating = rating,
          review_count=review_count,
          product_url=url,
          image_url = image_url,
          valid = valid
        )

        product_list.append(product)
      else:
        log.warning(f"Product item #{idx + 1} has no valid title or link found. Skipping.")
        raise ex.ScraperParsingError("Missing title or link element")
    except ex.ScraperParsingError as e:
       log.warning(f"[SCRAPE] Skipped one item due to parsing error: {e}")
       continue
    except Exception as e:
       log.error(f"[SCRAPE] Unexpected error while parsing one item on page {page_num}: {e}")
       continue
      #  raise ex.ScraperParsinError(f"Unexpected parsing failure: {e}")
  
  log.info(f"Finished extracting products from page {page_num}. Found {len(product_list)} products.")
  return product_list


def save_and_return_products(all_products: List[Product], query: str) -> List[Product]:
  """
  Save all products to both permanent and temp databases, then return the products.

  Args:
    all_products (List[Product]): All products collected from pagination
    query (str): Search query

  Returns:
    List[Product]: The same list of products that were saved
  """
  # Write data to both permanent DB (app.db) and live search temp DB (temp_app.db)
  permanent_session = None
  temp_app_session = None

  try:
    # Save to permanent database
    permanent_session = get_permanent_session()

    # First clear previous data in temp app database
    clear_database(selection="temp_app")
    # Save to live search temp database for immediate filtering
    temp_app_session = get_temp_app_session()

    # Save app.db
    for p in all_products:
      record = SearchRecord(
          query=query,
          title=p.title,
          price=p.price,
          rating=p.rating,
          review_count=p.review_count,
          product_url=p.product_url,
          image_url=p.image_url,
          valid=p.valid
      )
      permanent_session.add(record)
      
      # Save temp_app.db
      record_temp = TempAppSearchRecord(
          query=query,
          title=p.title,
          price=p.price,
          rating=p.rating,
          review_count=p.review_count,
          product_url=p.product_url,
          image_url=p.image_url,
          valid=p.valid
      )
      temp_app_session.add(record_temp)

    permanent_session.commit()
    temp_app_session.commit()
    log.info(f"Successfully saved {len(all_products)} products to permanent database for query: {query}")
    log.info(f"Successfully saved {len(all_products)} products to live search temp database for query: '{query}'")

  except Exception as e:
    log.error(f"[SCRAPE] Failed to save search results to DB: {e}")
    if permanent_session:
       permanent_session.rollback()
    if temp_app_session:
       temp_app_session.rollback()
  finally:
    if permanent_session:
       permanent_session.close()
    if temp_app_session:
       temp_app_session.close()

  log.info(f"Finished scraping for query: '{query}'. Total products: {len(all_products)}")
  return all_products


def safe_extract(soup, selector, field_name):
  """
  Safely extracts text or attributes from a BeautifulSoup element.
  Logs a warning if the element or attribute is missing.
  """

  if selector is None:
    element = soup
  else:
    element = soup.select_one(selector)

  if element:
    if field_name=="Link":
      extracted_value = element.get("href")
      if not extracted_value:
        log.warning(f"[EXTRACT] Missing 'href' attribute for '{field_name}' with sekector '{selector}'.")
        return None
      log.debug(f"[EXTRACT] Successfully extracted {field_name}: '{extracted_value}' (selector: '{selector}')")
      return extracted_value
    elif field_name=="Image":
      extracted_value = element.get("src")
      if not extracted_value:
        log.warning(f"[EXTRACT] Missing 'src' attribute for '{field_name}' with selector '{selector}'.")
        return None
      log.debug(f"[EXTRACT] Successfully extracted {field_name}: '{extracted_value}' (selector: '{selector}')")
      return extracted_value
    else:
      extracted_value = element.get_text(strip=True)
      if not extracted_value:
          log.debug(f"[EXTRACT] Extracted empty text for '{field_name}' with selector '{selector}'.")
      log.debug(f"[EXTRACT] Successfully extracted {field_name}: '{extracted_value}' (selector: '{selector}')")
      return extracted_value
  else:
    # This warning is crucial for debugging selector issues
    log.warning(f"[EXTRACT] Element not found for '{field_name}' with selector '{selector}'.")
    return None


def scraping_for_test(query:str):
  """
  A simplified scraping function for testing purposes, focusing on a single product.
  Uses the session object for consistency with main scraping.
  """
  log.info(f"Initiating test scraping for query: '{query}'")
  search_url = f"https://www.amazon.com/s?k={query.replace(" ", "+")}"

  try:
    response = session.get(search_url, headers=headers, timeout=10)
    response.raise_for_status()
    log.info(f"Test scrape: Successfully fetched page (Status: {response.status_code}) for query: '{query}'.")
  except requests.exceptions.RequestException as e:
    log.error(f"[TEST SCRAPER] Failed to fetch data for test query: '{query}'. Exception: {e}")
    # Re-raising here to ensure tests catch connection issues
    raise Exception(f"Test scraping failed due to: {e}")
  
  soup = BeautifulSoup(response.content, "html.parser")
  log.debug("Test scrape: HTML content parsed.")
  
  # Select only the first item for testing
  results = soup.select_one('div.s-main-slot div[role="listitem"]')

  if not results:
    log.warning(f"[TEST SCRAPER] No product item found for test query: '{query}'")
    # Return a non-valid product if no item is found, with a status code
    return Product(valid=False, title="No product found for test"), response.status_code


  title = safe_extract(results, selector="h2 span", field_name="Title")
  link = safe_extract(results, selector="a", field_name="Link")
  price_whole = safe_extract(results, selector=".a-price .a-offscreen", field_name="Price")
  rating_elem = safe_extract(results, selector="i.a-icon-star-small span", field_name="Rating")
  review_count_elem = safe_extract(results, selector="span[data-component-type='s-client-side-analytics']", field_name="Review Count")
  image_url = safe_extract(results, selector="img.s-image", field_name="Image")
  valid = all([title, price_whole, rating_elem, review_count_elem, link, image_url])


  if title and link: 
    url = urljoin("https://www.amazon.com", link)

    # Process Price
    price = _process_price(price_whole, 1)
    # Process Rating
    rating = _process_rating(rating_elem, 1)
    # Process Review Count
    review_count = _process_review_count(review_count_elem, 1)

    # Determine validity for the product
    valid = all([title, price, rating, review_count, url, image_url])
    if not valid:
        log.warning(f"[TEST SCRAPER] Test product is missing critical data. Valid: {valid}. \
Title: {bool(title)}, Price: {price is not None}, Rating: {bool(rating)}, \
Reviews: {bool(review_count)}, URL: {bool(url)}, Image: {bool(image_url)}")

  product = Product(
    title = title,
    price = price,
    rating = rating,
    review_count= review_count,
    product_url= url,
    image_url = image_url,
    valid = valid
  )
  
  log.info(f"Test scraping finished for query: '{query}'.")
  return product, response.status_code


def _process_price(price_full_text: str, item_idx: int) -> float | None:
  """Processes price string to float, logging warnings if conversion fails."""
  if price_full_text:
    price_str = re.sub(currency_pattern, "", price_full_text)
    try:
      price = float(price_str)
      if ENV == "testing":
        log.debug(f"[TEST PROCESSOR] Processed price: {price} from {price_full_text} for item #{item_idx + 1}.")   
      else:
        log.debug(f"[PROCESSOR] Processed price: {price} from {price_full_text} for item #{item_idx + 1}.")
      return price
    except ValueError:
      if ENV == "testing":
        log.warning(f"[TEST PROCESSOR] Price '{price_str}' could not be converted to float for item #{item_idx + 1}. Original: '{price_full_text}'")
      else:
        log.warning(f"[PROCESSOR] Could not convert price '{price_str}' to float for item #{item_idx + 1}. Original: '{price_full_text}'")
      return None
  else:
    log.debug(f"[PROCESSOR] Price data missing for item #{item_idx + 1}.")
    return None
  

def _process_rating(rating_text: str, item_idx: int) -> float | None:
  """Processes rating string to float, logging warnings if conversion fails."""
  if rating_text:
    match = re.search(r"([0-5]\.?[0-9]?) out of 5 stars", rating_text)
    if match:
      try:
        rating = float(match.group(1))
        if ENV == "testing":
            log.debug(f"[TEST PROCESSOR] Processed rating: {rating} from '{rating_text}' for item #{item_idx + 1}.")
        else:
            log.debug(f"[PROCESSOR] Processed rating: {rating} from '{rating_text}' for item #{item_idx + 1}.")
        return rating
      except ValueError:
          if ENV == "testing":
              log.warning(f"[TEST PROCESSOR] Rating '{match.group(1)}' could not be converted to float for item #{item_idx + 1}. Original: '{rating_text}'")
          else:
              log.warning(f"[PROCESSOR] Could not convert rating '{match.group(1)}' to float for item #{item_idx + 1}. Original: '{rating_text}'")
          return None
    else:
        if ENV == "testing":
            log.warning(f"[TEST PROCESSOR] Rating pattern not found in '{rating_text}' for item #{item_idx + 1}.")
        else:
            log.warning(f"[PROCESSOR] Rating pattern not found in '{rating_text}' for item #{item_idx + 1}.")
        return None
  else:
    log.debug(f"[PROCESSOR] Rating data missing for item #{item_idx + 1}.")
    return None


def _process_review_count(review_count_text: str, item_idx: int) -> int | None:
  """Processes review count string to int, logging warnings if conversion fails."""
  if review_count_text:
    try:
      # Remove commas before converting to int
      review_count = int(review_count_text.replace(",",""))
      if ENV == "testing":
          log.debug(f"[TEST PROCESSOR] Processed review count: {review_count} from '{review_count_text}' for item #{item_idx + 1}.")
      else:
          log.debug(f"[PROCESSOR] Processed review count: {review_count} from '{review_count_text}' for item #{item_idx + 1}.")
      return review_count
    except ValueError:
      if ENV == "testing":
          log.warning(f"[TEST PROCESSOR] Review count '{review_count_text.replace(",", "")}' \
could not be converted to int for item #{item_idx + 1}. Original: '{review_count_text}'")
      else:
          log.warning(f"[PROCESSOR] Could not convert review count '{review_count_text.replace(",", "")}' \
to int for item #{item_idx + 1}. Original: '{review_count_text}'")
      return None
  else:
    log.debug(f"[PROCESSOR] Review count data missing for item #{item_idx + 1}.")
    return None


