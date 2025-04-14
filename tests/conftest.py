import pytest
import sys
import os

# Add the application root directory to the Python path
# This allows tests to import modules from the 'app' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import the app
from app.main import app as flask_app

@pytest.fixture(scope='module')
def app():
    """Provides a test instance of the Flask application."""
    # Configure the app for testing
    flask_app.config.update({
        "TESTING": True,
        # Add other test-specific configurations if needed
        # e.g., use a separate test database or mock external services
        # "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Example for SQLAlchemy
    })

    # TODO: Consider mocking the Firestore client (db) here for isolation
    # For NVP, initial tests might hit the actual Firestore emulator or dev project

    yield flask_app

@pytest.fixture()
def client(app):
    """Provides a test client for the Flask application."""
    return app.test_client()

# @pytest.fixture()
# def runner(app):
#     """Provides a test CLI runner for the Flask application (if using Flask CLI commands)."""
#     return app.test_cli_runner()

# Add other fixtures as needed, e.g., for initializing database state
