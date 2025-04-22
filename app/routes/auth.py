"""
Authentication routes module.
This module handles user authentication, including:
- User registration
- Login/logout
- JWT token generation and validation
- Session management
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User

# Create authentication blueprint
# This organizes all authentication-related routes under the 'auth_bp' namespace
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/')
def index():
    """
    Render the home page.
    
    Returns:
        - If user is logged in: Redirects to dashboard
        - If user is not logged in: Renders index.html
        - If OpenAI API key is invalid: Shows warning message
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if OpenAI API key is valid
    if not current_app.config.get('OPENAI_API_KEY_VALID', False):
        flash('Warning: Invalid OpenAI API key. Please update your .env file with a valid key.', 'warning')
    
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    
    GET: Renders registration form
    POST: Processes registration form data
    
    Returns:
        - GET: Renders register.html
        - POST (success): Redirects to login page
        - POST (error): Renders register.html with error message
    """
    if request.method == 'GET':
        return render_template('register.html')
    
    data = request.form
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    # Validate input
    if not email or not password:
        flash('Email and password are required', 'error')
        return render_template('register.html')
    
    if password != confirm_password:
        flash('Passwords do not match', 'error')
        return render_template('register.html')
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered', 'error')
        return render_template('register.html')
    
    # Create new user
    new_user = User(email=email)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    flash('Registration successful! Please login.', 'success')
    return redirect(url_for('auth_bp.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    
    GET: Renders login form
    POST: Processes login form data
    
    Returns:
        - GET: Renders login.html
        - POST (success): Redirects to dashboard
        - POST (error): Renders login.html with error message
    """
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not email or not password:
        flash('Email and password are required', 'error')
        return render_template('login.html')
    
    # Check if user exists and password is correct
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash('Invalid email or password', 'error')
        return render_template('login.html')
    
    # Create session
    session['user_id'] = user.id
    session['email'] = user.email
    
    # Create JWT token
    access_token = create_access_token(identity=user.id)
    
    return redirect(url_for('dashboard_bp.dashboard'))

@auth_bp.route('/logout')
def logout():
    """
    Handle user logout.
    
    Returns:
        Redirects to home page with logout message
    """
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth_bp.index'))

# API routes for JWT authentication
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    API endpoint for user login.
    
    POST: Processes login request and returns JWT token
    
    Returns:
        - Success: JSON with access token and user info
        - Error: JSON with error message and status code
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Check if user exists and password is correct
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Create JWT token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'access_token': access_token,
        'user_id': user.id,
        'email': user.email
    }), 200

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    """
    API endpoint for user registration.
    
    POST: Processes registration request and returns JWT token
    
    Returns:
        - Success: JSON with access token and user info
        - Error: JSON with error message and status code
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create new user
    new_user = User(email=email)
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    # Create JWT token
    access_token = create_access_token(identity=new_user.id)
    
    return jsonify({
        'access_token': access_token,
        'user_id': new_user.id,
        'email': new_user.email
    }), 201

@auth_bp.route('/api/auth/user', methods=['GET'])
@jwt_required()
def api_get_user():
    """
    API endpoint to get current user info.
    
    GET: Returns current user information
    
    Returns:
        - Success: JSON with user info
        - Error: JSON with error message and status code
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.id,
        'email': user.email
    }), 200 