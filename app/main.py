import os
import hashlib
from flask import Flask, request, jsonify
from google.cloud import firestore
import logging
import json
import feedparser
from datetime import datetime
import traceback
from werkzeug.middleware.proxy_fix import ProxyFix

# Import configuration
from config import AppConfig

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize App and Config
app = Flask(__name__)
app.config.from_object(AppConfig)

# Add ProxyFix middleware for proper header handling
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize Firestore client - With better error handling
try:
    logger.info("Initializing Firestore client...")
    db = firestore.Client()
    # Test the connection
    db.collection('google_news_articles').limit(1).get()
    logger.info("✅ Firestore client initialized and connected successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Firestore client: {str(e)}")
    logger.error(f"Stacktrace: {traceback.format_exc()}")
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
    """
    Endpoint for scraping multiple RSS feeds with detailed error handling and logging
    """
    request_id = hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:8]
    logger.info(f"[Request-{request_id}] Starting new scrape request")

    try:
        data = request.get_json()
        if not data:
            logger.error(f"[Request-{request_id}] No JSON data received in request")
            return jsonify({"error": "No JSON data provided"}), 400

        urls = data.get('urls', [])
        user_id = data.get('user_id')
        page = data.get('page', 1)
        results_per_page = data.get('results_per_page', 5)

        logger.info(f"[Request-{request_id}] Processing request for user_id: {user_id}, urls: {urls}, page: {page}")

        if not isinstance(urls, list):
            logger.error(f"[Request-{request_id}] Invalid URLs format: {type(urls)}")
            return jsonify({"error": "URLs must be a list."}), 400
        if not user_id:
            logger.error(f"[Request-{request_id}] Missing user_id")
            return jsonify({"error": "User ID is required."}), 400

        # Simplified user config for MVP
        keywords = DEFAULT_KEYWORDS
        logger.info(f"[Request-{request_id}] Using default keywords: {keywords}")

        all_articles = []
        total_filtered = 0
        errors = []

        for url in urls:
            try:
                logger.info(f"[Request-{request_id}] Processing feed URL: {url}")
                feed = feedparser.parse(url)

                if feed.bozo == 1:
                    error_msg = f"Error parsing RSS feed {url}: {feed.bozo_exception}"
                    logger.error(f"[Request-{request_id}] {error_msg}")
                    errors.append({"url": url, "error": str(feed.bozo_exception)})
                    continue

                if not feed.entries:
                    logger.warning(f"[Request-{request_id}] No entries found in feed: {url}")
                    continue

                logger.info(f"[Request-{request_id}] Found {len(feed.entries)} entries in feed")
                filtered_entries = []

                for entry in feed.entries:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    content = f"{title} {summary}".lower()

                    if any(keyword.lower() in content for keyword in keywords):
                        filtered_entries.append(entry)

                total_filtered += len(filtered_entries)
                logger.info(f"[Request-{request_id}] Filtered {len(filtered_entries)} relevant entries from {url}")

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
                            doc_ref = db.collection('google_news_articles').document(
                                hashlib.md5(article_data['link'].encode()).hexdigest()
                            )
                            doc_ref.set(article_data, merge=True)
                            logger.info(f"[Request-{request_id}] Successfully stored article: {article_data['title'][:30]}...")
                        except Exception as e:
                            error_msg = f"Error storing article in Firestore: {str(e)}"
                            logger.error(f"[Request-{request_id}] {error_msg}")
                            logger.error(f"[Request-{request_id}] Stacktrace: {traceback.format_exc()}")
                            errors.append({"type": "firestore", "error": error_msg})

                    all_articles.append(article_data)

            except Exception as e:
                error_msg = f"Error processing RSS feed {url}: {str(e)}"
                logger.error(f"[Request-{request_id}] {error_msg}")
                logger.error(f"[Request-{request_id}] Stacktrace: {traceback.format_exc()}")
                errors.append({"url": url, "error": str(e)})

        response_data = {
            "articles": all_articles,
            "metadata": {
                "request_id": request_id,
                "filtered_with": keywords,
                "page": page,
                "results_per_page": results_per_page,
                "total_filtered": total_filtered,
                "returned_results": len(all_articles),
                "errors": errors if errors else None
            }
        }

        logger.info(f"[Request-{request_id}] Request completed successfully. Found {len(all_articles)} articles")
        return jsonify(response_data), 200

    except Exception as e:
        error_msg = f"Error processing scrape request: {str(e)}"
        logger.error(f"[Request-{request_id}] {error_msg}")
        logger.error(f"[Request-{request_id}] Stacktrace: {traceback.format_exc()}")
        return jsonify({
            "error": "Internal Server Error",
            "request_id": request_id,
            "details": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route("/")
def hello_world():
    """Health check endpoint with detailed status"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "firestore": {
                "connected": db is not None,
                "test_query": None
            },
            "version": "1.0.0"
        }

        # Test Firestore connection if available
        if db:
            try:
                # Try a simple query
                db.collection('google_news_articles').limit(1).get()
                health_status["firestore"]["test_query"] = "success"
            except Exception as e:
                health_status["firestore"]["test_query"] = f"failed: {str(e)}"
                logger.error(f"Health check - Firestore test query failed: {str(e)}")

        logger.info(f"Health check completed: {json.dumps(health_status)}")
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors with JSON response"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested resource does not exist",
        "status_code": 404
    }), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors with JSON response"""
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e),
        "status_code": 500
    }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug_mode = app.config.get('DEBUG', False)
    logger.info(f"Starting server on port {port} with debug={debug_mode}")
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
