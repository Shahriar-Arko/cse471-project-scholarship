from app.extensions import db
from flask_login import UserMixin
import datetime

class Evaluator(UserMixin, db.Document):
    meta = {
        'collection': 'evaluators',
        'strict': False
    }
    
    email = db.StringField(required=True, unique=True, max_length=255)
    password = db.StringField(required=True)
    full_name = db.StringField(required=True, max_length=255)
    role = db.StringField(default='evaluator')
    
    # OAuth Fields
    google_id = db.StringField(null=True)
    avatar_url = db.StringField(null=True)
    
    # Admin Approval & OTP Fields
    is_approved = db.BooleanField(default=False) 
    otp_code = db.StringField(null=True)
    otp_expiry = db.DateTimeField(null=True)
    
    # --- NEW: Profile Fields ---
    university = db.StringField(null=True)
    major = db.StringField(null=True)
    experience = db.StringField(null=True)
    nationality = db.StringField(null=True)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)