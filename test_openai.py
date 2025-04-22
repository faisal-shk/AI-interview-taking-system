import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_openai_connection():
    try:
        # Create client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("Client initialized successfully")
        
        # Check if API key is valid and the connection works
        if os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
            print("Warning: You need to update the OPENAI_API_KEY in .env file with your actual key")
            return
            
        return True
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI connection...")
    result = test_openai_connection()
    print(f"Test {'succeeded' if result else 'failed'}") 