# app/app.py

import streamlit as st
import requests
from comparator import filter_products, sort_products
from models import Product
from logger import get_logger

# Create logger object
log = get_logger(__name__)

API_URL = "http://127.0.0.1:8000"

def apply_filters():
    log.debug("Applying filters...")

    # If products list empty, do not filtering
    if not st.session_state.products:
        st.session_state.filtered_products = []
        log.info("Product list is empty, skipping filtering.")
        return
    
    # Get into state filter and order parameters
    min_price = st.session_state.min_price
    if st.session_state.max_price < st.session_state.min_price:
        log.warning(f"Max price ({st.session_state.max_price}) was less than min price \
({st.session_state.min_price}). Adjusting max price to min price.")
        st.session_state.max_price = st.session_state.min_price
        max_price = st.session_state.max_price
    else:
        max_price = st.session_state.max_price
    min_rating = st.session_state.min_rating
    sort_by = st.session_state.sort_by
    order = st.session_state.order

    log.debug(f"Filter parameters: min_price='{min_price}', max_price='{max_price}', \
min_rating='{min_rating}', sort_by='{sort_by}', order='{order}'")

    # Filter
    filtered = filter_products(st.session_state.products, min_price, max_price, min_rating)
    # Order rule
    ascending = (order == "asc")
    filtered_sorted = sort_products(filtered, sort_by=sort_by, ascending=ascending)

    st.session_state.filtered_products = filtered_sorted
    log.info(f"Filters applied. Original products: {len(st.session_state.products)}, \
Filtered products: {len(st.session_state.filtered_products)}")




