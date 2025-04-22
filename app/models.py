"""
Database models module.
This module defines the SQLAlchemy models for the application, including:
- User model for authentication and user management
- Profile model for user professional information
- Session model for interview sessions
- Question model for interview questions
- Answer model for user answers
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    """
    User model representing application users.
    
    Attributes:
        id (int): Primary key
        email (str): User's email address (unique)
        password_hash (str): Hashed password
        created_at (datetime): Account creation timestamp
        profiles (relationship): One-to-many relationship with Profile model
        sessions (relationship): One-to-many relationship with Session model
    """
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    profiles = db.relationship('Profile', backref='user', lazy=True)
    sessions = db.relationship('Session', backref='user', lazy=True)
    
    def set_password(self, password):
        """
        Set user's password.
        
        Args:
            password (str): Plain text password to hash and store
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify user's password.
        
        Args:
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

class Profile(db.Model):
    """
    Profile model representing user's professional information.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User model
        name (str): User's full name
        email (str): User's email address
        phone (str): User's phone number
        profile_type (str): Type of profile (e.g., 'Backend Developer')
        skills (str): Comma-separated list of skills
        experience_level (str): Level of experience (e.g., 'Junior', 'Senior')
        target_industry (str): Target industry for job search
        created_at (datetime): Profile creation timestamp
        updated_at (datetime): Last update timestamp
    """
    
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    profile_type = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.String(500))
    experience_level = db.Column(db.String(50), nullable=False)
    target_industry = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Session(db.Model):
    """
    Session model representing an interview session.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User model
        profile_id (int): Foreign key to Profile model
        job_title (str): Title of the job being interviewed for
        job_description (str): Description of the job
        total_questions (int): Total number of questions in the session
        current_question_index (int): Index of current question
        mode (str): Interview mode ('interactive' or 'bulk')
        completed (bool): Whether the session is completed
        created_at (datetime): Session creation timestamp
        completed_at (datetime): Session completion timestamp
        overall_score (float): Overall score for the interview session
        questions (relationship): One-to-many relationship with Question model
    """
    
    __tablename__ = 'sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    current_question_index = db.Column(db.Integer, default=0)
    mode = db.Column(db.String(20), nullable=False, default='interactive')  # 'interactive' or 'bulk'
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    overall_score = db.Column(db.Float, nullable=True)
    
    # Relationships
    questions = db.relationship('Question', backref='session', lazy=True)
    profile = db.relationship('Profile', backref='sessions', lazy=True)

class Question(db.Model):
    """
    Question model representing interview questions.
    
    Attributes:
        id (int): Primary key
        session_id (int): Foreign key to Session model
        question_text (str): The question text
        question_type (str): Type of question (e.g., 'technical', 'behavioral')
        question_index (int): Index of question in the session
        answered_at (datetime): When the question was answered
    """
    
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    answered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add unique constraint for session_id and question_index
    __table_args__ = (
        db.UniqueConstraint('session_id', 'question_index', name='uix_session_question_index'),
    )

class Answer(db.Model):
    """
    Answer model representing user's answers to interview questions.
    
    Attributes:
        id (int): Primary key
        question_id (int): Foreign key to Question model
        transcript (str): Text transcript of the answer
        score (float): Score for the answer (0-100)
        strengths (str): List of strengths in the answer
        weaknesses (str): List of weaknesses in the answer
        feedback (str): General feedback on the answer
        created_at (datetime): When the answer was created
    """
    
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    transcript = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    question = db.relationship('Question', backref=db.backref('answer', uselist=False)) 