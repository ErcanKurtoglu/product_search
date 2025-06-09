# app/app.py

import streamlit as st
import requests
import json
import pandas as pd
from io import StringIO
from models import Product
from logger import configure_logging, get_logger
from search_service import filter_app_temp_products, filter_hist_temp_products, get_all_temp_products
from typing import List

configure_logging()

# Create logger object
log = get_logger(__name__)
log.info("Streamlit application is starting...")

API_URL = "http://127.0.0.1:8000"


def main():
	# Page settings
	st.set_page_config(
	page_title="Amazon Product Search",
	page_icon="🛒",
	layout="centered"
	)

	# Anchor
	st.markdown('<div id="top"></div>', unsafe_allow_html=True)

	st.title("Amazon Product Search")
	
	#Initialize session_states
	initialize_sessions()

	# --- Slidebar: Mode selection ('Live Search', 'Previous Searchs')
	mode = st.sidebar.radio("Mode", ["Live Search", "Historical Search"], key="mode", on_change=handle_mode_change)

	# Sidebar note
	st.sidebar.markdown(
		"<p style='font-size:0.85em; font-style: italic; color: gray;'>"
		"Live Search → New scraping | Historical Search → View cahed results from DB </p>",
		unsafe_allow_html=True
	)

	if mode == "Live Search":
		st.session_state.historical_order_selection = False
		run_live_search()
	else:
		st.session_state.historical_order_selection = True
		run_historical_search()
	
	# Reset Filters
	with st.sidebar:
		st.button("Reset Filter Parameters", on_click=reset_filter_parameters, type="primary")

	# Back to Top Button
	with st.sidebar:
		st.markdown("---")
		st.markdown(
			"""
			<div style="
				margin-top: 20px; 
				text-align: center;
			">
				<a href="#top"
				   onclick="document.getElementById('top').scrollIntoView({behavior:'smooth'}); return false;"
				   style="
					 display: inline-block;
					 padding: 10px 15px;
					 background-color: #0099ff;
					 color: white;
					 text-decoration: none;
					 border-radius: 5px;
					 font-weight: bold;
				   ">
					↑ Back to Top
				</a>
			</div>
			""",
			unsafe_allow_html=True,
		)


