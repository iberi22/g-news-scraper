import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base Flask configuration settings."""
    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # Firestore Config
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

    # App Specific Config
    NEWS_COLLECTION = "google_news_articles"
    GOOGLE_NEWS_URL = "https://news.google.com/" # Adjust if needed (e.g., specific topic/region)
    SCRAPER_USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

    # --- Scraper CSS Selectors (CRITICAL: UPDATE THESE MANUALLY) ---
    # These selectors MUST be updated based on manual inspection of GOOGLE_NEWS_URL
    # Option 1: A single selector for the main article container
    SCRAPER_ARTICLE_CONTAINER_SELECTOR = 'article.MQsxIb' # PLACEHOLDER - Example Only!
    # Option 2: Or maybe multiple possible container selectors
    # SCRAPER_ARTICLE_CONTAINER_SELECTORS = ['article.MQsxIb', 'div.NiLAwe'] # PLACEHOLDER

    # Selectors *within* the article container (relative to the container element)
    SCRAPER_TITLE_SELECTOR = 'a.DY5qte'       # PLACEHOLDER - Example Only!
    SCRAPER_LINK_SELECTOR = 'a.DY5qte'        # PLACEHOLDER - Often the same as title
    SCRAPER_SOURCE_SELECTOR = 'div.wEwyrc'    # PLACEHOLDER - Example Only!
    SCRAPER_SNIPPET_SELECTOR = 'span.xBbh9'   # PLACEHOLDER - Example Only!
    # SCRAPER_IMAGE_SELECTOR = 'img.yhLvyb'    # PLACEHOLDER - If image needed
    # ------------------------------------------------------------------

# Use the base Config directly for NVP simplicity
AppConfig = Config()
