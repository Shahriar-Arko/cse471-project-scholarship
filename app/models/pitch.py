import datetime
from app.extensions import db
from mongoengine import CASCADE

class ResearchPitch(db.Document):
    meta = {
        'collection': 'research_pitches',
        'ordering': ['-created_at'],
        'strict': False
    }
    
    # Relationships
    student = db.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    professor = db.ReferenceField('Professor', required=True, reverse_delete_rule=CASCADE)
    
    # Application Data
    target_domain = db.StringField(required=True)
    pitch_text = db.StringField(required=True, max_length=1500) # Forces concise pitches
    
    # Status Pipeline: pending, shortlisted, declined
    status = db.StringField(default='pending', choices=['pending', 'shortlisted', 'declined'])
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)