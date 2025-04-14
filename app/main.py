import os
import hashlib
from flask import Flask, request, jsonify
from google.cloud import firestore
import logging

# Import configuration and services
from config import AppConfig
from services import scraper # Import the scraper service

# Configure logging (consider moving to a dedicated logging setup function)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialize App and Config ---
app = Flask(__name__)
app.config.from_object(AppConfig)

# --- Initialize Firestore client ---
# Global Firestore client instance
db = None
try:
    # Initialize client, potentially using project ID from config
    db = firestore.Client(project=app.config.get('GOOGLE_CLOUD_PROJECT'))
    # Verify connection/project ID (optional but good practice)
    logging.info(f"Firestore client initialized successfully for project: {db.project}")
except Exception as e:
    # Log critical error if DB connection fails
    logging.exception("CRITICAL: Failed to initialize Firestore client!")
    # db remains None, endpoints will check for this

# --- Constants ---
NEWS_COLLECTION = app.config.get('NEWS_COLLECTION', 'google_news_articles')
MAX_ARTICLES_LIMIT = 100 # Max articles per request for GET /news/google
DEFAULT_ARTICLES_LIMIT = 20 # Default articles per request

# --- Firestore Document ID Helper ---
def create_article_doc_id(article_url: str) -> str:
    """Creates a Firestore document ID by hashing the article URL.

    Args:
        article_url: The URL string of the article.

    Returns:
        A SHA256 hash hex digest of the URL.
    """
    return hashlib.sha256(article_url.encode('utf-8')).hexdigest()

# --- Request Verification Helper ---
def verify_scheduler_request(req) -> bool:
    """Verifies if the request likely comes from Cloud Scheduler.

    Checks for the X-CloudScheduler header.
    NOTE: For production, OIDC token verification is strongly recommended.

    Args:
        req: The Flask request object.

    Returns:
        True if the header is present and true, False otherwise.
    """
    # Basic check (suitable for NVP, enhance with OIDC later)
    is_scheduler = req.headers.get("X-CloudScheduler", "false") == "true"
    if not is_scheduler:
        logging.warning("Request verification failed: Missing or invalid X-CloudScheduler header.")
        # Consider adding OIDC check here in the future
    return is_scheduler

# --- API Endpoints ---

@app.route("/")
def hello_world():
    """Basic health check / landing page route."""
    # Example: read a value from config
    project_id = app.config.get('GOOGLE_CLOUD_PROJECT', '[Project ID not set]')
    logging.info(f"Serving hello_world request.")
    return f"Hello World! News Scraper API is running. Project: {project_id}"

@app.route("/tasks/scrape/google-news", methods=["POST"])
def handle_scrape_task():
    """Handles POST requests from Cloud Scheduler to trigger scraping.

    Verifies the request origin, calls the scraper service, processes results,
    and stores new articles in Firestore.

    Returns:
        JSON response summarizing the operation (200 OK),
        or error response (403 Forbidden, 500 Internal Server Error).
    """
    logging.info("Received POST request for /tasks/scrape/google-news")

    # 1. Verify Request Origin
    if not verify_scheduler_request(request):
        # Return 403 Forbidden if verification fails
        return jsonify({"status": "error", "message": "Unauthorized: Invalid or missing Cloud Scheduler header."}), 403

    # 2. Check Firestore Client Initialization
    if not db:
        logging.error("Cannot perform scrape task: Firestore client is not available.")
        return jsonify({"status": "error", "message": "Internal Server Error: Firestore client not initialized"}), 500

    # 3. Get Configuration
    try:
        google_news_url = app.config['GOOGLE_NEWS_URL']
        user_agent = app.config['SCRAPER_USER_AGENT']
        logging.info(f"Scraping target URL: {google_news_url}")
    except KeyError as e:
        logging.error(f"Missing critical configuration: {e}. Cannot proceed.")
        return jsonify({"status": "error", "message": f"Internal Server Error: Missing configuration '{e}'"}), 500

    # 4. Perform Scraping
    soup = scraper.scrape_google_news_page(google_news_url, user_agent)
    if soup is None:
        # Error already logged in scraper service
        return jsonify({"status": "error", "message": "Internal Server Error: Failed to scrape Google News page."}), 500

    # 5. Extract Articles
    extracted_articles = scraper.extract_articles_from_soup(soup, google_news_url)
    # Extraction errors/warnings logged in scraper service
    if not extracted_articles:
        logging.info("No articles extracted from the page.")
        # Return success, as the process completed, just found nothing new
        return jsonify({"status": "success", "message": "No articles found or extracted", "articles_processed": 0, "articles_added": 0, "articles_failed_or_skipped": 0}), 200

    # 6. Process and Store New Articles
    articles_added_count = 0
    articles_failed_count = 0
    articles_processed_count = len(extracted_articles)
    articles_existing_count = 0

    for article in extracted_articles:
        article_url = article.get('article_url')
        if not article_url:
            logging.warning("Skipping article due to missing 'article_url'.")
            articles_failed_count += 1
            continue

        try:
            # Generate Firestore Document ID
            doc_id = create_article_doc_id(article_url)

            # Check if article already exists in Firestore
            exists = scraper.check_article_exists(db, NEWS_COLLECTION, doc_id)

            if not exists:
                # Attempt to save the new article
                if scraper.save_new_article(db, NEWS_COLLECTION, doc_id, article):
                    articles_added_count += 1
                else:
                    # Error logged in save_new_article
                    articles_failed_count += 1
            else:
                articles_existing_count += 1
                logging.debug(f"Article already exists (ID: {doc_id}), skipping.")

        except Exception as e:
            # Catch unexpected errors during processing/saving an article
            logging.exception(f"Unexpected error processing article URL {article_url}: {e}")
            articles_failed_count += 1
            continue # Continue with the next article

    # 7. Log Summary and Return Response
    logging.info(
        f"Scraping task finished. Processed: {articles_processed_count}, "
        f"Added: {articles_added_count}, Existing: {articles_existing_count}, "
        f"Failed/Skipped: {articles_failed_count}"
    )
    return jsonify({
        "status": "success",
        "message": f"Scraping finished. Added {articles_added_count} new articles.",
        "articles_processed": articles_processed_count,
        "articles_added": articles_added_count,
        "articles_failed_or_skipped": articles_failed_count
    }), 200


