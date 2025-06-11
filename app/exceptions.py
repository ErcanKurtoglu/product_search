# app/exceptions.py

class ScraperException(Exception):
  """All scraper errors"""
  pass

class ScraperTimeoutError(ScraperException):
  """Request timeout error raise"""
  pass

class ScraperConnectionError(ScraperException):
  """Connection error raise"""

class ScraperHTTPError(ScraperException):
  """HTTP statuse code 400-499 or 500-599 raise"""
  def __init__(self, status_code: int, message: str = None):
    self.status_code = status_code
    self.message = message or f"HTTP error {status_code}"
    super().__init__(self.message)

class ScraperParsingError(ScraperException):
  """HTML parse or date parsing error"""
  pass