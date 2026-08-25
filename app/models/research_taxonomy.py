import datetime
from app.extensions import db

class ResearchTaxonomy(db.Document):
    meta = {
        'collection': 'research_taxonomies',
        'ordering': ['niche_title'],
        'strict': False
    }

    niche_title = db.StringField(required=True, unique=True)
    broad_domain = db.StringField(required=True)
    description = db.StringField(required=True)
    core_skills = db.ListField(db.StringField(), default=list)
    prerequisites = db.ListField(db.StringField(), default=list)
    
    # 768-Dimensional Gemini Embedding Vector
    embedding = db.ListField(db.FloatField(), default=list)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)