# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app, scrape_amazon_products
from app.models import Product
import app.main as main_module
from app.scraper import scraping_for_test
import logging
# import app.logger #Importing logger configuration
from app.logger import configure_logging
configure_logging()

client = TestClient(app, raise_server_exceptions=False)
test_log = logging.getLogger("tests") # Root logger


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
  monkeypatch.setenv("APP_ENV", "testing")
  #test_log.info("Setting APP_ENV to 'testing' for this test session.")


def test_search_valid_query(monkeypatch):
  def mock_scraper(query):
    test_log.debug(f"Mock scraper called with query: {query}")
    return [
      Product(
        title= "Test Headphone",
        price= 199.99,
        rating= 4.6,
        review_count= 123,
        product_url= "http://example.com/pruduct1",
        image_url= "https://example.com/image.jpg",
        valid= True
      )      
    ]
  
  monkeypatch.setattr(main_module, "scrape_amazon_products", mock_scraper)

  response = client.get("/search", params={"query": "headphones"})
  assert response.status_code == 200
  products = response.json()
  assert isinstance(products, list)
  assert "title" in products[0]
  assert "price" in products[0]
  test_log.info("test_search_valid_query completed successfully.")


def test_search_empty_results(monkeypatch):
  def mock_scraper(query):
    test_log.debug(f"Mock scraper for empty results called with query: {query}")
    return []
  
  monkeypatch.setattr(main_module, "scrape_amazon_products", mock_scraper)

  response = client.get("/search", params={"query": "nonexistentproduct12345"})
  assert response.status_code == 404
  assert response.json()["detail"] == "No products found for the given query."
  test_log.info("test_search_empty_results completed successfully.")


def test_scraping_error(monkeypatch):
  def mock_scraper(query):
    test_log.debug(f"Mock scraper for error case raising exception for query: {query}")
    raise Exception("Scraping failed")
  monkeypatch.setattr(main_module, "scrape_amazon_products", mock_scraper)

  response = client.get("/search", params={"query":"errorcase"})
  assert response.status_code == 500
  assert "Error during scraping" in response.json()["detail"]
  test_log.info("test_scraping_error completed successfully.")


# def test_search_real_query():
#   test_log.debug("Running test_search_real_query (actual scraping).")
#   response = client.get("/search", params={"query":"headphones"})
#   assert response.status_code == 200
#   data = response.json()
#   assert isinstance(data, list)
#   assert len(data)>0
#   assert "title" in data[0]
#   assert "price" in data[0]
#   test_log.info(f"Real query found {len(data)} products.")
#   test_log.info("test_search_real_query completed successfully.")


def test_search_missing_query():
  test_log.debug("Running test_search_missing_query.")
  response = client.get("/search")
  assert response.status_code == 422 # FastAPI gives error
  test_log.info("test_search_missing_query completed successfully.")


def test_global_exception_handler():
  test_log.debug("Running test_global_exception_handler.")
  response = client.get("/raise-exception")
  assert response.status_code == 500
  assert response.json() == {"detail": "Internal Server Error"}
  test_log.info("test_global_exception_handler completed successfully.")


def test_global_exception_handler_logs(caplog):
    test_log.info("Running test_global_exception_handler_logs.")
    with caplog.at_level("ERROR"):
        response = client.get("/raise-exception")
        assert response.status_code == 500
        assert {"detail": "Internal Server Error"} == response.json()
        assert any("Unhandled exception: This is a test error." in message for message in caplog.messages)
    test_log.info("test_global_exception_handler_logs completed successfully.")


def test_parsing():
  test_log.info("Running test_parsing (actual scraping/parsing test).")
  product, status = scraping_for_test("headphones")
  assert status == 200
  test_log.debug(f"Parsed Product: Title={product.title}, Price={product.price}, Rating={product.rating}, \
                 Review={product.review_count}, Url={product.product_url[:8]}..., Image={product.image_url[:8]}...")
  test_log.info("test_parsing completed successfully.")
  
  