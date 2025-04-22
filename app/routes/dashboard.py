"""
Dashboard routes module.
This module handles the main application dashboard and interview session management, including:
- Dashboard display
- Interview session creation and management
- Question generation and handling
- Session state management
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Profile, Session as InterviewSession, Question
from app.utils.openai_utils import generate_questions
from datetime import datetime

# Create dashboard blueprint
# This organizes all dashboard-related routes under the 'dashboard_bp' namespace
dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    """
    Render the main dashboard page.
    
    Returns:
        - If user is logged in: Renders dashboard.html with user's sessions and profiles
        - If user is not logged in: Redirects to login page
    """
    if 'user_id' not in session:
        flash('Please login to access the dashboard', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get user's profiles
    profiles = Profile.query.filter_by(user_id=user_id).all()
    
    # Get user's active and completed sessions
    active_sessions = InterviewSession.query.filter_by(user_id=user_id, completed=False).all()
    completed_sessions = InterviewSession.query.filter_by(user_id=user_id, completed=True).all()
    
    # Combine active and completed sessions
    interview_sessions = active_sessions + completed_sessions
    
    return render_template('dashboard.html', 
                         profiles=profiles,
                         interview_sessions=interview_sessions)

@dashboard_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Render and handle the profile creation form."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to create a profile', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if request.method == 'GET':
        # List of profile types
        profile_types = [
            'Backend Developer',
            'Frontend Developer',
            'Full Stack Developer',
            'DevOps Engineer',
            'Data Scientist',
            'Machine Learning Engineer',
            'Mobile Developer',
            'QA Engineer',
            'Product Manager',
            'UX/UI Designer'
        ]
        
        # List of experience levels
        experience_levels = [
            'Junior',
            'Mid-Level',
            'Senior',
            'Lead',
            'Principal'
        ]
        
        # List of skills (example)
        skills_list = [
            'Python', 'JavaScript', 'Java', 'C#', 'C++', 'Go', 'Rust',
            'React', 'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask',
            'Spring Boot', 'ASP.NET', 'Express.js',
            'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Redis',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'CI/CD', 'Git', 'TDD', 'Agile', 'Scrum',
            'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
            'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy',
            'REST API', 'GraphQL', 'Microservices', 'Serverless',
            'React Native', 'Flutter', 'iOS', 'Android',
            'UI/UX', 'Figma', 'Sketch', 'Adobe XD'
        ]
        
        # List of industries
        industries = [
            'Technology',
            'Finance',
            'Healthcare',
            'Education',
            'E-commerce',
            'Media',
            'Manufacturing',
            'Transportation',
            'Energy',
            'Government',
            'Consulting',
            'Telecommunications',
            'Retail'
        ]
        
        return render_template(
            'profile.html',
            profile_types=profile_types,
            experience_levels=experience_levels,
            skills_list=skills_list,
            industries=industries,
            user=user
        )
    
    # Handle form submission
    data = request.form
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    profile_type = data.get('profile_type')
    skills = data.getlist('skills')
    experience_level = data.get('experience_level')
    target_industry = data.get('target_industry')
    
    # Validate input
    if not all([name, email, profile_type, skills, experience_level, target_industry]):
        flash('All required fields must be filled', 'error')
        return redirect(url_for('dashboard_bp.profile'))
    
    # Create profile
    new_profile = Profile(
        user_id=user_id,
        name=name,
        email=email,
        phone=phone,
        profile_type=profile_type,
        skills=','.join(skills),  # Store as comma-separated string
        experience_level=experience_level,
        target_industry=target_industry
    )
    
    try:
        db.session.add(new_profile)
        db.session.commit()
        flash('Profile created successfully!', 'success')
        return redirect(url_for('dashboard_bp.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating profile: {str(e)}', 'error')
        return redirect(url_for('dashboard_bp.profile'))

@dashboard_bp.route('/start_interview', methods=['GET', 'POST'])
def start_interview():
    """Render and handle the interview setup form."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to start an interview', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    if request.method == 'GET':
        # Get user profiles
        profiles = Profile.query.filter_by(user_id=user_id).all()
        
        if not profiles:
            flash('Please create a profile first', 'error')
            return redirect(url_for('dashboard_bp.profile'))
        
        return render_template(
            'start_interview.html',
            profiles=profiles
        )
    
    # Handle form submission
    data = request.form
    profile_id = data.get('profile_id')
    mode = data.get('mode')
    num_questions = int(data.get('num_questions', 5))
    job_title = data.get('job_title')
    job_description = data.get('job_description')
    
    # Validate input
    if not profile_id or not mode or not num_questions or not job_title or not job_description:
        flash('All fields are required', 'error')
        return redirect(url_for('dashboard_bp.start_interview'))
    
    if num_questions < 1 or num_questions > 20:
        flash('Number of questions must be between 1 and 20', 'error')
        return redirect(url_for('dashboard_bp.start_interview'))
    
    # Create interview session
    new_session = InterviewSession(
        user_id=user_id,
        profile_id=profile_id,
        mode=mode,
        total_questions=num_questions,
        job_title=job_title,
        job_description=job_description
    )
    
    db.session.add(new_session)
    db.session.commit()
    
    # Redirect to the first question
    return redirect(url_for('interview_bp.question', session_id=new_session.id))

