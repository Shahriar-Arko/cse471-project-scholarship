import datetime
from app.extensions import db
from mongoengine import CASCADE

class StudentResearchProfile(db.Document):
    meta = {
        'collection': 'student_research_profiles',
        'ordering': ['-updated_at'],
        'strict': False
    }

    student = db.ReferenceField('User', required=True, unique=True, reverse_delete_rule=CASCADE)
    
    # Input Snapshot
    degree_level = db.StringField(default='Masters')
    major = db.StringField(default='Computer Science')
    cgpa = db.FloatField(default=3.5)
    research_statement = db.StringField(required=True)
    project_abstracts = db.StringField(required=True)
    technical_skills = db.ListField(db.StringField(), default=list)
    
    # AI Extracted Insights
    top_specializations = db.ListField(db.DictField(), default=list)
    identified_strengths = db.ListField(db.StringField(), default=list)
    missing_skills = db.ListField(db.StringField(), default=list)
    key_search_terms = db.ListField(db.StringField(), default=list)
    
    # 768-Dimensional Gemini Embedding Vector
    embedding = db.ListField(db.FloatField(), default=list)
    
    # Faculty Discovery Toggle
    is_visible_to_faculty = db.BooleanField(default=True)
    
    # Track professors who have already outreached to this student
    outreached_by = db.ListField(db.ReferenceField('Professor'), default=list)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.datetime.utcnow)