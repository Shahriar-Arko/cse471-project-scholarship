from app.models.user import User
from app.models.professor import Professor
from app.models.evaluator import Evaluator  # <-- Make sure this is imported!
from app.extensions import bcrypt

def register_user(email, password, full_name, role, institution=None, department=None):
    # Prevent duplicate emails across all user types
    if User.objects(email=email).first() or Professor.objects(email=email).first() or Evaluator.objects(email=email).first():
        return None, "An account with this email already exists."
        
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    
    if role == 'professor':
        user = Professor(email=email, password=hashed_pw, full_name=full_name, role=role, is_approved=False)
    elif role == 'evaluator':
        user = Evaluator(email=email, password=hashed_pw, full_name=full_name, role=role, is_approved=False)
    else:
        user = User(email=email, password=hashed_pw, full_name=full_name, role='student')
        
    user.save()
    return user, None

def authenticate_user(email, password, role):
    if role == 'professor':
        user = Professor.objects(email=email).first()
    elif role == 'evaluator':
        user = Evaluator.objects(email=email).first()
    else:
        user = User.objects(email=email).first()
        
    if not user or not bcrypt.check_password_hash(user.password, password):
        return None, "Invalid email or password."
        
    return user, None

def find_or_create_google_user(google_user_info, role):
    """Handles Google OAuth login and registration based on role."""
    email = google_user_info.get('email').lower()
    full_name = google_user_info.get('name')
    google_id = google_user_info.get('sub')
    avatar_url = google_user_info.get('picture')

    # 1. Check for Evaluator Google Login
    if role == 'evaluator':
        user = Evaluator.objects(email=email).first()
        if not user:
            # Create new Evaluator (pending approval)
            user = Evaluator(
                email=email, 
                full_name=full_name, 
                role=role, 
                google_id=google_id, 
                avatar_url=avatar_url,
                password="GOOGLE_AUTH_PLACEHOLDER", # Random placeholder since they use Google
                is_approved=False 
            )
            user.save()
        return user

    # 2. Check for Professor Google Login
    elif role == 'professor':
        user = Professor.objects(email=email).first()
        if not user:
            # Create new Professor (pending approval)
            user = Professor(
                email=email, 
                full_name=full_name, 
                role=role, 
                google_id=google_id, 
                avatar_url=avatar_url,
                password="GOOGLE_AUTH_PLACEHOLDER",
                is_approved=False
            )
            user.save()
        return user

    # 3. Check for Student Google Login (Default)
    else:
        user = User.objects(email=email).first()
        if not user:
            # Create new Student (auto-approved)
            user = User(
                email=email, 
                full_name=full_name, 
                role='student', 
                google_id=google_id, 
                avatar_url=avatar_url,
                password="GOOGLE_AUTH_PLACEHOLDER"
            )
            user.save()
        return user