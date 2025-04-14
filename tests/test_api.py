import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

# Import the client fixture from conftest
from .conftest import client # noqa: F401 (client fixture is used by pytest)

# Import the app to potentially patch things within it if needed
# from app.main import app

# --- Mock Firestore Data for API Tests ---

@pytest.fixture
def mock_firestore_query():
    """Mocks the Firestore query chain for get_google_news."""
    # Create mock documents that mimic Firestore data
    mock_doc1_data = {
        'title': 'API Test Article 1',
        'article_url': 'http://api.test/1',
        'source_name': 'API Source',
        'snippet': 'Snippet 1',
        'scraped_at': datetime(2023, 10, 27, 10, 0, 0) # Use datetime for mock
    }
    mock_doc2_data = {
        'title': 'API Test Article 2',
        'article_url': 'http://api.test/2',
        'source_name': 'API Source',
        'snippet': 'Snippet 2',
        'scraped_at': datetime(2023, 10, 27, 9, 0, 0)
    }

    mock_doc1 = MagicMock()
    mock_doc1.id = "mock_doc_id_1"
    mock_doc1.to_dict.return_value = mock_doc1_data

    mock_doc2 = MagicMock()
    mock_doc2.id = "mock_doc_id_2"
    mock_doc2.to_dict.return_value = mock_doc2_data

    # --- Mock the Query Chain --- 
    mock_db_client = MagicMock()
    mock_collection = MagicMock()
    mock_query = MagicMock()

    mock_db_client.collection.return_value = mock_collection
    mock_collection.order_by.return_value = mock_query
    # Mock the offset query part (if needed for specific tests)
    mock_offset_query = MagicMock()
    mock_collection.limit.return_value = mock_offset_query # Mock limit() called for offset calculation
    mock_offset_query.stream.return_value = [mock_doc1] # Simulate finding one doc at offset
    # Mock the start_after part
    mock_query.start_after.return_value = mock_query # Assume start_after returns the query
    # Mock the final limit and stream
    mock_query.limit.return_value = mock_query
    # Default stream result:
    mock_query.stream.return_value = [mock_doc1, mock_doc2]
    # -----------------------------

    # Patch the 'db' instance used within the main app
    with patch('app.main.db', mock_db_client):
        yield mock_db_client, mock_query # Yield the parts needed for assertions

# --- Tests for GET /news/google ---

def test_get_google_news_success(client, mock_firestore_query): # noqa: F811 (redefinition is pattern)
    """Test successful retrieval of news articles."""
    mock_db_client, mock_query = mock_firestore_query

    response = client.get('/news/google?limit=10&offset=0')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['status'] == 'success'
    assert len(data['articles']) == 2
    assert data['limit'] == 10
    assert data['offset'] == 0
    assert data['articles'][0]['id'] == 'mock_doc_id_1'
    assert data['articles'][0]['title'] == 'API Test Article 1'
    assert isinstance(data['articles'][0]['scraped_at'], str)
    assert data['articles'][1]['id'] == 'mock_doc_id_2'
    mock_db_client.collection.assert_called_with('google_news_articles')
    mock_collection = mock_db_client.collection()
    mock_collection.order_by.assert_called_once()
    mock_query.limit.assert_called_with(10)
    mock_query.stream.assert_called_once()

def test_get_google_news_pagination(client, mock_firestore_query): # noqa: F811
    """Test pagination logic (limit, offset -> start_after)."""
    mock_db_client, mock_query = mock_firestore_query
    mock_doc3 = MagicMock()
    mock_doc3.id = "mock_doc_id_3"
    mock_doc3.to_dict.return_value = { 'title': 'Doc 3', 'scraped_at': datetime.now() }
    mock_query.limit.return_value.stream.return_value = [mock_doc3]

    response = client.get('/news/google?limit=5&offset=1')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert len(data['articles']) == 1
    assert data['articles'][0]['id'] == 'mock_doc_id_3'
    assert data['limit'] == 5
    assert data['offset'] == 1
    mock_query.start_after.assert_called_once()
    mock_query.limit.assert_called_with(5)
    mock_db_client.collection().limit.assert_called_with(1)

def test_get_google_news_invalid_params(client, mock_firestore_query): # noqa: F811
    """Test response when invalid pagination parameters are provided."""
    response = client.get('/news/google?limit=-5&offset=abc')
    data = json.loads(response.data)
    assert response.status_code == 400
    assert data['status'] == 'error'

def test_get_google_news_firestore_error(client, mock_firestore_query): # noqa: F811
    """Test response when Firestore query fails."""
    mock_db_client, mock_query = mock_firestore_query
    mock_query.stream.side_effect = Exception("Firestore is down")
    response = client.get('/news/google')
    data = json.loads(response.data)
    assert response.status_code == 500
    assert data['status'] == 'error'

