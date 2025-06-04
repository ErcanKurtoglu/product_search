# /run.py

import subprocess
import threading
import time
import webbrowser
import logging

def run_fastapi():
  subprocess.run(["uvicorn", "app.main:app", "--reload"])

def run_streamlit():
  time.sleep(2)
  subprocess.run(["streamlit", "run", "app/app.py"])

def open_browser():
  time.sleep(1)
  webbrowser.open("http://localhost:8501")

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