def run_live_search():
	"""
	Live Search mode:
	- Scrapes new data and saves to both app.db and temp_app.db
	- Uses SQL-based filtering on temp_app.db for performance
	"""
	# Header
	st.header("Live Search")

	# Sidebar header
	st.sidebar.header("🆕 Live Search")

	### Filters - sidebar inputs with keys and on_change callback
	st.sidebar.header("🔍 Filter&Order")

	# Filter parameters
	filter_parameters()

	# Search input
	query = st.text_input("Search product", placeholder="Ex: headphones", key="live_search_query")

	# Search Product
	if st.button("Search"):
		log.info(f"Search button clicked. Query: '{query}'")
		if not query.strip():
			st.warning("Please type a product!")
			log.warning("User attempted search with empty query.")
			return

		with st.spinner("Searching..."):
			try:
				# Scrape new data (saves to both app.dp and temp_app.db)
				log.info(f"Attempting to call API for query: '{query}' at {API_URL}/search")
				response = requests.get(f"{API_URL}/search", params={"query":query})

				if response.status_code == 200:
					products_live = [Product(**prod_dict) for prod_dict in response.json()]
					st.session_state.products_live = products_live
					st.session_state.live_query = query

					st.success(f"Found {len(products_live)} products and saved to databases")
					log.info(f"Live search successful. Found {len(products_live)} products for query: '{query}'.")
				elif response.status_code == 404:
					st.info("Product has not been found.")
					log.warning(f"API returned 404 (Not Found) for query: '{query}'.")
				elif response.status_code == 408:
					st.error("Request timed out. Please try again later.")
					log.error(f"API Timeout (408) for '{query}'.")
				elif response.status_code == 502:
					st.error("Connection error to Amazon service (502).")
					log.error(f"API 502 for '{query}'.")
				else:
					st.error(f"Unexpected error: {response.status_code}.\nPlease try a bit later.")
					log.error(f"API returned unexpected status code {response.status_code} for query: '{query}'. Response: {response.text}")
			except requests.exceptions.Timeout as e:
				st.error("API call timed out (client-side).")
				log.exception(f"Streamlit request Timeout for '{query}': {e}")
			except requests.exceptions.ConnectionError as e:
				st.error("Unable to connect to API (client-side).")
				log.exception(f"Streamlit connection error for '{query}': {e}")                
			except Exception as e:
				st.error(f"Unexpected error: {e}")
				log.exception(f"Streamlit unexpected error for: '{query}'. Exception {e}")
	
	# Download buttons
	if st.session_state.products_live:
		with st.container():
			col1, col2 = st.columns([1,1])

			with col1:
				download_condition_json = download_datas(st.session_state.products_live, "json")
			
			with col2:
				download_condition_csv = download_datas(st.session_state.products_live, "csv")
		if download_condition_json:
			log.info(f"{download_condition_json} file has been downloaded")
			st.success(f"{download_condition_json} file has been downloaded")
		if download_condition_csv:
			log.info(f"{download_condition_csv} file has been downloaded")
			st.success(f"{download_condition_csv} file has been downloaded")

	# # Display filtered results using SQL ifltering on temp_app.db
	if st.session_state.get("products_live", False): #st.session_state.get("live_search_completed", False):
		try:
			filtered_products = filter_app_temp_products(
				min_price=st.session_state.get("min_price"),
				max_price=st.session_state.get("max_price"),
				min_rating=st.session_state.get("min_rating"),
				sort_by=st.session_state.get("sort_by"),
				order = st.session_state.get("order")
			)

			query_display = st.session_state.get("live_query","")
			all_products = get_all_temp_products("live")				

			if filtered_products:
				st.markdown(f"## 🔍 Live Search Results for \"{query_display}\"")
				display_products(filtered_products)

				# Show metrics
				with st.sidebar:
					st.markdown("---")
					st.metric("Total Found", len(all_products))
					st.metric("After Filters", len(filtered_products))
			else:
				st.warning("No products match the current filter criteria")

				with st.sidebar:
					st.markdown("---")
					st.metric("Total Found", len(all_products))
					st.metric("After Filters", 0)
		except Exception as e:
			st.error(f"Error applying filters: {str(e)}")
			log.error(f"Filter error in live search: {e}")
	elif not st.session_state.error:
		st.info("No products to display. Please run a search.")
		log.info("No products to display yet (initial state or no search conducted).")
	else:
		st.info("No products to display.")
		log.info("No products found after applying filters.")


