import os
import openai
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

# Check if API key is set
if not api_key or api_key == "your_openai_api_key_here":
    print("WARNING: Invalid OpenAI API key. AI features will not work properly.")

# Initialize OpenAI client
try:
    openai.api_key = api_key
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")

def generate_questions(profile_type, skills, experience_level, target_industry, num_questions=5, previous_qa=None):
    """Generate interview questions based on the candidate's profile."""
    
    # Check if API key is available
    if not api_key or api_key == "your_openai_api_key_here":
        return ["OpenAI API key is not configured. Please update your .env file with a valid API key."] * num_questions
    
    system_prompt = """You are an expert technical interviewer. Generate challenging and relevant interview questions 
    based on the candidate's profile. Questions should be specific, technical, and appropriate for the given experience level."""
    
    user_prompt = f"""
    Profile Type: {profile_type}
    Skills: {skills}
    Experience Level: {experience_level}
    Target Industry: {target_industry}
    
    Generate {num_questions} interview questions that would effectively assess this candidate.
    """
    
    if previous_qa:
        user_prompt += f"\n\nPrevious Q&A:\n{previous_qa}\n\nGenerate the next question based on previous responses."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        questions = response.choices[0].message.content.strip().split('\n')
        # Remove numbered prefixes if present (e.g., "1. ", "Q1: ")
        clean_questions = []
        for q in questions:
            q = q.strip()
            if q:
                # Remove numeric prefixes like "1. " or "Q1: "
                parts = q.split('. ', 1)
                if len(parts) > 1 and parts[0].replace('Q', '').isdigit():
                    clean_questions.append(parts[1])
                else:
                    clean_questions.append(q)
        
        return clean_questions[:num_questions]  # Ensure we return the exact number requested
    
    except Exception as e:
        print(f"Error generating questions: {e}")
        return ["Error generating questions. Please try again."]

def evaluate_answer(question, transcript):
    """Evaluate the candidate's answer using OpenAI."""
    
    # Check if API key is available
    if not api_key or api_key == "your_openai_api_key_here":
        print("WARNING: Invalid OpenAI API key for evaluation. Using fallback evaluation.")
        return get_fallback_evaluation(transcript)
    
    system_prompt = """You are an expert technical interviewer evaluating candidate responses.
    Provide an honest and fair assessment based on technical accuracy, completeness, and clarity.
    Your evaluation should include:
    1. A numerical score from 0-100
    2. A bullet-point list of strengths
    3. A bullet-point list of weaknesses
    4. Free-form feedback with improvement suggestions
    """
    
    user_prompt = f"""
    Question: {question}
    
    Candidate's Answer: {transcript}
    
    Please evaluate this response with:
    - Score (0-100): 
    - Strengths:
    - Weaknesses:
    - Feedback:
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        evaluation = response.choices[0].message.content
        
        # Parse the evaluation to extract score, strengths, weaknesses, and feedback
        score = 0
        strengths = ""
        weaknesses = ""
        feedback = ""
        
        lines = evaluation.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('Score') or line.startswith('- Score'):
                try:
                    # Extract number from string like "Score (0-100): 75"
                    score_str = line.split(':')[1].strip()
                    score = int(score_str.split()[0])
                except:
                    score = 0
            
            elif line.startswith('Strengths') or line.startswith('- Strengths'):
                strengths_lines = []
                j = i + 1
                while j < len(lines) and (lines[j].startswith('-') or lines[j].startswith('*') or not lines[j].strip()):
                    if lines[j].strip() and not lines[j].strip() == '-':
                        strengths_lines.append(lines[j].strip())
                    j += 1
                strengths = '\n'.join(strengths_lines)
            
            elif line.startswith('Weaknesses') or line.startswith('- Weaknesses'):
                weaknesses_lines = []
                j = i + 1
                while j < len(lines) and (lines[j].startswith('-') or lines[j].startswith('*') or not lines[j].strip()):
                    if lines[j].strip() and not lines[j].strip() == '-':
                        weaknesses_lines.append(lines[j].strip())
                    j += 1
                weaknesses = '\n'.join(weaknesses_lines)
            
            elif line.startswith('Feedback') or line.startswith('- Feedback'):
                feedback_lines = []
                j = i + 1
                while j < len(lines):
                    if lines[j].strip():
                        feedback_lines.append(lines[j].strip())
                    j += 1
                feedback = '\n'.join(feedback_lines)
        
        # If parsing failed, use fallback evaluation
        if not score and not strengths and not weaknesses and not feedback:
            print("Failed to parse evaluation. Using fallback evaluation.")
            return get_fallback_evaluation(transcript)
        
        return {
            "score": score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": feedback,
            "raw_evaluation": evaluation
        }
    
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return get_fallback_evaluation(transcript)

def get_fallback_evaluation(transcript):
    """Generate a basic evaluation when OpenAI API is not available."""
    # Calculate a basic score based on answer length
    word_count = len(transcript.split())
    
    if word_count < 10:
        score = 30
        strengths = "- Brief response"
        weaknesses = "- Answer lacks detail and specificity\n- Response is too short"
        feedback = "Try to provide more detailed answers with specific examples from your experience."
    elif word_count < 50:
        score = 60
        strengths = "- Provided a concise answer"
        weaknesses = "- Could include more specific details"
        feedback = "Your answer is a good start. Consider expanding with specific examples or technical details."
    else:
        score = 75
        strengths = "- Provided a detailed response\n- Included specific information"
        weaknesses = "- Ensure all parts of the question are addressed"
        feedback = "Good detailed answer. Make sure you're directly addressing all aspects of the question."
    
    return {
        "score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "feedback": feedback,
        "raw_evaluation": "Fallback evaluation based on response length"
    }

def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI's Whisper API."""
    # Check if API key is available
    if not api_key or api_key == "your_openai_api_key_here":
        return "Error: OpenAI API key is not configured. Please update your .env file with a valid API key."
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None 