# API routes for dashboard

@dashboard_bp.route('/api/profiles', methods=['GET'])
@jwt_required()
def api_get_profiles():
    """API endpoint to get user profiles."""
    current_user_id = get_jwt_identity()
    
    profiles = Profile.query.filter_by(user_id=current_user_id).all()
    
    profiles_list = []
    for profile in profiles:
        profiles_list.append({
            'id': profile.id,
            'profile_type': profile.profile_type,
            'skills': profile.skills.split(','),
            'experience_level': profile.experience_level,
            'target_industry': profile.target_industry,
            'created_at': profile.created_at.isoformat()
        })
    
    return jsonify(profiles_list), 200

@dashboard_bp.route('/api/profiles', methods=['POST'])
@jwt_required()
def api_create_profile():
    """API endpoint to create a profile."""
    current_user_id = get_jwt_identity()
    
    data = request.get_json()
    profile_type = data.get('profile_type')
    skills = data.get('skills')
    experience_level = data.get('experience_level')
    target_industry = data.get('target_industry')
    
    # Validate input
    if not profile_type or not skills or not experience_level or not target_industry:
        return jsonify({'error': 'All fields are required'}), 400
    
    # Create profile
    new_profile = Profile(
        user_id=current_user_id,
        profile_type=profile_type,
        skills=','.join(skills) if isinstance(skills, list) else skills,
        experience_level=experience_level,
        target_industry=target_industry
    )
    
    db.session.add(new_profile)
    db.session.commit()
    
    return jsonify({
        'id': new_profile.id,
        'profile_type': new_profile.profile_type,
        'skills': new_profile.skills.split(','),
        'experience_level': new_profile.experience_level,
        'target_industry': new_profile.target_industry,
        'created_at': new_profile.created_at.isoformat()
    }), 201