@patch('app.main.db', None)
def test_get_google_news_db_not_initialized(client): # noqa: F811
    """Test response when Firestore client wasn't initialized."""
    response = client.get('/news/google')
    data = json.loads(response.data)
    assert response.status_code == 500
    assert data['status'] == 'error'

# --- Tests for POST /tasks/scrape/google-news ---

# Fixture to mock the entire scraper service module
@pytest.fixture
def mock_scraper_service():
    """Mocks all functions within the app.services.scraper module."""
    with patch('app.main.scraper') as mock_scraper:
        # Default mock behaviors (can be overridden in tests)
        mock_scraper.scrape_google_news_page.return_value = BeautifulSoup("<html></html>", 'html.parser') # Return empty soup
        mock_scraper.extract_articles_from_soup.return_value = [
            {'article_url': 'http://test.com/new1'},
            {'article_url': 'http://test.com/exists'},
        ]
        # Simulate one existing article
        mock_scraper.check_article_exists.side_effect = lambda db, coll, doc_id: doc_id == scraper.create_article_doc_id('http://test.com/exists')
        mock_scraper.save_new_article.return_value = True
        yield mock_scraper

def test_scrape_task_success(client, mock_scraper_service): # noqa: F811
    """Test successful execution of the scrape task endpoint."""
    headers = {'X-CloudScheduler': 'true'}
    response = client.post('/tasks/scrape/google-news', headers=headers)
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['status'] == 'success'
    assert data['articles_processed'] == 2
    assert data['articles_added'] == 1 # Only the new one
    assert data['articles_failed_or_skipped'] == 0

    # Verify scraper functions were called
    mock_scraper_service.scrape_google_news_page.assert_called_once()
    mock_scraper_service.extract_articles_from_soup.assert_called_once()
    assert mock_scraper_service.check_article_exists.call_count == 2
    mock_scraper_service.save_new_article.assert_called_once()
    # Check that save was called with the *new* article data
    call_args, _ = mock_scraper_service.save_new_article.call_args
    assert call_args[3]['article_url'] == 'http://test.com/new1'

def test_scrape_task_unauthorized(client, mock_scraper_service): # noqa: F811
    """Test endpoint access without the required header."""
    response = client.post('/tasks/scrape/google-news') # No headers
    data = json.loads(response.data)

    assert response.status_code == 403 # Forbidden
    assert data['status'] == 'error'
    assert data['message'] == 'Unauthorized'
    mock_scraper_service.scrape_google_news_page.assert_not_called()

def test_scrape_task_scrape_fails(client, mock_scraper_service): # noqa: F811
    """Test endpoint when the initial page scrape fails."""
    mock_scraper_service.scrape_google_news_page.return_value = None # Simulate scrape failure
    headers = {'X-CloudScheduler': 'true'}
    response = client.post('/tasks/scrape/google-news', headers=headers)
    data = json.loads(response.data)

    assert response.status_code == 500
    assert data['status'] == 'error'
    assert data['message'] == 'Failed to scrape Google News'
    mock_scraper_service.extract_articles_from_soup.assert_not_called()

def test_scrape_task_extraction_fails(client, mock_scraper_service): # noqa: F811
    """Test endpoint when article extraction returns nothing."""
    mock_scraper_service.extract_articles_from_soup.return_value = [] # Simulate extraction failure
    headers = {'X-CloudScheduler': 'true'}
    response = client.post('/tasks/scrape/google-news', headers=headers)
    data = json.loads(response.data)

    assert response.status_code == 200 # Endpoint succeeds, but adds 0 articles
    assert data['status'] == 'success'
    assert data['message'] == 'No articles found or extracted'
    assert data['articles_added'] == 0
    mock_scraper_service.check_article_exists.assert_not_called()

def test_scrape_task_save_fails(client, mock_scraper_service): # noqa: F811
    """Test endpoint when saving a new article fails."""
    mock_scraper_service.save_new_article.return_value = False # Simulate save failure
    headers = {'X-CloudScheduler': 'true'}
    response = client.post('/tasks/scrape/google-news', headers=headers)
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['status'] == 'success'
    assert data['articles_added'] == 0
    assert data['articles_failed_or_skipped'] == 1 # The one new article failed to save
    mock_scraper_service.save_new_article.assert_called_once()

@patch('app.main.db', None) # Simulate db connection failed at startup
def test_scrape_task_db_not_initialized(client): # noqa: F811
    """Test response when Firestore client wasn't initialized."""
    headers = {'X-CloudScheduler': 'true'}
    response = client.post('/tasks/scrape/google-news', headers=headers)
    data = json.loads(response.data)

    assert response.status_code == 500
    assert data['status'] == 'error'
    assert data['message'] == 'Firestore client not initialized'
