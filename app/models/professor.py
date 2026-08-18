from app.extensions import db
from flask_login import UserMixin
import datetime

class Publication(db.EmbeddedDocument):
    title = db.StringField(required=True)
    year = db.IntField()
    venue = db.StringField()  # e.g., "NeurIPS 2025", "IEEE Trans. PAMI"
    citation_url = db.StringField()  # Link to Google Scholar, ArXiv, or DOI
    citations_count = db.IntField(default=0)

class GrantProject(db.EmbeddedDocument):
    title = db.StringField(required=True)
    agency = db.StringField()  # e.g., "NSF", "NIH", "Horizon Europe"
    amount = db.StringField()  # e.g., "$1.2M"
    status = db.StringField(default="Active")  # "Active", "Ongoing"

class Professor(UserMixin, db.Document):
    meta = {
        'collection': 'professors',
        'ordering': ['-created_at'],
        'strict': False
    }
    
    email = db.StringField(required=True, unique=True, max_length=255)
    password = db.StringField(required=True)
    full_name = db.StringField(required=True, max_length=255)
    title = db.StringField(default="Associate Professor")  # e.g., "Full Professor", "Assistant Professor"
    role = db.StringField(default='professor')

    is_approved = db.BooleanField(default=False)


    
    # Google Auth & Media
    google_id = db.StringField(null=True)
    avatar_url = db.StringField(null=True)

    # Institution & Location Details
    institution = db.StringField(required=True)  # e.g. "Carnegie Mellon University"
    department = db.StringField(required=True)   # e.g. "Computer Science Department"
    country = db.StringField(required=True)      # e.g. "United States"
    office_location = db.StringField(null=True)  # e.g. "Gates Center 4102"
    website_url = db.StringField(null=True)
    
    # Research Specializations
    primary_domain = db.StringField(required=True)  # e.g. "Artificial Intelligence & Robotics"
    research_interests = db.ListField(db.StringField(), default=list)  # e.g. ["Federated Learning", "Reinforcement Learning", "NLP"]
    bio_summary = db.StringField(null=True)

    # Lab & Funding Status
    lab_name = db.StringField(null=True)  # e.g. "Decentralized Intelligence Lab"
    lab_website = db.StringField(null=True)
    accepting_students = db.BooleanField(default=True)  # Actively looking for MS/PhD
    has_funding = db.BooleanField(default=True)        # Active assistantships available
    funding_types = db.ListField(db.StringField(), default=list)  # ["RA", "TA", "Fully-Funded Fellowship"]
    open_positions_count = db.IntField(default=2)

    # Publications & Ongoing Grants
    publications = db.EmbeddedDocumentListField(Publication, default=list)
    grant_projects = db.EmbeddedDocumentListField(GrantProject, default=list)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)