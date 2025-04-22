"""
Interview routes module.
This module handles the interview session flow, including:
- Question display and generation
- Answer submission and evaluation
- Session progression
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app, send_file, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models import db, User, Profile, Session, Question, Answer
from app.utils.openai_utils import generate_questions
from app.services.openai_service import evaluate_answer
from app.utils.report_utils import generate_csv_report, generate_pdf_report

# Create interview blueprint
interview_bp = Blueprint('interview_bp', __name__)

@interview_bp.route('/interview/<int:session_id>/question')
def question(session_id):
    """
    Display the current question in the interview session.
    
    Args:
        session_id (int): ID of the interview session
    
    Returns:
        - If successful: Renders question.html with current question
        - If error: Redirects to appropriate page with error message
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to access the interview', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Check if interview is completed
    if interview_session.completed:
        return redirect(url_for('interview_bp.results', session_id=session_id))
    
    # Get current question
    question = Question.query.filter(
        Question.session_id == session_id,
        Question.question_index == interview_session.current_question_index + 1
    ).first()
    
    # If question doesn't exist, generate it
    if not question:
        # Get profile
        profile = Profile.query.get(interview_session.profile_id)
        
        if not profile:
            flash('Profile not found', 'error')
            return redirect(url_for('dashboard_bp.dashboard'))
        
        try:
            # Generate questions based on interview mode
            if interview_session.mode == 'bulk':
                # Generate all questions at once
                questions_data = generate_questions(
                    interview_session.job_title,
                    interview_session.job_description,
                    interview_session.total_questions
                )
                for i, q_data in enumerate(questions_data):
                    question = Question(
                        session_id=interview_session.id,
                        question_text=q_data['question'],
                        question_type=q_data['type'],
                        question_index=i + 1
                    )
                    db.session.add(question)
            else:
                # Generate first question for interactive mode
                current_index = interview_session.current_question_index + 1
                questions_data = generate_questions(
                    interview_session.job_title,
                    interview_session.job_description,
                    1
                )
                question = Question(
                    session_id=interview_session.id,
                    question_text=questions_data[0]['question'],
                    question_type=questions_data[0]['type'],
                    question_index=current_index
                )
                db.session.add(question)
                
            db.session.commit()
            
            # Get the question we just created if it's not already assigned
            if not question:
                question = Question.query.filter(
                    Question.session_id == session_id,
                    Question.question_index == interview_session.current_question_index + 1
                ).first()
                
            # Safety check - if still no question, create a generic one
            if not question:
                question = Question(
                    session_id=interview_session.id,
                    question_text="Tell me about your experience and skills relevant to this position.",
                    question_type="general",
                    question_index=interview_session.current_question_index + 1
                )
                db.session.add(question)
                db.session.commit()
                
        except Exception as e:
            current_app.logger.error(f"Error generating questions: {str(e)}")
            
            # Create a generic question as a fallback
            question = Question(
                session_id=interview_session.id,
                question_text="Please describe your relevant experience for this position.",
                question_type="general",
                question_index=interview_session.current_question_index + 1
            )
            db.session.add(question)
            
            try:
                db.session.commit()
            except Exception as commit_error:
                current_app.logger.error(f"Error saving fallback question: {str(commit_error)}")
                db.session.rollback()
                flash('Error generating questions. Please try again.', 'error')
                return redirect(url_for('dashboard_bp.dashboard'))
    
    return render_template(
        'interview.html',
        interview_session=interview_session,
        question=question,
        question_number=interview_session.current_question_index + 1,
        total_questions=interview_session.total_questions
    )

