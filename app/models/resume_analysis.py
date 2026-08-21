import datetime

from app.extensions import db


class ResumeAnalysis(db.Document):
    meta = {'collection': 'resume_analyses', 'strict': False}

    user_id = db.ReferenceField('User', required=True)
    file_name = db.StringField(required=True)
    file_path = db.StringField()
    extracted_text = db.StringField(default='')
    overall_summary = db.StringField(default='')
    strengths = db.ListField(db.StringField(), default=list)
    improvements = db.ListField(db.StringField(), default=list)
    technical_skills = db.ListField(db.StringField(), default=list)
    keywords = db.ListField(db.StringField(), default=list)
    recommendations = db.ListField(db.StringField(), default=list)
    ats_score = db.IntField(default=0)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