def run_historical_search():
	"""
	Historical Search mode:
	- Searches in app.db and copies results to temp_hist.db
	- Uses SQL-based filtering on hist_temp.db for performance
	"""
	# Header
	st.header("Load Products From DB")

	# Sidebar header
	st.sidebar.header("🕒 Historical Searches")

	### Filters - sidebar inputs with keys and on_change callback
	st.sidebar.header("🔍 Filter&Order")

	# Filters controls in sidebar
	filter_parameters()

	# Query input for load product which cached into DB
	query = st.text_input("Load product from DB", placeholder="Ex: headphones", key="hist_search_query")

	# Load product from DB
	if st.button("Load"):
		log.info(f"Load button clicked. Query: '{query}'")
		if not query.strip():
			st.warning("Please type a product!")
			log.warning("User attempted search with empty query.")
			return

		with st.spinner("Loading from database..."):
			try:
				log.info(f"Attempting to call API for query: '{query}' at {API_URL}/history")
				response = requests.get(f"{API_URL}/history", params={"query":query})
				# products = search_and_copy_to_hist_temp_db(query)
				
				if response.status_code == 200:
					products_hist = [Product(**prod_dict) for prod_dict in response.json()]
					st.session_state.products_hist = products_hist
					st.session_state.hist_query = query

					st.success(f"Found {len(products_hist)} products in database")
					log.info(f"Historical search successful: Found {len(products_hist)} products")
				elif response.status_code == 404:
					st.info("Product history has not been found.")
					log.warning(f"API returned 404 (Not Found) for query: '{query}'.")
					return
				else:
					st.error(f"Error accured: {response.status_code}.")
					log.error(f"API returned unexpected status code {response.status_code} for query: '{query}'. Response: {response.text}")
					return
			except requests.exceptions.RequestException as e:
				st.error(f"API connection error: {e}")
				log.exception(f"API connection error for query: '{query}'. Exception {e}")
				return

	# Download buttons
	if st.session_state.products_hist:
		with st.container():
			col1, col2 = st.columns([1,1])

			with col1:
				download_condition_json = download_datas(st.session_state.products_live, "json")
			
			with col2:
				download_condition_csv = download_datas(st.session_state.products_live, "csv")
		if download_condition_json:
			log.info(f"{download_condition_json} file has been downloaded")
			st.success(f"{download_condition_json} file has been downloaded")
		if download_condition_csv:
			log.info(f"{download_condition_csv} file has been downloaded")
			st.success(f"{download_condition_csv} file has been downloaded")

	# Display filtered results using SQL filtering on temp_hist.db
	if st.session_state.get("products_hist", False): #st.session_state.get("hist_search_completed", False):
		try:
			filtered_products = filter_hist_temp_products(
				min_price=st.session_state.get("min_price"),
				max_price=st.session_state.get("max_price"),
				min_rating=st.session_state.get("min_rating"),
				sort_by=st.session_state.get("sort_by"),
				order = st.session_state.get("order"),
				duplicate = st.session_state.get("duplicate")
			)

			query_display = st.session_state.get("hist_query","")
			all_products = get_all_temp_products("hist")

			if filtered_products:
				st.markdown(f"## 🔍 Historical Search Results for \"{query_display}\"")
				display_products(filtered_products, show_timestamp=True)

				# Show metrics
				with st.sidebar:
					st.markdown("---")
					all_products = get_all_temp_products("hist")
					st.metric("Total Found", len(all_products))
					st.metric("After Filters", len(filtered_products))
			else:
				st.warning("No products match the current filter criteria")

				with st.sidebar:
					st.markdown("---")
					st.metric("Total Found", len(all_products))
					st.metric("After Filters",0)
		except Exception as e:
			st.error(f"Error applying filters: {str(e)}")
			log.error(f"Filter error in live search: {e}")
	elif not st.session_state.error:
		st.info("No products to display. Please run a search.")
		log.info("No products to display yet (initial state or no load conducted).")
	else:
		st.info("No products to display.")
		log.info("No products found after applying filters.")

def display_products(products: List[Product], show_timestamp: bool = False):
	"""Display products in a consistent format."""
	for i, product in enumerate(products):
		with st.container():
			col1, col2 = st.columns([1,3])

			with col1:
				if product.image_url:
					try:
						st.image(product.image_url, width=150)
					except:
						st.writ("🖼️ Image not available")
				else:
					st.write("🖼️ No image ")
			
			with col2:
				st.subheader(product.title)
				
				col2_1, col2_2, col2_3 = st.columns(3)

				with col2_1:
					if product.price:
						st.metric("Price", f"${product.price:.2f}")
					else:
						st.write("Price: Not available")
				
				with col2_2:
					if product.rating:
						st.metric("Rating", f"{product.rating:.1f}/5")
					else:
						st.write("Rating: Not available")

				with col2_3:
					if product.review_count:
						st.metric("Reviews", f"{product.review_count:,}")
					else:
						st.write("Reviews: Not available")
				
				if show_timestamp and product.timestamp:
					st.caption(f"Scraped: {product.timestamp.date()}")
				
				if product.product_url:
					st.link_button("View on Amazon", product.product_url)
			st.divider()


