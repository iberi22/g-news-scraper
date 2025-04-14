import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the app directory is in the path (if running tests directly)
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bs4 import BeautifulSoup
from google.cloud import firestore # Import for type hinting and SERVER_TIMESTAMP

# Import functions to test
from app.services import scraper

# --- Mock Data ---
MOCK_GOOGLE_NEWS_URL = "https://mock.news.google.com/"
MOCK_USER_AGENT = "Test User Agent 1.0"

MOCK_HTML_VALID = """
<html><head><title>Mock News</title></head><body>
<article class="MQsxIb">
    <a class="DY5qte" href="./articles/real-article-1">Real Title 1</a>
    <div class="wEwyrc">Source One</div>
    <span class="xBbh9">Snippet for article one.</span>
</article>
<article class="MQsxIb">
    <a class="DY5qte" href="http://absolute.com/article-2">Absolute Title 2</a>
    <div class="wEwyrc">Source Two</div>
    <span class="xBbh9"></span>
</article>
<article class="MQsxIb">
    <a class="DY5qte" href="./articles/real-article-3">Third Title</a>
    <div class="wEwyrc">Source One</div>
</article>
<article class="MQsxIb">
    <div class="wEwyrc">Source Four No Link</div>
</article>
</body></html>
"""
MOCK_HTML_NO_ARTICLES = "<html><body>No articles here</body></html>"
MOCK_HTML_INVALID_STRUCTURE = "<html><body><div><a class='wrong'></div></body></html>"

# --- Tests for scrape_google_news_page ---

@patch('app.services.scraper.requests.get')
def test_scrape_google_news_page_success(mock_get):
    """Test successful scraping of a page."""
    # Configure the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = MOCK_HTML_VALID
    mock_response.raise_for_status.return_value = None # No exception on 200
    mock_get.return_value = mock_response

    soup = scraper.scrape_google_news_page(MOCK_GOOGLE_NEWS_URL, MOCK_USER_AGENT)

    assert soup is not None
    assert soup.title.string == "Mock News"
    mock_get.assert_called_once_with(
        MOCK_GOOGLE_NEWS_URL,
        headers={"User-Agent": MOCK_USER_AGENT},
        timeout=15
    )

@patch('app.services.scraper.requests.get')
def test_scrape_google_news_page_http_error(mock_get):
    """Test handling of HTTP errors during scraping."""
    # Configure the mock response to raise an exception
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("HTTP Error")
    mock_get.return_value = mock_response

    soup = scraper.scrape_google_news_page(MOCK_GOOGLE_NEWS_URL, MOCK_USER_AGENT)

    assert soup is None
    mock_get.assert_called_once()

@patch('app.services.scraper.requests.get')
def test_scrape_google_news_page_other_exception(mock_get):
    """Test handling of non-HTTP errors during scraping (e.g., parsing)."""
    # Configure the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<htmlinvalid" # Malformed HTML
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    # Mock BeautifulSoup to raise an error during parsing
    with patch('app.services.scraper.BeautifulSoup', side_effect=Exception("Parsing Error")):
        soup = scraper.scrape_google_news_page(MOCK_GOOGLE_NEWS_URL, MOCK_USER_AGENT)
        assert soup is None
    mock_get.assert_called_once()

# --- Tests for extract_articles_from_soup ---
# We need to patch app.config used within the function

# Mock config values (replace with actual expected values)
MOCK_CONFIG = {
    'SCRAPER_ARTICLE_CONTAINER_SELECTOR': 'article.MQsxIb',
    'SCRAPER_TITLE_SELECTOR': 'a.DY5qte',
    'SCRAPER_LINK_SELECTOR': 'a.DY5qte',
    'SCRAPER_SOURCE_SELECTOR': 'div.wEwyrc',
    'SCRAPER_SNIPPET_SELECTOR': 'span.xBbh9',
}

@patch('app.services.scraper.app.config', MOCK_CONFIG)
def test_extract_articles_from_soup_valid():
    """Test extracting articles from valid HTML using config selectors."""
    soup = BeautifulSoup(MOCK_HTML_VALID, 'html.parser')
    articles = scraper.extract_articles_from_soup(soup, MOCK_GOOGLE_NEWS_URL)

    assert len(articles) == 3 # Should skip the one missing a link
    assert articles[0]['title'] == "Real Title 1"
    assert articles[0]['article_url'] == "https://mock.news.google.com/articles/real-article-1" # Resolved URL
    assert articles[0]['source_name'] == "Source One"
    assert articles[0]['snippet'] == "Snippet for article one."
    assert articles[1]['title'] == "Absolute Title 2"
    assert articles[1]['article_url'] == "http://absolute.com/article-2" # Absolute URL
    assert articles[1]['source_name'] == "Source Two"
    assert articles[1]['snippet'] == "" # Empty snippet tag
    assert articles[2]['title'] == "Third Title"
    assert articles[2]['article_url'] == "https://mock.news.google.com/articles/real-article-3" # Resolved URL
    assert articles[2]['source_name'] == "Source One"
    assert articles[2]['snippet'] is None # No snippet tag

