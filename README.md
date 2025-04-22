# AI-Powered Interview Platform

A full-stack web application that helps candidates practice interviews with AI-generated questions, speech recognition, and real-time feedback.

## Features

- **User Authentication**: Secure registration and login system
- **Customizable Profiles**: Create job profiles with specific skills and experience levels
- **Two Interview Modes**:
  - **Bulk Mode**: Generates all questions at once
  - **Interactive Mode**: Adapts questions based on previous answers
- **Speech Recognition**: Real-time transcription using the Web Speech API
- **AI Evaluation**: Get detailed feedback and scores for each answer
- **Comprehensive Reports**: View overall performance and areas for improvement
- **Export Options**: Download reports as CSV or PDF

## Technology Stack

- **Backend**: Python 3.10+ with Flask, SQLAlchemy (SQLite), and Flask-JWT-Extended
- **Frontend**: HTML/CSS (Bootstrap), Vanilla JavaScript
- **Speech-to-Text**: Web Speech API (browser-native) with Whisper API fallback
- **AI**: OpenAI API for question generation and answer evaluation

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd interview-platform
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables:

   Create a `.env` file in the project root with the following:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   DATABASE_URI=sqlite:///interview_app.db
   ```
   
   Replace `your_secret_key_here` with a strong secret key and `your_openai_api_key_here` with your OpenAI API key.

5. Initialize the database:
   ```
   flask run
   ```
   This will automatically create the database tables on first run.

### Running the Application

1. Start the development server:
   ```
   flask run
   ```

2. Access the application at `http://127.0.0.1:5000/`

## Usage Guide

1. **Register an Account**: Create a user account with your email and password
2. **Create a Profile**: Set up your professional profile with skills and experience level
3. **Start an Interview**:
   - Choose a profile
   - Select Bulk or Interactive mode
   - Choose the number of questions
4. **Answer Questions**:
   - Click "Start Speaking" to use speech recognition
   - Or type your answer manually
   - Submit your answer when ready
5. **View Results**:
   - Each answer receives an AI evaluation with scores and feedback
   - After completing all questions, view your comprehensive report
   - Export the report as needed

## PDF Export

The PDF export feature uses WeasyPrint. If you encounter issues with PDF generation, please ensure that the additional dependencies required by WeasyPrint are installed on your system. See [WeasyPrint installation documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for details.

## License

[MIT License](LICENSE)

## Acknowledgements

- OpenAI for the API services
- Bootstrap for the frontend framework
- Flask and its extensions for the backend framework 