def filter_parameters():
	"""Display filter parameter controls in sidebar."""
	# Filters parameters
	st.sidebar.number_input("Minimum Price ($)", min_value=0.0, step=1.0, key="min_price")
	
	st.sidebar.number_input("Maximum Price ($)", min_value=0.0, step=1.0,key="max_price")
	
	st.sidebar.slider("Minimum Rating", 0.0, 5.0, step=0.1, key="min_rating", )
	
	st.sidebar.selectbox(
		"Sort",
		["Default", "Price (Asc)", "Price (Desc)", "A-Z", "Z-A", "Rating (Higher)", "Review (Higher)"],
		key="sort_option"
	)

	# Map selectbox selection
	sort_map = {
		"Default": ("price", "asc"),
		"Price (Asc)": ("price", "asc"),
		"Price (Desc)": ("price", "desc"),
		"A-Z": ("title", "asc"),
		"Z-A": ("title", "desc"),
		"Rating (Higher)": ("rating", "desc"),
		"Review (Higher)": ("review_count", "desc"),
	}

	sort_by, order = sort_map.get(st.session_state.sort_option, ("price", "asc"))
	log.debug(f"Sort option set to: {sort_by}, order: {order}")

	# Order description
	st.sidebar.markdown(
		f"<p style='font-size: 0.85em; font-style: italic; color: gray;'>Default value is '{sort_by}' and '{order}'.</p>",
		unsafe_allow_html=True,
	)

	st.sidebar.toggle("Don't show 'Duplicated' products", key="duplicate", disabled=st.session_state.mode=="Live Search")

	# # Update session state
	# st.session_state.min_price = min_price if min_price > 0 else 0.0
	# st.session_state.max_price = max_price if max_price > 0 else 0.0
	# st.session_state.min_rating = min_rating if min_rating > 0 else 0.0
	st.session_state.sort_by = sort_by
	st.session_state.order = order


def download_datas(products:List[Product], data_type:str):
	"""
	Download datas as JSON or CSV format.
	
	Args:
		products: List[Product] : All products objects
		data_type: str : Datas download type. 'json', 'csv'
	"""
	try:
		if data_type == 'json':
			if st.download_button(
				label = "📥 Download All Data as JSON File",
				data = json.dumps([p.model_dump() for p in products], indent=2, ensure_ascii=False, default=str),
				file_name = "products.json",
				mime = "application/json"
			):
				return "JSON"
				
		else:
			if st.download_button(
				label = "📥 Download All Data as CSV File",
				data = pd.DataFrame([p.model_dump() for p in products]).to_csv(index=False).encode("utf-8"),
				file_name = "products.csv",
				mime = "text/csv"
			):
				return "CSV"
	except:
		return None
	

def initialize_sessions():
	"""Initialize session state variables."""
	if "min_price" not in st.session_state:
		st.session_state.min_price = 0.0
		log.debug("Session state 'min_price' initialized.")
	if "max_price" not in st.session_state:
		st.session_state.max_price = 0.0
		log.debug("Session state 'max_price' initialized.")
	if "min_rating" not in st.session_state:
		st.session_state.min_rating = 0.0
		log.debug("Session state 'min_rating' initialized.")
	if "sort_option" not in st.session_state:
		st.session_state.sort_option = "Default"
		log.debug("Session state 'sort_option' initialized.")
	if "sort_by" not in st.session_state:
		st.session_state.sort_by = "price"
		log.debug("Session state 'sort_by' initialized.")
	if "duplicate" not in st.session_state:
		st.session_state.duplicate = False
		log.debug("Session state 'duplicate' initialized.")
	if "error" not in st.session_state:
		st.session_state.error = None
		log.debug("Session state 'error' initialized.")
	if "products_live" not in st.session_state:
		st.session_state.products_live = None
		log.debug("Session state 'products_live' initialized.")
	if "products_hist" not in st.session_state:
		st.session_state.products_hist = None
		log.debug("Session state 'products_hist' initialized.")


def handle_mode_change(): # replit ile eklendi
	"""Handle mode changes and reset relevant session state."""
	# Switch sort option
	if st.session_state.mode == "Historical Search":
		st.session_state.sort_option = "A-Z"
	else:
		st.session_state.sort_option = "Default"


def reset_filter_parameters():
	st.session_state.min_price = 0.0
	st.session_state.max_price = 0.0
	st.session_state.min_rating = 0.0
	st.session_state.sort_option = "Default" if st.session_state.mode == "Live Search" else "A-Z"
	st.session_state.duplicate = False

if __name__ == "__main__":
	main()
