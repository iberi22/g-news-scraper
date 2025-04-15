import os
import hashlib
from flask import Flask, request, jsonify
from google.cloud import firestore
import logging
import json
import feedparser
from datetime import datetime

# Import configuration
from config import AppConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize App and Config
app = Flask(__name__)
app.config.from_object(AppConfig)

# Initialize Firestore client - Simplified for MVP
try:
    db = firestore.Client()
    logging.info("Firestore client initialized successfully")
except Exception as e:
    logging.exception("Failed to initialize Firestore client!")
    db = None

# Default keywords for MVP
DEFAULT_KEYWORDS = [
    "android", "android development", "mobile development",
    "programming", "software development", "coding",
    "automation", "process automation", "workflow automation",
    "python", "java", "kotlin"
]

@app.route("/scrape", methods=["POST"])
def scrape_multiple_urls():
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        user_id = data.get('user_id')
        page = data.get('page', 1)
        results_per_page = data.get('results_per_page', 5)

        if not isinstance(urls, list):
            return jsonify({"error": "URLs must be a list."}), 400
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400

        # Simplified user config for MVP
        keywords = DEFAULT_KEYWORDS

        all_articles = []
        total_filtered = 0

        for url in urls:
            try:
                feed = feedparser.parse(url)
                if feed.bozo == 1:
                    logging.error(f"Error parsing RSS feed {url}: {feed.bozo_exception}")
                    continue

                entries = feed.entries
                filtered_entries = []

                for entry in entries:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    content = f"{title} {summary}".lower()

                    if any(keyword.lower() in content for keyword in keywords):
                        filtered_entries.append(entry)

                total_filtered += len(filtered_entries)

                # Apply pagination
                start_index = (page - 1) * results_per_page
                end_index = start_index + results_per_page
                paginated_entries = filtered_entries[start_index:end_index]

                for entry in paginated_entries:
                    article_data = {
                        'title': entry.get('title'),
                        'link': entry.get('link'),
                        'summary': entry.get('summary', ''),
                        'published': entry.get('published', ''),
                        'scraped_at': datetime.utcnow().isoformat(),
                        'source_url': url
                    }

                    # Store in Firestore if client is available
                    if db:
                        try:
                            # Use article link as document ID to avoid duplicates
                            doc_ref = db.collection('google_news_articles').document(
                                hashlib.md5(article_data['link'].encode()).hexdigest()
                            )
                            doc_ref.set(article_data, merge=True)
                        except Exception as e:
                            logging.error(f"Error storing article in Firestore: {e}")

                    all_articles.append(article_data)

            except Exception as e:
                logging.error(f"Error processing RSS feed {url}: {e}", exc_info=True)

        return jsonify({
            "articles": all_articles,
            "metadata": {
                "filtered_with": keywords,
                "page": page,
                "results_per_page": results_per_page,
                "total_filtered": total_filtered,
                "returned_results": len(all_articles)
            }
        }), 200

    except Exception as e:
        logging.exception(f"Error processing scrape request: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/")
def hello_world():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "firestore_connected": db is not None
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug_mode = app.config.get('DEBUG', False)
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
