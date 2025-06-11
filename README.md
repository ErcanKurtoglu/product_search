# 🛍️ Amazon Smart Web Scraper API

This project is a dynamic web scraper that retrieves product data from Amazon.com based on a search query and serves it through a FastAPI-based RESTful API. It includes JSON-formatted logging and retry mechanisms for reliability.

---

## 📌 Features

- 🔍 Scrape Amazon products by keyword with pagination support
- 📦 Product details include: title, price, rating, review count, image, and product link
- ✅ Product validity check for data completeness
- 🔁 Built-in retry strategy for unstable connections
- 📄 Pagination support to scrape and return results from multiple pages
- 📄 Structured JSON logging (file + console)
- 💾 SQLite database to store results  
- 🧮 Filter and sort products by price, rating, and review count using efficient DB queries  
- ⬇️ One-click export and download of filtered results as CSV or JSON  
- ⚙️ Development & production environment modes

---

## 🧱 Technologies Used

- **FastAPI** — Modern Python web framework
- **BeautifulSoup4** — HTML parsing
- **Requests + Retry** — HTTP connection handling
- **Pydantic** — Data modeling
- **SQLite + SQLModel** — Lightweight database and ORM for data persistence and filtering
- **Logging** — Structured JSON log system
- **RotatingFileHandler** — File-based rotating logging system

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ErcanKurtoglu/product_search.git
cd product_search
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate
```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```
## ⚙️ Usage

### To Run all project via Streamlit app

```bash
python run.py
```
The application will be opened via web browser or can be opened manually `localhost:5000`

### Run the API only

```bash
uvicorn app.main:app --reload
```

### Endpoint

`GET /search?query=your_search_term`

#### Example:
```http
GET http://127.0.0.1:8000/search?query=laptop
```

#### Response

```json
[
  {
    "title": "Laptop Model XYZ",
    "price": 849.99,
    "rating": 4.5,
    "review_count": 187,
    "product_url": "https://www.amazon.com/dp/XYZ",
    "image_url": "https://m.media-amazon.com/images/I/XYZ.jpg",
    "valid": true
  },
  ...
]
```

## 🧪 Testing

### Manual Test Script:

```python
from app.scraper import scraping_for_test

product, status = scraping_for_test("laptop")
print(product)
```

## 📁 Project Structure

```graphql
product_search/
│
├── app/
│   ├── app.py              # Streamlit app
│   ├── main.py             # FastAPI app
│   ├── scraper.py          # Scraper logic
│   ├── models.py           # Pydantic models
│   ├── db_models.py        # SQLModel ORM models
│   ├── databese.py         # DB setup
│   ├── search_service.py   # Search & filtering services with DB queries
│   ├── exceptions.py       # Defined exception classes
│   └── logger.py           # JSON logger config
│
├── db/
│   ├── app.db              # All product db 
│   ├── temp_app.db         # Live search products filtered db 
│   ├── temp_hist.db        # Historical search products filtered db 
│
├── tests/
│   └── test_api.py    # App test 
├── logs/
│   └── app.log        # Rotating JSON log file (auto-generated)
│
├── requirements.txt
├── .env
├── run.py             # Project run
└── README.md
```

.env file:
```.env
# .env
APP_ENV=production
```

## 📊 Logging System

* **File:** `logs/app.log`

* **Format:** JSON

* **Fields:**

  * `timestamp`, `level`, `logger`, `message`, `file`, `line`, `function`

#### Example log entry:

```json
{
  "timestamp": "2025-05-30T14:45:01.123456Z",
  "level": "INFO",
  "logger": "api.scraper",
  "message": "Scraping started for query: 'laptop'",
  "file": "/app/api/scraper.py",
  "line": 32,
  "function": "scrape_amazon_products"
}
```


## ⚠️ Warnings

* Amazon's HTML structure changes frequently. The scraper should be kept up-to-date.

* Amazon employs bot protection mechanisms. Excessive use may result in IP bans.

* This project is for educational and personal use only. Commercial use may lead to legal issues.


## 📬 Developer Note

This project demonstrates a professional approach to dynamic data scraping, API development, and structured logging. Optional enhancements include Redis, database integration, and cron-based automation.


## 📝 License

This project is licensed under the **MIT License**.  
See the [LICENSE](./LICENSE) file for details.