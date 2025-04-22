"""
Main application entry point.
"""

from app import create_app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting application...")
    app = create_app()
    logger.info("Database initialized. Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
