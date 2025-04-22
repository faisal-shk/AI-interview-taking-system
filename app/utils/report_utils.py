"""
Report generation utilities module.
This module handles the generation of CSV and PDF reports from interview data.
"""

import os
import csv
import io
from datetime import datetime
# fpdf is imported inside generate_pdf_report to allow lazy loading
from flask import current_app

def generate_csv_report(session, questions):
    """
    Generate a CSV report from interview session data.
    
    Args:
        session: The interview session object
        questions: List of questions with answers
        
    Returns:
        BytesIO: CSV file as a bytes buffer
    """
    # Use a binary buffer with a text wrapper for CSV
    buffer = io.BytesIO()
    text_buffer = io.TextIOWrapper(buffer, encoding='utf-8', newline='')
    writer = csv.writer(text_buffer)
    
    # Write header row
    writer.writerow(['Interview Report', '', ''])
    writer.writerow(['Job Title', session.job_title, ''])
    writer.writerow(['Date', session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else 'Incomplete', ''])
    writer.writerow(['Mode', session.mode, ''])
    writer.writerow(['', '', ''])
    writer.writerow(['Question #', 'Question', 'Question Type', 'Answer', 'Score', 'Feedback'])
    
    # Write question and answer data
    for i, question in enumerate(questions):
        if question.answer:
            writer.writerow([
                i + 1,
                question.question_text,
                question.question_type,
                question.answer.transcript,
                question.answer.score if question.answer.score else 'N/A',
                question.answer.feedback if question.answer.feedback else 'No feedback'
            ])
        else:
            writer.writerow([i + 1, question.question_text, question.question_type, 'No answer', 'N/A', 'N/A'])
    
    # Write summary
    writer.writerow(['', '', ''])
    writer.writerow(['Overall Score', f'{session.overall_score}/100', ''])
    
    # Flush and rewind binary buffer
    text_buffer.flush()
    buffer.seek(0)
    return buffer

def generate_pdf_report(session, questions):
    """
    Generate a PDF report from interview session data.
    
    Args:
        session: The interview session object
        questions: List of questions with answers
        
    Returns:
        BytesIO: PDF file as a bytes buffer
    """
    # Lazy import of FPDF to avoid ModuleNotFoundError at top-level
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    
    # Set up fonts
    pdf.set_font('Arial', 'B', 16)
    
    # Title
    pdf.cell(190, 10, 'Interview Report', 0, 1, 'C')
    pdf.ln(5)
    
    # Interview details
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Job Title:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(150, 10, session.job_title, 0, 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Date:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(150, 10, session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else 'Incomplete', 0, 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Mode:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(150, 10, session.mode.capitalize(), 0, 1)
    
    pdf.ln(5)
    
    # Overall score
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, f'Overall Score: {session.overall_score}/100', 0, 1, 'C')
    
    # Draw a horizontal line
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Questions and answers
    for i, question in enumerate(questions):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(190, 10, f'Question {i+1}: {question.question_type.capitalize()}', 0, 1)
        
        pdf.set_font('Arial', '', 12)
        # Handle multi-line question text
        pdf.multi_cell(190, 10, question.question_text)
        pdf.ln(2)
        
        if hasattr(question, 'answer') and question.answer:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, 'Your Answer:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(190, 10, question.answer.transcript)
            
            if question.answer.score:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(40, 10, 'Score:', 0, 0)
                pdf.set_font('Arial', '', 12)
                pdf.cell(150, 10, f'{question.answer.score}/100', 0, 1)
            
            if question.answer.strengths:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(40, 10, 'Strengths:', 0, 1)
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(190, 10, question.answer.strengths)
            
            if question.answer.weaknesses:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(40, 10, 'Areas for Improvement:', 0, 1)
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(190, 10, question.answer.weaknesses)
            
            if question.answer.feedback:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(40, 10, 'Feedback:', 0, 1)
                pdf.set_font('Arial', '', 12)
                pdf.multi_cell(190, 10, question.answer.feedback)
        else:
            pdf.set_font('Arial', 'I', 12)
            pdf.cell(190, 10, 'No answer provided', 0, 1)
        
        # Draw a horizontal line between questions
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Add a new page if we're running out of space
        if pdf.get_y() > 250:
            pdf.add_page()
    
    # Add summary and recommendations
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(190, 10, 'Summary and Recommendations', 0, 1, 'C')
    pdf.ln(5)
    
    # Performance categories
    if session.overall_score >= 80:
        performance = "Excellent"
        recommendation = "The candidate demonstrated strong knowledge and skills relevant to the position. They provided clear, comprehensive answers with good examples. Highly recommended for the next stage of the interview process."
    elif session.overall_score >= 70:
        performance = "Good"
        recommendation = "The candidate showed good understanding of the key concepts and provided satisfactory answers. Consider moving forward with the interview process."
    elif session.overall_score >= 60:
        performance = "Satisfactory"
        recommendation = "The candidate demonstrated basic understanding but could improve in some areas. Consider additional assessment or a follow-up interview focusing on weaker areas."
    else:
        performance = "Needs Improvement"
        recommendation = "The candidate struggled with several key concepts. Consider additional training or experience before proceeding with the interview process."
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Performance:', 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.cell(150, 10, performance, 0, 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Recommendation:', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(190, 10, recommendation)
    
    # Generate PDF as a string and wrap in BytesIO buffer
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_bytes) 