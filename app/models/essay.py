from app.extensions import db
import datetime

class EssaySubmission(db.Document):
    meta = {
        'collection': 'essay_submissions',
        'strict': False
    }
    
    student = db.ReferenceField('User', required=True)
    evaluator = db.ReferenceField('Evaluator', required=True)
    title = db.StringField(required=True)
    
    # --- CHANGED: File Storage Fields instead of text content ---
    file_path = db.StringField(required=True)
    original_filename = db.StringField(required=True)
    
    status = db.StringField(default='pending', choices=['pending', 'reviewed'])
    feedback = db.StringField(null=True)
    score = db.IntField(null=True, min_value=0, max_value=10)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)