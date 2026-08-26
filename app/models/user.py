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
    
    # --- PROFESSOR PIPELINE / BOOKMARKS ---
    bookmarked_professors = db.ListField(db.ReferenceField('Professor'), default=list)
    
    # --- FREEMIUM & PAYMENT TRACKING FIELDS ---
    is_paid = db.BooleanField(default=False)
    sop_generations_count = db.IntField(default=0)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    from app.models.professor import Professor
    from app.models.evaluator import Evaluator
    from app.models.admin import Admin

    # Check Student collection
    user = User.objects(id=user_id).first()
    if user: return user
    
    # Check Professor collection
    prof = Professor.objects(id=user_id).first()
    if prof: return prof
    
    # Check Evaluator collection (THIS IS LIKELY WHAT YOU WERE MISSING)
    evaluator = Evaluator.objects(id=user_id).first()
    if evaluator: return evaluator

    # Check Admin collection
    admin = Admin.objects(id=user_id).first()
    if admin: return admin

    return None