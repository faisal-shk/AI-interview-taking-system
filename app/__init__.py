"""
Application initialization module.
This module initializes the Flask application and its components.
"""

import os
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv
import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from logging.handlers import RotatingFileHandler
import markupsafe
from app.extensions import init_extensions, db
from flask import render_template, flash, redirect, request, url_for
import werkzeug.exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev')

# Initialize extensions
init_extensions(app)

# Add datetime functions to Jinja2 environment
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

# Check for valid OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key or openai_api_key == "your_openai_api_key_here":
    app.config['OPENAI_API_KEY_VALID'] = False
    print("WARNING: Invalid OpenAI API key. Please update your .env file with a valid key.")
else:
    app.config['OPENAI_API_KEY_VALID'] = True

# Create custom jinja2 filter for nl2br
def nl2br_filter(value):
    if value:
        if not isinstance(value, str):
            value = str(value)
        return markupsafe.Markup(markupsafe.escape(value).replace('\n', '<br>'))
    return ''

def ensure_db_directory():
    """
    Ensure the database directory exists and has proper permissions.
    """
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance')
    os.makedirs(db_path, exist_ok=True)
    # Set permissions to allow read/write
    os.chmod(db_path, 0o755)

def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: The configured Flask application
    """
    # Ensure database directory exists
    ensure_db_directory()
    
    # Register nl2br filter
    app.jinja_env.filters['nl2br'] = nl2br_filter
    
    # Register blueprints with unique names
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.interview import interview_bp
    from app.routes.report import report_bp
    
    app.register_blueprint(auth_bp, name='auth_bp')
    app.register_blueprint(dashboard_bp, name='dashboard_bp')
    app.register_blueprint(interview_bp, name='interview_bp')
    app.register_blueprint(report_bp, name='report_bp')
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(werkzeug.exceptions.RequestEntityTooLarge)
    def request_entity_too_large(e):
        flash('The file you are trying to upload is too large.', 'error')
        return redirect(request.referrer or url_for('dashboard_bp.dashboard'))
    
    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('App startup')
    
    # Create database tables and initial data
    with app.app_context():
        # Import models here to avoid circular imports
        from app.models import User
        
        try:
            # Create all tables
            db.create_all()
        except SQLAlchemyError as e:
            app.logger.error(f'Error creating database tables: {str(e)}')
            raise
        
        # Create test user if it doesn't exist
        test_email = 'test@example.com'
        try:
            test_user = User.query.filter_by(email=test_email).first()
            if not test_user:
                test_user = User(email=test_email)
                test_user.set_password('password')
                db.session.add(test_user)
                db.session.commit()
                app.logger.info('Test user created')
            else:
                app.logger.info('Test user already exists')
        except IntegrityError:
            db.session.rollback()
            app.logger.info('Test user already exists (IntegrityError)')
        
        # Create admin user if not exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        try:
            admin_user = User.query.filter_by(email=admin_email).first()
            if not admin_user:
                admin = User(email=admin_email)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                app.logger.info(f'Admin user created with email: {admin_email}')
            else:
                app.logger.info('Admin user already exists')
        except IntegrityError:
            db.session.rollback()
            app.logger.info('Admin user already exists (IntegrityError)')
    
    return app