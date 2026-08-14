import datetime

from app.extensions import db


class ResumeAnalysis(db.Document):
    meta = {
        'collection': 'resume_analyses',
        'strict': False,
        'indexes': [
            {'fields': ['user', 'created_at']},
            {'fields': ['created_at']},
        ],
    }

    user = db.ReferenceField('User', required=True)
    filename = db.StringField(required=True, max_length=255)
    overall_score = db.FloatField(default=0.0)
    formatting_score = db.FloatField(default=0.0)
    academic_score = db.FloatField(default=0.0)
    skills_score = db.FloatField(default=0.0)
    completeness_score = db.FloatField(default=0.0)
    extracted_data = db.DictField(default={})
    missing_information = db.DictField(default={})
    recommendations = db.ListField(db.StringField())
    scholarship_matches = db.DictField(default={})
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
