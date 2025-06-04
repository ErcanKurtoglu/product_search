# app/app.py

import streamlit as st
import requests
from comparator import filter_products, sort_products
from models import Product
from logger import configure_logging, get_logger
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
    mode = st.sidebar.radio("Mode", ["Live Search", "Previous Searches"], key="mode", on_change=handle_mode_change)

    # Sidebar note
    st.sidebar.markdown(
        "<p style='font-size:0.85em; font-style: italic; color: gray;'>"
        "Live Search → New scraping | Previous Searches → View cahed results from DB </p>",
        unsafe_allow_html=True
    )

    if mode == "Live Search":
        st.session_state.historical_order_selection = False
        run_live_search()
    else:
        st.session_state.historical_order_selection = True
        run_previous_searches()
    
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
    # Header
    st.header("Live Search")

    # Sidebar header
    st.sidebar.header("🆕 Live Search")

    ### Filters - sidebar inputs with keys and on_change callback
    st.sidebar.header("🔍 Filter&Order")

    # Filter parameters
    filter_parameters()

    # Order description
    st.sidebar.markdown(
        "<p style='font-size: 0.85em; font-style: italic; color: gray;'>Default value is 'price' and 'asc'.</p>",
        unsafe_allow_html=True,
    )

    # Search input
    query = st.text_input("Search product", placeholder="Ex: headphones", key="query")

    # Search Product
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
                elif response.status_code == 408:
                    st.error("Request timed out. Please try again later.")
                    st.session_state.error = True
                    log.error(f"API Timeout (408) for '{query}'.")
                elif response.status_code == 502:
                    st.error("Connection error to Amazon service (502).")
                    st.session_state.error =True
                    log.error(f"API 502 for '{query}'.")
                else:
                    st.error(f"Unexpected error: {response.status_code}.\nPlease try a bit later.")
                    st.session_state.error = True
                    log.error(f"API returned unexpected status code {response.status_code} \
for query: '{query}'. Response: {response.text}")
            except requests.exceptions.Timeout as e:
                st.error("API call timed out (client-side).")
                st.session_state.error = True
                log.exception(f"Streamlit request Timeout for '{query}': {e}")
            except requests.exceptions.ConnectionError as e:
                st.error("Unable to connect to API (client-side).")
                st.session_state.error = True
                log.exception(f"Streamlit connection error for '{query}': {e}")                
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.session_state.error = True
                log.exception(f"Streamlit unexpected error for: '{query}'. Exception {e}")

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

    # Product and Filtered product counts
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