@interview_bp.route('/interview/<int:session_id>/answer', methods=['POST'])
def submit_answer(session_id):
    """
    Handle answer submission for the current question.
    
    Args:
        session_id (int): ID of the interview session
    
    Returns:
        - If successful: Redirects to next question or results page
        - If error: Redirects back to current question with error message
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to submit an answer', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Get current question
    question = Question.query.filter(
        Question.session_id == session_id,
        Question.question_index == interview_session.current_question_index + 1
    ).first()
    
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    # Get answer from form
    answer_text = request.form.get('answer', '').strip()
    
    if not answer_text:
        flash('Please provide an answer', 'error')
        return redirect(url_for('interview_bp.question', session_id=session_id))
    
    try:
        # Evaluate the answer (if OpenAI API key is configured)
        evaluation = evaluate_answer(question.question_text, answer_text)
        
        # Create new Answer object with evaluation
        answer = Answer(
            question_id=question.id,
            transcript=answer_text,
            score=evaluation['score'],
            strengths=evaluation['strengths'],
            weaknesses=evaluation['weaknesses'],
            feedback=evaluation['feedback']
        )
    except Exception as e:
        # If evaluation fails, create basic Answer object
        current_app.logger.error(f"Error evaluating answer: {str(e)}")
        answer = Answer(
            question_id=question.id,
            transcript=answer_text,
            score=0
        )
    
    db.session.add(answer)
    
    # Update question
    question.answered_at = datetime.utcnow()
    
    # Move to next question or complete session
    interview_session.current_question_index += 1
    if interview_session.current_question_index >= interview_session.total_questions:
        interview_session.completed = True
        interview_session.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    if interview_session.completed:
        return redirect(url_for('interview_bp.results', session_id=session_id))
    else:
        # For interactive mode, generate the next question before redirecting
        if interview_session.mode == 'interactive':
            # Check if the next question already exists
            next_question = Question.query.filter(
                Question.session_id == session_id,
                Question.question_index == interview_session.current_question_index + 1
            ).first()
            
            # Generate the next question if it doesn't exist
            if not next_question:
                try:
                    questions_data = generate_questions(
                        interview_session.job_title,
                        interview_session.job_description,
                        1
                    )
                    
                    next_question = Question(
                        session_id=session_id,
                        question_text=questions_data[0]['question'],
                        question_type=questions_data[0]['type'],
                        question_index=interview_session.current_question_index + 1
                    )
                    db.session.add(next_question)
                    db.session.commit()
                except Exception as e:
                    current_app.logger.error(f"Error generating next question: {str(e)}")
                    # Create a generic fallback question
                    try:
                        next_question = Question(
                            session_id=session_id,
                            question_text="Could you elaborate on your previous answer and relate it to your professional experience?",
                            question_type="follow-up",
                            question_index=interview_session.current_question_index + 1
                        )
                        db.session.add(next_question)
                        db.session.commit()
                    except Exception as inner_e:
                        current_app.logger.error(f"Error creating fallback question: {str(inner_e)}")
        
        return redirect(url_for('interview_bp.question', session_id=session_id))

@interview_bp.route('/interview/<int:session_id>/results')
def results(session_id):
    """
    Display interview session results.
    
    Args:
        session_id (int): ID of the interview session
    
    Returns:
        - If successful: Renders results.html with session data
        - If error: Redirects to dashboard with error message
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to view results', 'error')
        return redirect(url_for('auth_bp.login'))
    
    user_id = session['user_id']
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # Get all questions and answers
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    # Calculate overall score
    total_score = 0
    answered_questions = 0
    
    for q in questions:
        if hasattr(q, 'answer') and q.answer and q.answer.score:
            total_score += q.answer.score
            answered_questions += 1
    
    overall_score = round(total_score / answered_questions, 1) if answered_questions > 0 else 0
    
    # Update overall score in session model
    interview_session.overall_score = overall_score
    db.session.commit()
    
    return render_template(
        'results.html',
        interview_session=interview_session,
        questions=questions,
        overall_score=overall_score
    )

@interview_bp.route('/interview/<int:session_id>/download/<format>')
def download_report(session_id, format):
    """
    Download interview report in specified format.
    Args:
        session_id (int): ID of the interview session
        format (str): 'csv' or 'pdf'
    Returns:
        - File download response or redirect on error
    """
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login to download reports', 'error')
        return redirect(url_for('auth_bp.login'))

    user_id = session['user_id']
    interview_session = Session.query.filter_by(id=session_id, user_id=user_id).first()
    if not interview_session:
        flash('Interview session not found', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))

    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    filename_base = f"interview_report_{interview_session.job_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # CSV format
    if format.lower() == 'csv':
        try:
            buf = generate_csv_report(interview_session, questions)
            buf.seek(0)
            data = buf.getvalue()
            return Response(
                data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename_base}.csv'
                }
            )
        except Exception as e:
            current_app.logger.error(f"CSV download error: {e}")
            flash('Error generating CSV report.', 'error')
            return redirect(url_for('interview_bp.results', session_id=session_id))

    # PDF format
    elif format.lower() == 'pdf':
        try:
            buf = generate_pdf_report(interview_session, questions)
            buf.seek(0)
            data = buf.getvalue()
            return Response(
                data,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename={filename_base}.pdf'
                }
            )
        except Exception as e:
            current_app.logger.error(f"PDF download error: {e}")
            flash('Error generating PDF report.', 'error')
            return redirect(url_for('interview_bp.results', session_id=session_id))

    else:
        flash('Invalid report format specified', 'error')
        return redirect(url_for('interview_bp.results', session_id=session_id))

# API routes for interview

