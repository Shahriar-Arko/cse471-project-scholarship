import os
from flask import Blueprint
from google import genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Create the master Blueprint
student_bp = Blueprint('student', __name__, url_prefix='/student')

# Initialize AI Clients centrally so they are only created once
gemini_api_key = os.environ.get('GEMINI_API_KEY')
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

groq_api_key = os.environ.get('GROQ_API_KEY')
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Import all the separate route files (Must be placed at the bottom to avoid circular imports)
from . import scholarship_discovery, app_tracker, checklist, chatbot, resume_analyzer