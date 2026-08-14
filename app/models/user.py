from app.extensions import db, login_manager
from flask_login import UserMixin
import datetime
from app.models.professor import Professor
from app.models.admin import Admin
from app.models.evaluator import Evaluator  # <-- Added Evaluator import

class User(UserMixin, db.Document):
    meta = {
        'collection': 'users',
        'strict': False
    }
    
    email = db.StringField(required=True, unique=True, max_length=255)
    password = db.StringField(required=True)
    full_name = db.StringField(required=True, max_length=255)
    
    # FIXED: Added all valid roles to choices
    role = db.StringField(default='student', choices=['student', 'professor', 'evaluator', 'admin'])
    
    google_id = db.StringField(null=True)
    avatar_url = db.StringField(null=True)
    
    # --- NEW: Admin Approval & OTP Fields ---
    is_approved = db.BooleanField(default=True)
    otp_code = db.StringField(null=True)
    otp_expiry = db.DateTimeField(null=True)
    
    # Student specific fields
    gpa = db.FloatField(null=True)
    degree_level = db.StringField(null=True)
    nationality = db.StringField(null=True)
    major = db.StringField(null=True)
    tracked_scholarships = db.ListField(db.ReferenceField('Scholarship'))
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    # Inside your User model class in app/models/user.py
    is_paid = db.BooleanField(default=False)
@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.objects(id=user_id).first()
        if user:
            return user
            
        professor = Professor.objects(id=user_id).first()
        if professor:
            return professor
            
        # <-- Added Evaluator to login session loader -->
        evaluator = Evaluator.objects(id=user_id).first()
        if evaluator:
            return evaluator
            
        admin = Admin.objects(id=user_id).first()
        if admin:
            return admin
    except Exception:
        pass
    return None