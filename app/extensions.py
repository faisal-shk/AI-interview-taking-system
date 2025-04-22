"""
Flask extensions module.
This module initializes Flask extensions used throughout the application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def init_extensions(app):
    """
    Initialize Flask extensions with the application.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app) 