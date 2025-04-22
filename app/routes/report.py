import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, make_response, send_file, Response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Profile, Session as InterviewSession, Question, Answer
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.utils.report_utils import generate_csv_report, generate_pdf_report

# Create report blueprint
report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/reports')
def reports():
    """Render the reports list page."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to view reports', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get completed interview sessions
    completed_sessions = InterviewSession.query.filter(
        InterviewSession.user_id == user_id,
        InterviewSession.completed_at.isnot(None)
    ).order_by(InterviewSession.completed_at.desc()).all()
    
    return render_template('reports.html', sessions=completed_sessions)

@report_bp.route('/reports/<int:session_id>')
def view_report(session_id):
    """Render the report view page."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to view the report', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = InterviewSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if interview is completed
    if not interview_session.completed_at:
        flash('Interview is not completed yet', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    # Get profile
    profile = Profile.query.get(interview_session.profile_id)
    
    # Get questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    # Calculate overall score
    total_score = 0
    answered_questions = 0
    
    for question in questions:
        if question.answer and question.answer.score:
            total_score += question.answer.score
            answered_questions += 1
    
    overall_score = round(total_score / answered_questions, 1) if answered_questions > 0 else 0
    
    # Update overall score in session model
    interview_session.overall_score = overall_score
    db.session.commit()
    
    # Prepare questions and answers for template
    qa_list = []
    for question in questions:
        qa_item = {
            'question': question.question_text,
            'question_index': question.question_index
        }
        
        if question.answer:
            qa_item['answer'] = question.answer.transcript
            qa_item['score'] = question.answer.score
            qa_item['strengths'] = question.answer.strengths.split('\n') if question.answer.strengths else []
            qa_item['weaknesses'] = question.answer.weaknesses.split('\n') if question.answer.weaknesses else []
            qa_item['feedback'] = question.answer.feedback
        else:
            qa_item['answer'] = 'No answer provided'
            qa_item['score'] = 0
            qa_item['strengths'] = []
            qa_item['weaknesses'] = []
            qa_item['feedback'] = 'No feedback available'
        
        qa_list.append(qa_item)
    
    # Get improvement tips
    improvement_tips = []
    for qa in qa_list:
        if qa.get('weaknesses'):
            for weakness in qa.get('weaknesses'):
                if weakness and weakness not in improvement_tips:
                    improvement_tips.append(weakness)
    
    return render_template(
        'report.html',
        interview_session=interview_session,
        profile=profile,
        qa_list=qa_list,
        improvement_tips=improvement_tips
    )

@report_bp.route('/reports/<int:session_id>/csv')
def download_csv(session_id):
    """Generate and download a CSV report."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to download the report', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = InterviewSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if interview is completed
    if not interview_session.completed_at:
        flash('Interview is not completed yet', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    # Get questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    # Calculate overall score
    total_score = 0
    answered_questions = 0
    
    for question in questions:
        if question.answer and question.answer.score:
            total_score += question.answer.score
            answered_questions += 1
    
    overall_score = round(total_score / answered_questions, 1) if answered_questions > 0 else 0
    
    # Update overall score in session model
    interview_session.overall_score = overall_score
    db.session.commit()
    
    try:
        buf = generate_csv_report(interview_session, questions)
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=interview_report_{session_id}.csv'
            }
        )
    except Exception as e:
        current_app.logger.error(f"CSV download error: {e}")
        flash('Error generating CSV report.', 'error')
        return redirect(url_for('report_bp.view_report', session_id=session_id))

@report_bp.route('/reports/<int:session_id>/pdf')
def download_pdf(session_id):
    """Generate and download a PDF report."""
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to download the report', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = InterviewSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if interview is completed
    if not interview_session.completed_at:
        flash('Interview is not completed yet', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    # Get profile
    profile = Profile.query.get(interview_session.profile_id)
    
    # Get questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    # Calculate overall score
    total_score = 0
    answered_questions = 0
    
    for question in questions:
        if question.answer and question.answer.score:
            total_score += question.answer.score
            answered_questions += 1
    
    overall_score = round(total_score / answered_questions, 1) if answered_questions > 0 else 0
    
    # Update overall score in session model
    interview_session.overall_score = overall_score
    db.session.commit()
    
    # Prepare questions and answers for template
    qa_list = []
    for question in questions:
        qa_item = {
            'question': question.question_text,
            'question_index': question.question_index
        }
        
        if question.answer:
            qa_item['answer'] = question.answer.transcript
            qa_item['score'] = question.answer.score
            qa_item['strengths'] = question.answer.strengths.split('\n') if question.answer.strengths else []
            qa_item['weaknesses'] = question.answer.weaknesses.split('\n') if question.answer.weaknesses else []
            qa_item['feedback'] = question.answer.feedback
        else:
            qa_item['answer'] = 'No answer provided'
            qa_item['score'] = 0
            qa_item['strengths'] = []
            qa_item['weaknesses'] = []
            qa_item['feedback'] = 'No feedback available'
        
        qa_list.append(qa_item)
    
    # Get improvement tips
    improvement_tips = []
    for qa in qa_list:
        if qa.get('weaknesses'):
            for weakness in qa.get('weaknesses'):
                if weakness and weakness not in improvement_tips:
                    improvement_tips.append(weakness)
    
    # Create PDF
    try:
        buf = generate_pdf_report(interview_session, questions)
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=interview_report_{session_id}.pdf'
            }
        )
    except Exception as e:
        current_app.logger.error(f"PDF download error: {e}")
        flash('Error generating PDF report.', 'error')
        return redirect(url_for('report_bp.view_report', session_id=session_id))

# API routes for reports

@report_bp.route('/api/reports', methods=['GET'])
@jwt_required()
def api_get_reports():
    """API endpoint to get user's reports."""
    current_user_id = get_jwt_identity()
    
    # Get completed interview sessions
    completed_sessions = InterviewSession.query.filter(
        InterviewSession.user_id == current_user_id,
        InterviewSession.completed_at.isnot(None)
    ).order_by(InterviewSession.completed_at.desc()).all()
    
    reports_list = []
    for session in completed_sessions:
        profile = Profile.query.get(session.profile_id)
        
        reports_list.append({
            'id': session.id,
            'profile_type': profile.profile_type,
            'experience_level': profile.experience_level,
            'overall_score': session.overall_score,
            'total_questions': session.total_questions,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
    
    return jsonify(reports_list), 200

@report_bp.route('/api/reports/<int:session_id>', methods=['GET'])
@jwt_required()
def api_get_report(session_id):
    """API endpoint to get a specific report."""
    current_user_id = get_jwt_identity()
    
    # Get interview session
    interview_session = InterviewSession.query.filter_by(id=session_id, user_id=current_user_id).first()
    
    if not interview_session:
        return jsonify({'error': 'Interview session not found'}), 404
    
    # Check if interview is completed
    if not interview_session.completed_at:
        return jsonify({'error': 'Interview is not completed yet'}), 400
    
    # Get profile
    profile = Profile.query.get(interview_session.profile_id)
    
    # Get questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    # Prepare questions and answers for response
    qa_list = []
    for question in questions:
        qa_item = {
            'question_id': question.id,
            'question_index': question.question_index,
            'question_text': question.question_text
        }
        
        if question.answer:
            qa_item['answer'] = {
                'transcript': question.answer.transcript,
                'score': question.answer.score,
                'strengths': question.answer.strengths.split('\n') if question.answer.strengths else [],
                'weaknesses': question.answer.weaknesses.split('\n') if question.answer.weaknesses else [],
                'feedback': question.answer.feedback
            }
        
        qa_list.append(qa_item)
    
    # Prepare response
    response = {
        'session_id': interview_session.id,
        'profile': {
            'profile_type': profile.profile_type,
            'skills': profile.skills.split(','),
            'experience_level': profile.experience_level,
            'target_industry': profile.target_industry
        },
        'overall_score': interview_session.overall_score,
        'total_questions': interview_session.total_questions,
        'completed_at': interview_session.completed_at.isoformat() if interview_session.completed_at else None,
        'qa_list': qa_list
    }
    
    return jsonify(response), 200 