@interview_bp.route('/api/sessions/<int:session_id>/questions', methods=['GET'])
@jwt_required()
def api_get_questions(session_id):
    """API endpoint to get questions for a session."""
    current_user_id = get_jwt_identity()
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=current_user_id).first()
    
    if not interview_session:
        return jsonify({'error': 'Interview session not found'}), 404
    
    # Get questions
    questions = Question.query.filter_by(session_id=session_id).order_by(Question.question_index).all()
    
    questions_list = []
    for question in questions:
        question_data = {
            'id': question.id,
            'question_index': question.question_index,
            'question_text': question.question_text,
            'created_at': question.created_at.isoformat()
        }
        
        if question.answer:
            question_data['answer'] = {
                'transcript': question.answer.transcript,
                'score': question.answer.score,
                'strengths': question.answer.strengths,
                'weaknesses': question.answer.weaknesses,
                'feedback': question.answer.feedback,
                'created_at': question.answer.created_at.isoformat()
            }
        
        questions_list.append(question_data)
    
    return jsonify(questions_list), 200

@interview_bp.route('/api/sessions/<int:session_id>/questions/<int:question_index>', methods=['GET'])
@jwt_required()
def api_get_question(session_id, question_index):
    """API endpoint to get a specific question."""
    current_user_id = get_jwt_identity()
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=current_user_id).first()
    
    if not interview_session:
        return jsonify({'error': 'Interview session not found'}), 404
    
    # Get question
    question = Question.query.filter_by(session_id=session_id, question_index=question_index).first()
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    question_data = {
        'id': question.id,
        'question_index': question.question_index,
        'question_text': question.question_text,
        'created_at': question.created_at.isoformat()
    }
    
    if question.answer:
        question_data['answer'] = {
            'transcript': question.answer.transcript,
            'score': question.answer.score,
            'strengths': question.answer.strengths,
            'weaknesses': question.answer.weaknesses,
            'feedback': question.answer.feedback,
            'created_at': question.answer.created_at.isoformat()
        }
    
    return jsonify(question_data), 200

@interview_bp.route('/api/sessions/<int:session_id>/questions/<int:question_index>/answer', methods=['POST'])
@jwt_required()
def api_submit_answer(session_id, question_index):
    """API endpoint to submit an answer."""
    current_user_id = get_jwt_identity()
    
    # Get interview session
    interview_session = Session.query.filter_by(id=session_id, user_id=current_user_id).first()
    
    if not interview_session:
        return jsonify({'error': 'Interview session not found'}), 404
    
    # Validate question index
    if question_index != interview_session.current_question_index:
        return jsonify({'error': 'Invalid question index'}), 400
    
    # Get question
    question = Question.query.filter_by(session_id=session_id, question_index=question_index).first()
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Get transcript
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    
    # Validate transcript
    if not transcript or len(transcript) < 10:
        return jsonify({'error': 'Please provide a more detailed answer'}), 400
    
    # Evaluate answer
    evaluation = evaluate_answer(question.question_text, transcript)
    
    # Save answer
    answer = Answer(
        question_id=question.id,
        transcript=transcript,
        score=evaluation['score'],
        strengths=evaluation['strengths'],
        weaknesses=evaluation['weaknesses'],
        feedback=evaluation['feedback']
    )
    db.session.add(answer)
    
    # Update session
    interview_session.current_question_index += 1
    
    # Check if interview is completed
    if interview_session.current_question_index > interview_session.total_questions:
        # Calculate overall score
        total_score = 0
        answered_questions = 0
        
        for q in interview_session.questions:
            if q.answer:
                total_score += q.answer.score
                answered_questions += 1
        
        if answered_questions > 0:
            interview_session.overall_score = round(total_score / answered_questions, 2)
        
        interview_session.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    # Generate next question if in interactive mode
    next_question = None
    if interview_session.mode == 'interactive' and interview_session.current_question_index <= interview_session.total_questions:
        # Generate the next question
        questions_data = generate_questions(
            interview_session.job_title,
            interview_session.job_description,
            1
        )
        
        # Save question
        next_question = Question(
            session_id=session_id,
            question_text=questions_data[0]['question'],
            question_type=questions_data[0]['type'],
            question_index=interview_session.current_question_index + 1
        )
        db.session.add(next_question)
        db.session.commit()
    
    # Prepare response
    response = {
        'answer_id': answer.id,
        'score': answer.score,
        'strengths': answer.strengths,
        'weaknesses': answer.weaknesses,
        'feedback': answer.feedback,
        'current_question_index': interview_session.current_question_index,
        'total_questions': interview_session.total_questions,
        'is_completed': interview_session.current_question_index > interview_session.total_questions
    }
    
    if next_question:
        response['next_question'] = {
            'id': next_question.id,
            'question_text': next_question.question_text
        }
    
    return jsonify(response), 201 