@dashboard_bp.route('/api/sessions', methods=['GET'])
@jwt_required()
def api_get_sessions():
    """API endpoint to get user interview sessions."""
    current_user_id = get_jwt_identity()
    
    sessions = InterviewSession.query.filter_by(user_id=current_user_id).order_by(InterviewSession.created_at.desc()).all()
    
    sessions_list = []
    for session in sessions:
        sessions_list.append({
            'id': session.id,
            'profile_id': session.profile_id,
            'mode': session.mode,
            'current_question_index': session.current_question_index,
            'total_questions': session.total_questions,
            'overall_score': session.overall_score,
            'created_at': session.created_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
    
    return jsonify(sessions_list), 200

@dashboard_bp.route('/api/sessions', methods=['POST'])
@jwt_required()
def api_create_session():
    """API endpoint to create an interview session."""
    current_user_id = get_jwt_identity()
    
    data = request.get_json()
    profile_id = data.get('profile_id')
    mode = data.get('mode')
    num_questions = int(data.get('num_questions', 5))
    
    # Validate input
    if not profile_id or not mode:
        return jsonify({'error': 'Profile ID and mode are required'}), 400
    
    if num_questions < 1 or num_questions > 20:
        return jsonify({'error': 'Number of questions must be between 1 and 20'}), 400
    
    # Validate profile ownership
    profile = Profile.query.get(profile_id)
    if not profile or profile.user_id != current_user_id:
        return jsonify({'error': 'Profile not found or not owned by user'}), 404
    
    # Create interview session
    new_session = InterviewSession(
        user_id=current_user_id,
        profile_id=profile_id,
        mode=mode,
        total_questions=num_questions
    )
    
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({
        'id': new_session.id,
        'profile_id': new_session.profile_id,
        'mode': new_session.mode,
        'current_question_index': new_session.current_question_index,
        'total_questions': new_session.total_questions,
        'created_at': new_session.created_at.isoformat()
    }), 201

@dashboard_bp.route('/create_session', methods=['POST'])
def create_session():
    """
    Create a new interview session.
    
    POST: Processes session creation request
    
    Returns:
        - Success: Redirects to interview session page
        - Error: Redirects to dashboard with error message
    """
    if 'user_id' not in session:
        flash('Please login to create a session', 'error')
        return redirect(url_for('auth_bp.login'))
    
    # Get form data
    job_title = request.form.get('job_title')
    job_description = request.form.get('job_description')
    num_questions = int(request.form.get('num_questions', 5))
    
    # Validate input
    if not job_title or not job_description:
        flash('Job title and description are required', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Generate questions using OpenAI
    try:
        questions_data = generate_questions(job_title, job_description, num_questions)
    except Exception as e:
        flash(f'Error generating questions: {str(e)}', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Create new session
    new_session = InterviewSession(
        user_id=session['user_id'],
        job_title=job_title,
        job_description=job_description,
        total_questions=num_questions,
        current_question_index=0,
        mode='bulk'  # Default to bulk mode for form-based creation
    )
    db.session.add(new_session)
    db.session.commit()
    
    # Create questions for the session
    for q_data in questions_data:
        question = Question(
            session_id=new_session.id,
            question_text=q_data['question'],
            question_type=q_data['type']
        )
        db.session.add(question)
    
    db.session.commit()
    
    return redirect(url_for('interview_bp.question', session_id=new_session.id))

@dashboard_bp.route('/interview/<int:session_id>')
def interview(session_id):
    """
    Display and handle interview session.
    
    Args:
        session_id: ID of the interview session
    
    Returns:
        - If session exists: Renders interview.html with current question
        - If session doesn't exist: Redirects to dashboard with error
        - If session is completed: Redirects to results page
    """
    if 'user_id' not in session:
        flash('Please login to access the interview', 'error')
        return redirect(url_for('auth_bp.login'))
    
    # Get session and validate ownership
    interview_session = InterviewSession.query.get_or_404(session_id)
    if interview_session.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if session is completed
    if interview_session.completed:
        return redirect(url_for('dashboard_bp.results', session_id=session_id))
    
    # Get current question
    current_question = Question.query.filter_by(
        session_id=session_id,
        question_index=interview_session.current_question_index
    ).first()
    
    if not current_question:
        flash('No questions found for this session', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    return render_template('interview.html',
                         session=interview_session,
                         question=current_question)

@dashboard_bp.route('/submit_answer/<int:session_id>', methods=['POST'])
def submit_answer(session_id):
    """
    Process answer submission for current question.
    
    Args:
        session_id: ID of the interview session
    
    Returns:
        - Success: Redirects to next question or results page
        - Error: Redirects to current question with error message
    """
    if 'user_id' not in session:
        flash('Please login to submit answers', 'error')
        return redirect(url_for('auth_bp.login'))
    
    # Get session and validate ownership
    interview_session = InterviewSession.query.get_or_404(session_id)
    if interview_session.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Get current question
    current_question = Question.query.filter_by(
        session_id=session_id,
        question_index=interview_session.current_question_index
    ).first()
    
    if not current_question:
        flash('No questions found for this session', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Get and validate answer
    answer = request.form.get('answer')
    if not answer:
        flash('Please provide an answer', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    # Save answer
    current_question.answer = answer
    current_question.answered_at = datetime.utcnow()
    
    # Move to next question or complete session
    interview_session.current_question_index += 1
    if interview_session.current_question_index >= interview_session.total_questions:
        interview_session.completed = True
        interview_session.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    if interview_session.completed:
        return redirect(url_for('dashboard_bp.results', session_id=session_id))
    else:
        return redirect(url_for('interview_bp.question', session_id=session_id))

@dashboard_bp.route('/results/<int:session_id>')
def results(session_id):
    """
    Display interview session results.
    
    Args:
        session_id: ID of the interview session
    
    Returns:
        - If session exists: Renders results.html with session data
        - If session doesn't exist: Redirects to dashboard with error
    """
    if 'user_id' not in session:
        flash('Please login to view results', 'error')
        return redirect(url_for('auth_bp.login'))
    
    # Get session and validate ownership
    interview_session = InterviewSession.query.get_or_404(session_id)
    if interview_session.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Get all questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    return render_template('results.html',
                         session=interview_session,
                         questions=questions) 