def main():
  st.set_page_config(
      page_title="Amazon Product Search",
      page_icon="🛒",
      layout="centered"
  )
  st.title("Amazon Product Search")

  # init session state
  if "products" not in st.session_state:
      st.session_state.products = []
      log.debug("Session state 'products' initialized.")
  if "filtered_products" not in st.session_state:
      st.session_state.filtered_products = []
      log.debug("Session state 'filtered_products' initialized.")
  if "error" not in st.session_state:
      st.session_state.error = False
      log.debug("Session state 'error' initialized.")
  if "sort_by" not in st.session_state:
      st.session_state.sort_by = "price"
      log.debug("Session state 'sort_by' initialized to 'price'.")
  if "order" not in st.session_state:
      st.session_state.order = "desc"
      log.debug("Session state 'order' initialized to 'desc'.")
  if "min_price" not in st.session_state:
      st.session_state.min_price = 0.0
      log.debug("Session state 'min_price' initialized to 0.0.")
  if "max_price" not in st.session_state:
      st.session_state.max_price = 0.0
      log.debug("Session state 'max_price' initialized to 0.0.")
  if "min_rating" not in st.session_state:
      st.session_state.min_rating = 0.0
      log.debug("Session state 'min_rating' initialized to 0.0.")

  ### Filters - sidebar inputs with keys and on_change callback
  st.sidebar.header("🔍 Filter&Sort")

  st.sidebar.number_input("Minimum Price", min_value=0.0, step=1.0, key="min_price", on_change=apply_filters)
  st.sidebar.number_input("Maximum Price", min_value=0.0, step=1.0, key="max_price", on_change=apply_filters)
  st.sidebar.slider("Minimum Star", 0.0, 5.0, step=0.1, key="min_rating", on_change=apply_filters)

  sort_option = st.sidebar.selectbox(
      "Sort",
      ["Default", "Price (Asc)", "Price (Desc)", "Star (Higher)", "Review (Higer)"],
      key="sort_option",
      on_change=apply_filters,
  )
  st.sidebar.markdown(
      "<p style='font-size: 0.85em; font-style: italic; color: gray;'>Default value is 'price' and 'desc'.</p>",
      unsafe_allow_html=True,
  )

  # Map selectbox seçimini session state'ye uygula
  sort_map = {
      "Default": ("price", "desc"),
      "Price (Asc)": ("price", "asc"),
      "Price (Desc)": ("price", "desc"),
      "Star (Higher)": ("rating", "desc"),
      "Review (Higer)": ("review_count", "desc"),
  }
  st.session_state.sort_by, st.session_state.order = sort_map.get(sort_option, ("price", "desc"))
  log.debug(f"Sort option set to: {st.session_state.sort_by}, order: {st.session_state.order}")

  # Search input
  query = st.text_input("Search product", placeholder="Ex: headphones", key="query")

  if st.button("Search"):
      log.info(f"Search button clicked. Query: '{query}'")
      if not query.strip():
          st.warning("Please type a product!")
          log.warning("User attempted search with empty query.")
          return

      with st.spinner("Searching..."):
          try:
              log.info(f"Attempting to call API for query: '{query}' at {API_URL}/search")
              response = requests.get(f"{API_URL}/search", params={"query":query})
              print(len(response.json()))

              if response.status_code == 200:
                  st.session_state.products = [Product(**prod_dict) for prod_dict in response.json()]
                  st.session_state.error = False
                  apply_filters()  # Apply filter after search
                  log.info(f"API call successful. {len(st.session_state.products)} products \
received for query: '{query}'.")
              elif response.status_code == 404:
                  st.info("Product has not been found.")
                  st.session_state.products = []
                  st.session_state.filtered_products = []
                  st.session_state.error = True
                  log.warning(f"API returned 404 (Not Found) for query: '{query}'.")
              else:
                  st.error(f"Error accured: {response.status_code}.\nTry couple minutes later again.")
                  st.session_state.error = True
                  log.error(f"API returned unexpected status code {response.status_code} \
for query: '{query}'. Response: {response.text}")
          except requests.exceptions.RequestException as e:
              st.error(f"API connection error: {e}")
              st.session_state.error = True
              log.exception(f"API connection error for query: '{query}'. Exception {e}")

  # Show products
  if st.session_state.filtered_products:
      st.markdown(
          "<div style='max-height: 600px; overflow-y: auto; padding-right: 10px;'>",
          unsafe_allow_html=True,
      )
      log.debug(f"Displaying {len(st.session_state.filtered_products)} filtered products.")
      for p in st.session_state.filtered_products:
          with st.container():
              cols = st.columns([1, 4])
              with cols[0]:
                  st.image(p.image_url, width=130)
              with cols[1]:
                  if p.price is not None:
                    shown_price = '$'+ str(p.price)
                  else:
                    shown_price = "**No price value detected. Check link.**"
                  if p.rating is not None:
                    shown_rating = p.rating
                  else:
                    shown_rating = "**No rating value detected.**"
                  if p.review_count is not None:
                    shown_review_count = p.review_count
                  else:
                    shown_review_count = "**No review value detected.**"

                  st.markdown(f"**{p.title}**")
                  st.markdown(f"💰Price: {shown_price}")
                  st.markdown(f"⭐Rating: {shown_rating}")
                  st.markdown(f"💬Review count: {shown_review_count}")
                  st.markdown(f"""🔗<a href="{p.product_url}" target="_blank">View Product</a>""", unsafe_allow_html=True)
                  st.markdown("---")
      st.markdown("</div>", unsafe_allow_html=True)
  elif not st.session_state.error:
      st.info("No products to display. Please run a search.")
      log.info("No products to display yet (initial state or no search conducted).")
  elif len(st.session_state.filtered_products) == 0:
      st.info("No products to display.")
      log.info("No products found after applying filters.")

  with st.sidebar:
      st.markdown("---")
      st.markdown(
          f"""
          <div style='background-color: transparent; padding: 10px; border-radius: 8px;'>
              <span style='font-size: 0.9em;'>Number of products:&nbsp;</span>
              <strong style='font-size: 1.1em;'>{len(st.session_state.products)}</strong>
          </div>
          """,
          unsafe_allow_html=True
      )

      st.markdown(
          f"""
          <div style='background-color: transparent; padding: 10px; border-radius: 8px;'>
              <span style='font-size: 0.9em;'>Filtered products:&nbsp;</span>
              <strong style='font-size: 1.1em;'>{len(st.session_state.filtered_products)}</strong>
          </div>
          """,
          unsafe_allow_html=True
      )
  log.debug("Sidebar product count updated.")

if __name__ == "__main__":
    main()