@app.route("/news/google", methods=["GET"])
def get_google_news():
    """Retrieves latest scraped news articles from Firestore with pagination.

    Query Parameters:
        limit (int): Max number of articles to return (default 20, max 100).
        offset (int): Number of articles to skip (default 0).

    Returns:
        JSON list of articles (200 OK) or error response (400, 500).
    """
    # 1. Check Firestore Client
    if not db:
        logging.error("Cannot retrieve news: Firestore client is not available.")
        return jsonify({"status": "error", "message": "Internal Server Error: Firestore client not initialized"}), 500

    # 2. Parse and Validate Pagination Parameters
    try:
        limit_str = request.args.get('limit', str(DEFAULT_ARTICLES_LIMIT))
        offset_str = request.args.get('offset', '0')
        limit = int(limit_str)
        offset = int(offset_str)
    except ValueError:
        logging.warning(f"Invalid pagination parameters received: limit='{limit_str}', offset='{offset_str}'")
        return jsonify({"status": "error", "message": "Invalid limit or offset parameter. Must be integers."}), 400

    # Apply bounds to limit and offset
    limit = max(0, min(limit, MAX_ARTICLES_LIMIT)) # Ensure limit is between 0 and MAX
    offset = max(0, offset) # Ensure offset is non-negative

    logging.info(f"Received GET request for /news/google - Limit: {limit}, Offset: {offset}")

    # 3. Query Firestore
    articles = []
    try:
        query = db.collection(NEWS_COLLECTION).order_by(
            'scraped_at', direction=firestore.Query.DESCENDING
        )

        # Apply offset using start_after for better performance with large offsets
        if offset > 0:
            # Get the document snapshot at the offset position
            offset_docs_stream = query.limit(offset).stream()
            last_doc_at_offset = None
            # Iterate through the stream to get the last document
            for doc in offset_docs_stream:
                last_doc_at_offset = doc

            if last_doc_at_offset:
                logging.debug(f"Applying offset: starting query after doc ID {last_doc_at_offset.id}")
                query = query.start_after(last_doc_at_offset)
            else:
                # Offset is larger than the total number of documents
                logging.info(f"Requested offset {offset} is beyond the total number of articles.")
                # Return empty list, but indicate success
                return jsonify({"status": "success", "articles": [], "limit": limit, "offset": offset}), 200

        # Apply limit to the final query
        final_docs_stream = query.limit(limit).stream()

        # 4. Process Results
        for doc in final_docs_stream:
            article_data = doc.to_dict()
            article_data['id'] = doc.id # Include Firestore document ID
            # Convert Firestore timestamp to ISO 8601 string for JSON
            if 'scraped_at' in article_data and hasattr(article_data['scraped_at'], 'isoformat'):
                article_data['scraped_at'] = article_data['scraped_at'].isoformat()
            else:
                # Handle cases where timestamp might be missing or incorrect type
                article_data['scraped_at'] = None
                logging.warning(f"Article ID {doc.id} missing valid 'scraped_at' timestamp.")
            articles.append(article_data)

        logging.info(f"Successfully retrieved {len(articles)} articles from Firestore.")
        # 5. Return Success Response
        return jsonify({"status": "success", "articles": articles, "limit": limit, "offset": offset}), 200

    except Exception as e:
        # Log the full error and return a generic 500 response
        logging.exception(f"Error retrieving articles from Firestore: {e}")
        return jsonify({"status": "error", "message": "Internal Server Error: Failed to retrieve articles from database."}), 500

# --- Main Execution Entrypoint ---
if __name__ == "__main__":
    # Note: Gunicorn runs the app in production (via Dockerfile)
    # This block is primarily for local development (`python app/main.py`)
    port = int(os.environ.get("PORT", 3000))
    # Debug mode is read from AppConfig, loaded from FLASK_DEBUG env var
    debug_mode = app.config.get('DEBUG', False)
    logging.info(f"Starting Flask development server on http://0.0.0.0:{port} (Debug: {debug_mode})")
    # Host 0.0.0.0 makes it accessible externally if needed (e.g., within Docker)
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
