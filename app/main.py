import os
import hashlib
from flask import Flask, request, jsonify
from google.cloud import firestore
import logging
import json
import feedparser

# Import configuration
from config import AppConfig

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


@app.route("/scrape", methods=["POST"])
def scrape_multiple_urls():
    """Scrapes news articles from an array of RSS feed URLs.

    Args:
        urls: An array of RSS feed URLs to scrape.

    Returns:
        A JSON response containing the scraped articles.
    """
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        tag_filter = data.get('tag_filter')
        page = data.get('page', 1)
        results_per_page = data.get('results_per_page', 5)

        if not isinstance(urls, list):
            return jsonify({"error": "URLs must be a list."}), 400

        all_articles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                if feed.bozo == 1:
                    logging.error(f"Error parsing RSS feed {url}: {feed.bozo_exception}")
                    continue

                entries = feed.entries
                start_index = (page - 1) * results_per_page
                end_index = start_index + results_per_page

                for entry in entries[start_index:end_index]:
                    title = entry.get('title')
                    link = entry.get('link')
                    summary = entry.get('summary', '') # Provide a default value if summary is missing

                    if not all([title, link]):
                        logging.warning(f"Skipping entry due to missing title or link in {url}")
                        continue

                    if tag_filter and tag_filter.lower() not in title.lower():
                        continue

                    all_articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary
                    })

            except Exception as e:
                logging.error(f"Error processing RSS feed {url}: {e}", exc_info=True)

        return jsonify({"articles": all_articles}), 200

    except Exception as e:
        logging.exception(f"Error processing scrape request: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# --- API Endpoints ---

@app.route("/")
def hello_world():
    """Basic health check / landing page route."""
    # Example: read a value from config
    project_id = app.config.get('GOOGLE_CLOUD_PROJECT', '[Project ID not set]')
    logging.info(f"Serving hello_world request.")
    return f"Hello World! News Scraper API is running. Project: {project_id}"

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