def run_previous_searches():
    """
    Previous Searches mode:
    - /history/query endpoint
    """
    # Header
    st.header("Load Products From DB")

    # Sidebar header
    st.sidebar.header("🕒 Previous Searches")

    ### Filters - sidebar inputs with keys and on_change callback
    st.sidebar.header("🔍 Filter&Order")

    # Filters parameters
    filter_parameters()

    # Order description
    st.sidebar.markdown(
        "<p style='font-size: 0.85em; font-style: italic; color: gray;'>Default value is 'title' and 'asc'.</p>",
        unsafe_allow_html=True,
    )

    # Query input for load product which cached into DB
    query = st.text_input("Load product from DB", placeholder="Ex: headphones", key="query")

    # Load product from DB
    if st.button("Load"):
        log.info(f"Load button clicked. Query: '{query}'")
        if not query.strip():
            st.warning("Please type a product!")
            log.warning("User attempted search with empty query.")
            return

        with st.spinner("Loading..."):
            try:
                log.info(f"Attempting to call API for query: '{query}' at {API_URL}/search")
                hist_response = requests.get(f"{API_URL}/history", params={"query":query})

                if hist_response.status_code == 200:
                    st.session_state.hist_products = [Product(**prod_dict) for prod_dict in hist_response.json()]
                    st.session_state.error = False
                    apply_filters()  # Apply filter after search
                    log.info(f"API call successful. {len(st.session_state.hist_products)} products \
received for query: '{query}'.")
                elif hist_response.status_code == 404:
                    st.info("Product history has not been found.")
                    st.session_state.hist_products = []
                    st.session_state.hist_filtered_products = []
                    st.session_state.error = True
                    log.warning(f"API returned 404 (Not Found) for query: '{query}'.")
                else:
                    st.error(f"Error accured: {hist_response.status_code}.")
                    st.session_state.error = True
                    log.error(f"API returned unexpected status code {hist_response.status_code} \
for query: '{query}'. Response: {hist_response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"API connection error: {e}")
                st.session_state.error = True
                log.exception(f"API connection error for query: '{query}'. Exception {e}")
        
        st.markdown(f"## 📜 Previous results for \"{query}\"")

    # Show products
    if st.session_state.hist_filtered_products:
        st.markdown(
            "<div style='max-height: 600px; overflow-y: auto; padding-right: 10px;'>",
            unsafe_allow_html=True,
        )
        log.debug(f"Displaying {len(st.session_state.hist_filtered_products)} filtered products.")
        for p in st.session_state.hist_filtered_products:
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
                    st.markdown(f"🕒Scraped Date: {p.timestamp.date()}")
                    st.markdown(f"""🔗<a href="{p.product_url}" target="_blank">View Product</a>""", unsafe_allow_html=True)
                    st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

    elif not st.session_state.error:
        st.info("No previous products to display. Please run a Load.")
        log.info("No previous products to display yet (initial state or no search conducted).")
    elif len(st.session_state.hist_filtered_products) == 0:
        st.info("No previous products to display.")
        log.info("No previous products found after applying filters.")

    # Product counts
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            f"""
            <div style='background-color: transparent; padding: 10px; border-radius: 8px;'>
                <span style='font-size: 0.9em;'>Number of loaded products from DB:&nbsp;</span>
                <strong style='font-size: 1.1em;'>{len(st.session_state.hist_products)}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style='background-color: transparent; padding: 10px; border-radius: 8px;'>
                <span style='font-size: 0.9em;'>Filtered products:&nbsp;</span>
                <strong style='font-size: 1.1em;'>{len(st.session_state.hist_filtered_products)}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
    log.debug("Sidebar product count updated.")


def apply_filters():
    log.debug("Applying filters...")

    # Map selectbox selection
    sort_map = {
        "Default": ("price", "asc"),
        "Price (Asc)": ("price", "asc"),
        "Price (Desc)": ("price", "desc"),
        "A-Z": ("title", "asc"),
        "Z-A": ("title", "desc"),
        "Star (Higher)": ("rating", "desc"),
        "Review (Higer)": ("review_count", "desc"),
    }
    st.session_state.sort_by, st.session_state.order = sort_map.get(st.session_state.sort_option, ("price", "asc"))
    log.debug(f"Sort option set to: {st.session_state.sort_by}, order: {st.session_state.order}")

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

    # Weather Live or Previous products
    if st.session_state.historical_order_selection:
        # If hist_products list empty, do not filtering
        if not st.session_state.hist_products:
            st.session_state.hist_filtered_products = []
            log.info("Previous products list is empty, skipping filtering.")
            return
        
        # Filter
        hist_filtered = filter_products(st.session_state.hist_products, min_price, max_price, min_rating)
        # Order rule
        descending = (order == "desc")
        hist_filtered_sorted = sort_products(hist_filtered, sort_by=sort_by, descending=descending)

        st.session_state.hist_filtered_products = hist_filtered_sorted
        log.info(f"Filters applied to previous products. Original products: {len(st.session_state.hist_products)}, \
Filtered products: {len(st.session_state.hist_filtered_products)}")
    else:
        # If products list empty, do not filtering
        if not st.session_state.products:
            st.session_state.filtered_products = []
            log.info("Product list is empty, skipping filtering.")
            return
        
        # Filter
        filtered = filter_products(st.session_state.products, min_price, max_price, min_rating)
        # Order rule
        descending = (order == "desc")
        filtered_sorted = sort_products(filtered, sort_by=sort_by, descending=descending)

        st.session_state.filtered_products = filtered_sorted
        log.info(f"Filters applied. Original products: {len(st.session_state.products)}, \
Filtered products: {len(st.session_state.filtered_products)}")


def filter_parameters():
    # Filters parameters
    st.sidebar.number_input("Minimum Price", min_value=0.0, step=1.0, key="min_price",on_change=apply_filters)
    st.sidebar.number_input("Maximum Price", min_value=0.0, step=1.0, key="max_price", on_change=apply_filters)
    st.sidebar.slider("Minimum Star", 0.0, 5.0, step=0.1, key="min_rating", on_change=apply_filters)
    st.sidebar.selectbox(
        "Sort",
        ["Default", "Price (Asc)", "Price (Desc)", "A-Z", "Z-A", "Star (Higher)", "Review (Higer)"],
        key="sort_option",
        on_change=apply_filters,
    )


def handle_mode_change():
    if st.session_state.mode == "Previous Searches":
        st.session_state.sort_option = "A-Z"
    else:
        st.session_state.sort_option = "Default"
    

def initialize_sessions():
    # init session states
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
        st.session_state.order = "asc"
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
    if "sort_option" not in st.session_state:
        st.session_state.sort_option = "Default"
        log.debug("Session state 'sort_option' initialized to Default.")

    if "query" not in st.session_state: # Arama sorgusunu da Session State'e ekleyin
        st.session_state.query = ""
        log.debug("Session state 'query' initialized.")
    if "mode" not in st.session_state:
        st.session_state.mode = "Live Search"
        log.debug("Session state 'mode' initialized.")
    if "hist_products" not in st.session_state:
        st.session_state.hist_products = []
        log.debug("Session state 'hist_products' initialized.")
    if "hist_filtered_products" not in st.session_state:
        st.session_state.hist_filtered_products = []
        log.debug("Session state 'hist_filtered_products' initialized.")
    if "historical_order_selection" not in st.session_state:
        st.session_state.historical_order_selection = False
        log.debug("Session state 'historical_order_selection' initialized.")


if __name__ == "__main__":
    main()
