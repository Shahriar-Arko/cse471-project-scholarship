from app.extensions import db
import datetime

class SOPTemplate(db.Document):
    meta = {
        'collection': 'sop_templates',  # This name will appear in MongoDB
        'strict': False
    }
    
    major = db.StringField(required=True)
    url = db.StringField()
    content = db.StringField(required=True)
    embedding = db.ListField(db.FloatField())  # Vector array for RAG search
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)