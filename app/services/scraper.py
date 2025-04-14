import logging
import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
from urllib.parse import urljoin

# Import the Flask app instance to access config (NVP simplification)
from main import app

def scrape_google_news_page(url: str, user_agent: str) -> BeautifulSoup | None:
    """Performs an HTTP GET request and returns BeautifulSoup soup.

    Args:
        url: The URL to scrape.
        user_agent: The User-Agent string for the request.

    Returns:
        A BeautifulSoup object of the parsed HTML, or None if an error occurs.
    """
    logging.info(f"Attempting to scrape URL: {url}")
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers, timeout=15) # Increased timeout slightly
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        # Specify parser explicitly for consistency
        soup = BeautifulSoup(response.text, 'html.parser')
        logging.info(f"Successfully scraped and parsed URL: {url}")
        return soup
    except requests.exceptions.RequestException as e:
        # Catching specific requests exceptions
        logging.error(f"HTTP request failed for {url}: {e}")
        return None
    except Exception as e:
        # Catch other potential errors during parsing etc.
        logging.error(f"Error parsing HTML for {url}: {e}", exc_info=True)
        return None

def _resolve_url(base_url: str, link: str) -> str:
    """Resolves a potentially relative URL against a base URL.

    Args:
        base_url: The URL of the page where the link was found.
        link: The href value (can be relative or absolute).

    Returns:
        The absolute URL.
    """
    # urljoin handles both relative and absolute links correctly
    return urljoin(base_url, link)

def extract_articles_from_soup(soup: BeautifulSoup | None, base_url: str) -> list[dict]:
    """Extracts article data from BeautifulSoup soup using selectors from app config.

    Args:
        soup: A BeautifulSoup object, or None.
        base_url: The base URL the soup was scraped from (for resolving relative links).

    Returns:
        A list of dictionaries, each representing extracted article metadata.
        Example article dict:
        {
            "title": str,
            "article_url": str, # Resolved absolute URL
            "source_name": str,
            "snippet": str | None,
            "google_news_url": str | None # URL on Google News itself
        }
    """
    if not soup:
        logging.warning("Cannot extract articles, soup object is None.")
        return []

    articles = []
    # --- Get Selectors from Config (Ensure these are set!) ---
    # Using .get() with default to prevent KeyError if missing, though error is logged
    container_selector = app.config.get('SCRAPER_ARTICLE_CONTAINER_SELECTOR', '')
    title_selector = app.config.get('SCRAPER_TITLE_SELECTOR', '')
    link_selector = app.config.get('SCRAPER_LINK_SELECTOR', '')
    source_selector = app.config.get('SCRAPER_SOURCE_SELECTOR', '')
    snippet_selector = app.config.get('SCRAPER_SNIPPET_SELECTOR') # Optional selector

    # Check if essential selectors are configured
    if not all([container_selector, title_selector, link_selector, source_selector]):
        logging.error("Essential scraper selectors (container, title, link, source) missing in config! Update app/config.py.")
        return []
    # -------------------------------------------------------

    logging.info(f"Using article container selector: '{container_selector}'")
    article_elements = soup.select(container_selector)

    if not article_elements:
        logging.warning(f"Could not find article elements using selector '{container_selector}'. Verify selector and page structure at {base_url}")
        return []

    logging.info(f"Found {len(article_elements)} potential article elements using '{container_selector}'.")

    for i, element in enumerate(article_elements, 1):
        try:
            title_element = element.select_one(title_selector)
            link_element = element.select_one(link_selector)
            source_element = element.select_one(source_selector)
            # Snippet is optional
            snippet_element = element.select_one(snippet_selector) if snippet_selector else None

            # Extract text/attributes safely
            title = title_element.get_text(strip=True) if title_element else None
            raw_link = link_element.get('href') if link_element else None
            source_name = source_element.get_text(strip=True) if source_element else None
            snippet = snippet_element.get_text(strip=True) if snippet_element else None

            # Basic validation: Need at least title, link, and source
            if not all([title, raw_link, source_name]):
                logging.debug(f"Skipping element #{i}, missing essential data (title, link, or source). Title: '{title}', Link: '{raw_link}', Source: '{source_name}'")
                continue

            # Resolve the URL (e.g., handle relative links like ./articles/...)
            resolved_url = _resolve_url(base_url, raw_link)

            # Placeholder for differentiating original vs. Google News URL
            # For NVP, we assume the resolved URL is the one we store as both for now
            # TODO: Refine this if Google News HTML allows extracting the original source URL separately
            article_url = resolved_url
            google_news_url = resolved_url

            article_data = {
                "title": title,
                "article_url": article_url,
                "source_name": source_name,
                "snippet": snippet,
                "google_news_url": google_news_url
            }
            articles.append(article_data)
            logging.debug(f"Extracted article #{i}: {title}")

        except Exception as e:
            # Log specific element extraction error but continue with others
            logging.warning(f"Failed to process potential article element #{i}: {e}", exc_info=True)
            continue

    logging.info(f"Successfully extracted metadata for {len(articles)} articles out of {len(article_elements)} potential elements.")
    return articles

def check_article_exists(db: firestore.Client | None, collection_name: str, doc_id: str) -> bool:
    """Checks if a document with the given ID exists in Firestore.

    Args:
        db: Firestore client instance.
        collection_name: Name of the Firestore collection.
        doc_id: The document ID (hashed URL) to check.

    Returns:
        True if the document exists or if db client is None/error occurs
        (fail-safe to prevent duplicate writes), False otherwise.
    """
    if not db:
        logging.error("Firestore client not available for check_article_exists")
        return True # Fail-safe: Assume exists if DB unavailable

    doc_ref = db.collection(collection_name).document(doc_id)
    try:
        doc_snapshot = doc_ref.get()
        logging.debug(f"Checking existence for doc ID: {doc_id} - Exists: {doc_snapshot.exists}")
        return doc_snapshot.exists
    except Exception as e:
        logging.error(f"Error checking Firestore document {doc_id}: {e}", exc_info=True)
        return True # Fail-safe: Assume exists on error

def save_new_article(db: firestore.Client | None, collection_name: str, doc_id: str, article_data: dict) -> bool:
    """Saves a new article document to Firestore, adding scraped_at timestamp.

    Args:
        db: Firestore client instance.
        collection_name: Name of the Firestore collection.
        doc_id: The document ID (hashed URL) for the new article.
        article_data: Dict containing article metadata (title, url, source, etc.).

    Returns:
        True if save was successful, False otherwise.
    """
    if not db:
        logging.error(f"Firestore client not available for saving article {doc_id}")
        return False

    doc_ref = db.collection(collection_name).document(doc_id)
    try:
        # Add the server timestamp when saving
        article_data_to_save = article_data.copy()
        article_data_to_save['scraped_at'] = firestore.SERVER_TIMESTAMP

        doc_ref.set(article_data_to_save)
        logging.info(f"Saved new article ID: {doc_id} (Title: {article_data.get('title')})")
        return True
    except Exception as e:
        logging.error(f"Error saving article {doc_id} to Firestore: {e}", exc_info=True)
        return False
