# /run.py

import subprocess
import threading
import time
import webbrowser
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_fastapi():
  subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"], cwd=BASE_DIR)

def run_streamlit():
  time.sleep(2)
  subprocess.run([sys.executable, "-m", "streamlit", "run", "app/app.py", "--server.port", "5000", "--server.address", "0.0.0.0"], cwd=BASE_DIR)

def open_browser():
  time.sleep(1)
  webbrowser.open("http://localhost:5000")

if __name__ == "__main__":

  t1 = threading.Thread(target=run_fastapi)
  t2 = threading.Thread(target=run_streamlit)
  # t3 = threading.Thread(target=open_browser)

  t1.start()
  t2.start()
  # t3.start()

  t1.join()
  t2.join()
  # t3.join()