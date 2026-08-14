from app.extensions import db, login_manager
from flask_login import UserMixin
import datetime
from app.models.professor import Professor
from app.models.admin import Admin

class User(UserMixin, db.Document):
    meta = {
        'collection': 'users',
        'strict': False
    }
    
    email = db.StringField(required=True, unique=True, max_length=255)
    password = db.StringField(required=True)
    full_name = db.StringField(required=True, max_length=255)
    role = db.StringField(default='student')
    google_id = db.StringField(null=True)
    avatar_url = db.StringField(null=True)
    
    gpa = db.FloatField(null=True)
    degree_level = db.StringField(null=True)
    nationality = db.StringField(null=True)
    major = db.StringField(null=True)
    tracked_scholarships = db.ListField(db.ReferenceField('Scholarship'))
    
    # --- FREEMIUM & PAYMENT TRACKING FIELDS ---
    is_paid = db.BooleanField(default=False)
    sop_generations_count = db.IntField(default=0)
    
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
            
        admin = Admin.objects(id=user_id).first()
        if admin:
            return admin
    except Exception:
        pass
    return None