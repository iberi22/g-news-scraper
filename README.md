# Google News Scraper API (NVP)

This project implements a Minimum Viable Product (NVP) for a Python Flask API service designed to periodically scrape Google News, store new findings in Firestore, and provide an API endpoint to retrieve the latest news.

The primary constraint is to operate strictly within the Google Cloud Platform (GCP) free tier limitations.

## Features

*   **Periodic Scraping:** Uses Cloud Scheduler to trigger scraping task via HTTP POST.
*   **Google News Scraping:** Scrapes Google News homepage (requires manual CSS selector configuration).
*   **Deduplication:** Stores only new articles in Firestore based on hashed article URL.
*   **Firestore Storage:** Stores article metadata (title, URL, source, snippet, timestamp).
*   **API Endpoint:** Provides a `GET /news/google` endpoint to retrieve the latest stored articles with pagination.

## Project Structure

```
/
├── app/                  # Main Flask application code
│   ├── services/         # Business logic modules (e.g., scraper)
│   │   └── scraper.py
│   ├── __init__.py
│   ├── config.py         # Configuration settings (including selectors)
│   └── main.py           # Flask app creation, routes, Firestore client
├── docs/                 # Project documentation (PLANNING, RULES, TASK)
├── tests/                # Pytest tests
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures (app, client)
│   ├── test_api.py       # API endpoint tests
│   └── test_scraper.py   # Scraper service unit tests
├── .env.example        # Example environment variables
├── .flake8             # Flake8 configuration
├── .gitignore          # Git ignore file (assumed)
├── Dockerfile          # Dockerfile for containerization
├── firestore.rules     # Firestore security rules
├── pyproject.toml      # Black configuration
├── README.md           # This file
├── requirements-dev.txt # Development dependencies (testing, linting)
├── requirements.txt    # Application dependencies
└── devserver.sh        # Script to run local dev server
```

## Setup and Local Development

1.  **Prerequisites:**
    *   Python 3.11+ (as specified in `pyproject.toml` and `Dockerfile`)
    *   `virtualenv` (or Python's built-in `venv`)
    *   Google Cloud SDK (`gcloud`) installed and configured (optional, for local ADC)

2.  **Clone the Repository:**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

3.  **Create Virtual Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

4.  **Install Dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

5.  **Configuration:**
    *   Copy `.env.example` to `.env`: `cp .env.example .env`
    *   **(Optional - Local Firestore Access):** If you want to connect to a real Firestore project locally (instead of the emulator), you need Application Default Credentials (ADC) setup:
        *   Run `gcloud auth application-default login`
        *   Ensure the project set in `gcloud config list` matches your target Firestore project, or uncomment and set `GOOGLE_CLOUD_PROJECT` in `.env`.
    *   **(CRITICAL - Scraper Selectors):** You **MUST** manually inspect the Google News page configured in `app/config.py` (`GOOGLE_NEWS_URL`) and update the `SCRAPER_*_SELECTOR` variables in `app/config.py` with the correct CSS selectors. The current values are placeholders and **will not work**. See comments in `app/config.py` for guidance.

6.  **Run the Development Server:**
    ```bash
    ./devserver.sh
    ```
    The API should be available at `http://localhost:3000` (or the port specified by the `PORT` env var).

## Testing

Run the unit and integration tests using pytest:

```bash
source .venv/bin/activate # Make sure virtualenv is active
pytest tests/
```

## API Endpoints

*   **`GET /news/google`**: Retrieves the latest stored articles.
    *   Query Parameters:
        *   `limit` (int, optional, default: 20, max: 100): Number of articles to return.
        *   `offset` (int, optional, default: 0): Number of articles to skip.
    *   Success Response (200):
        ```json
        {
          "status": "success",
          "articles": [
            {
              "id": "firestore_doc_id_1",
              "title": "Article Title 1",
              "article_url": "http://original.site/article1",
              "source_name": "News Source A",
              "snippet": "A short description...",
              "google_news_url": "http://news.google.com/...",
              "scraped_at": "2023-10-27T10:00:00+00:00"
            },
            ...
          ],
          "limit": 20,
          "offset": 0
        }
        ```
    *   Error Responses: 400 (invalid params), 500 (server/db error).

*   **`POST /tasks/scrape/google-news`**: Triggers the scraping process. **Intended to be called by Cloud Scheduler.**
    *   Security: Requires `X-CloudScheduler: true` header (or OIDC token if configured).
    *   Success Response (200):
        ```json
        {
          "status": "success",
          "articles_processed": 50,
          "articles_added": 5,
          "articles_failed_or_skipped": 0
        }
        ```
    *   Error Responses: 403 (unauthorized), 500 (server/db/scrape error).

## Deployment (Overview)

This application is designed for deployment on Google Cloud Run.

1.  **Dockerfile:** The included `Dockerfile` builds a container image using `gunicorn`.
2.  **Firestore Setup:**
    *   Ensure you have a Firestore database created in your GCP project (Native mode recommended).
    *   **Indexes:** Manually create the required single-field indexes in the Firestore console for the `google_news_articles` collection:
        *   `scraped_at` - Descending
        *   *(Note: Index on `article_url` is not strictly needed if checking existence by Document ID hash, but was specified in planning)*
    *   **Security Rules:** Deploy the rules defined in `firestore.rules` (e.g., using Firebase CLI or GCP console). These allow public reads and restrict writes.
3.  **Cloud Run Service:**
    *   Build the Docker image (e.g., using Cloud Build: `gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/google-news-scraper`).
    *   Deploy the image to Cloud Run (`gcloud run deploy google-news-scraper --image gcr.io/YOUR_PROJECT_ID/google-news-scraper --platform managed --region YOUR_REGION --allow-unauthenticated`).
    *   **Permissions:** Ensure the Cloud Run service account (find it in the service details) has permission to write to Firestore (e.g., grant the `roles/datastore.user` IAM role to the service account).
    *   **(Optional) Environment Variables:** Configure `GOOGLE_CLOUD_PROJECT` if needed in the Cloud Run service settings.
4.  **Cloud Scheduler Job:**
    *   Create a Cloud Scheduler job.
    *   Target Type: HTTP.
    *   URL: The HTTPS URL of your deployed Cloud Run service, appended with `/tasks/scrape/google-news`.
    *   HTTP Method: POST.
    *   Headers: Add a header `X-CloudScheduler` with value `true`.
    *   Frequency: Define your desired schedule (e.g., `0 * * * *` for hourly).
    *   (Recommended): Configure OIDC authentication for a more secure connection between Scheduler and Cloud Run instead of the basic header check.

## Important Notes

*   **CSS Selectors:** Scraping relies on CSS selectors found in `app/config.py`. These are **brittle** and **will break** when Google changes its website structure. They must be manually updated periodically by inspecting the target URL.
*   **Free Tier:** The architecture aims for the GCP free tier, but monitor usage (Firestore reads/writes, Cloud Run instance time, Scheduler jobs).
*   **Error Handling:** Basic error handling is implemented, but could be enhanced (e.g., retries, more specific logging).
