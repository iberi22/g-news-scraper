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

# Use the base Config directly for NVP simplicity
AppConfig = Config()
