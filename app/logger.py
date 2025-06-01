# app/logger.py

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import json
from datetime import datetime, timezone


# Custom JSON Formatter
class JsonFormatter(logging.Formatter):
  def format(self, record):
    log_record = {
      "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
      "level": record.levelname,
      "logger": record.name,
      "message": record.getMessage(),
      "file": record.pathname,
      "line": record.lineno,
      "function": record.funcName
    }

    if record.exc_info:
      log_record["exception"] = self.formatException(record.exc_info)
    
    return json.dumps(log_record)

# # Log format
# log_formatter = logging.Formatter(
#   "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s", "%Y-%m-%d %H:%M:%S"
# )


json_formatter = JsonFormatter()

def configure_logging():
  ENV = os.getenv("APP_ENV", "development")

  # Check logs files whether or not exist
  LOG_DIR = "logs"
  APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")
  TEST_LOG_FILE = os.path.join(LOG_DIR, "test.log")

  if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

  # Root logger
  logger = logging.getLogger()
  if ENV == "testing" or ENV == "development":
      logger.setLevel(logging.DEBUG)
  else: # Bu durumda ENV == "production"
      logger.setLevel(logging.INFO)

  # Clear previous handler
  if logger.hasHandlers():
    logger.handlers.clear()

  # --- Console (stdout) logger ---
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setFormatter(json_formatter)
  console_handler.setLevel(logging.ERROR) # stdout ERROR messages
  logger.addHandler(console_handler)


  # File logging for testing stage test.log, others app.log
  if ENV == "testing":
      file_handler = RotatingFileHandler(TEST_LOG_FILE, maxBytes=1*1024*1024, backupCount=1, encoding="utf-8")
      file_handler.setFormatter(json_formatter)
      file_handler.setLevel(logging.DEBUG)
      logger.addHandler(file_handler)
  else: # File logging for prod and develop stage
      file_handler = RotatingFileHandler(APP_LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
      file_handler.setFormatter(json_formatter)
      file_handler.setLevel(logging.INFO)
      logger.addHandler(file_handler)


# For get application logger's 
def get_logger(name):
    """
    Returns a logger object with specific name.
    Before call this function configure_logging() must be called.
    """
    return logging.getLogger(name)