@patch('app.services.scraper.app.config', MOCK_CONFIG)
def test_extract_articles_from_soup_no_articles_found():
    """Test extraction when the container selector finds nothing."""
    soup = BeautifulSoup(MOCK_HTML_NO_ARTICLES, 'html.parser')
    articles = scraper.extract_articles_from_soup(soup, MOCK_GOOGLE_NEWS_URL)
    assert len(articles) == 0

@patch('app.services.scraper.app.config', MOCK_CONFIG)
def test_extract_articles_from_soup_invalid_structure():
    """Test extraction with HTML that doesn't match inner selectors."""
    soup = BeautifulSoup(MOCK_HTML_INVALID_STRUCTURE, 'html.parser')
    # Need a container to find first
    mock_config_wrong_inner = MOCK_CONFIG.copy()
    mock_config_wrong_inner['SCRAPER_ARTICLE_CONTAINER_SELECTOR'] = 'div'
    with patch('app.services.scraper.app.config', mock_config_wrong_inner):
        articles = scraper.extract_articles_from_soup(soup, MOCK_GOOGLE_NEWS_URL)
        assert len(articles) == 0 # Inner selectors won't match

def test_extract_articles_from_soup_no_soup():
     """Test passing None as soup object."""
     articles = scraper.extract_articles_from_soup(None, MOCK_GOOGLE_NEWS_URL)
     assert articles == []

# --- Tests for Firestore Interaction (check_article_exists, save_new_article) ---
# These require mocking the Firestore client (`db`)

@pytest.fixture
def mock_db():
    """Fixture to provide a mocked Firestore client."""
    mock_db_client = MagicMock(spec=firestore.Client)
    mock_collection = MagicMock(spec=firestore.CollectionReference)
    mock_doc_ref = MagicMock(spec=firestore.DocumentReference)
    mock_doc_snapshot = MagicMock(spec=firestore.DocumentSnapshot)

    mock_db_client.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = mock_doc_snapshot
    # Default: document exists
    mock_doc_snapshot.exists = True

    return mock_db_client, mock_collection, mock_doc_ref, mock_doc_snapshot

# Test check_article_exists
def test_check_article_exists_true(mock_db):
    mock_db_client, _, _, mock_doc_snapshot = mock_db
    mock_doc_snapshot.exists = True
    exists = scraper.check_article_exists(mock_db_client, "test_coll", "doc1")
    assert exists is True
    mock_db_client.collection.assert_called_with("test_coll")
    mock_db_client.collection().document.assert_called_with("doc1")
    mock_db_client.collection().document().get.assert_called_once()

def test_check_article_exists_false(mock_db):
    mock_db_client, _, _, mock_doc_snapshot = mock_db
    mock_doc_snapshot.exists = False
    exists = scraper.check_article_exists(mock_db_client, "test_coll", "doc1")
    assert exists is False

def test_check_article_exists_db_error(mock_db):
    mock_db_client, _, mock_doc_ref, _ = mock_db
    mock_doc_ref.get.side_effect = Exception("Firestore Error")
    exists = scraper.check_article_exists(mock_db_client, "test_coll", "doc1")
    assert exists is True # Should default to True on error

# Test save_new_article
def test_save_new_article_success(mock_db):
    mock_db_client, _, mock_doc_ref, _ = mock_db
    article_data = {"title": "Test", "url": "test.com"}
    success = scraper.save_new_article(mock_db_client, "test_coll", "doc1", article_data.copy())

    assert success is True
    mock_db_client.collection.assert_called_with("test_coll")
    mock_db_client.collection().document.assert_called_with("doc1")
    # Check that data passed to set includes scraped_at timestamp placeholder
    args, kwargs = mock_doc_ref.set.call_args
    assert args[0]['title'] == "Test"
    assert 'scraped_at' in args[0]
    # assert args[0]['scraped_at'] == firestore.SERVER_TIMESTAMP # Direct comparison might not work
    assert isinstance(args[0]['scraped_at'], firestore.SERVER_TIMESTAMP.__class__)

def test_save_new_article_db_error(mock_db):
    mock_db_client, _, mock_doc_ref, _ = mock_db
    mock_doc_ref.set.side_effect = Exception("Firestore Error")
    article_data = {"title": "Test", "url": "test.com"}
    success = scraper.save_new_article(mock_db_client, "test_coll", "doc1", article_data)

    assert success is False
