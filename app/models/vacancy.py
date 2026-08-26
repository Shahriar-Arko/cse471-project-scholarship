import datetime
from app.extensions import db
from mongoengine import CASCADE

class Vacancy(db.Document):
    meta = {
        'collection': 'lab_vacancies',
        'ordering': ['-created_at'],
        'strict': False
    }

    professor = db.ReferenceField('Professor', required=True, reverse_delete_rule=CASCADE)
    title = db.StringField(required=True, max_length=255)
    position_type = db.StringField(required=True, choices=['RA', 'TA', 'PostDoc', 'PhD Position', 'Graduate Researcher'])
    department = db.StringField(required=True)
    domain = db.StringField(required=True)
    funding_stipend = db.StringField(required=True)  # e.g. "$2,500/month + Tuition Waiver"
    openings_count = db.IntField(default=1)
    min_cgpa = db.FloatField(default=3.0)
    target_degrees = db.ListField(db.StringField(), default=list)  # ['Bachelors', 'Masters', 'PhD']
    required_skills = db.ListField(db.StringField(), default=list)
    description = db.StringField(required=True)
    responsibilities = db.StringField(null=True)
    deadline = db.DateTimeField(null=True)
    is_active = db.BooleanField(default=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)


class VacancyApplication(db.Document):
    meta = {
        'collection': 'vacancy_applications',
        'ordering': ['-created_at'],
        'strict': False
    }

    vacancy = db.ReferenceField('Vacancy', required=True, reverse_delete_rule=CASCADE)
    student = db.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    professor = db.ReferenceField('Professor', required=True, reverse_delete_rule=CASCADE)
    cover_letter = db.StringField(required=True)
    
    # List of uploaded documents (Max 3): [{'name': 'transcript.pdf', 'url': '/static/uploads/...'}]
    documents = db.ListField(db.DictField(), default=list)
    
    # Snapshot of student stats at application time
    applicant_cgpa = db.FloatField(null=True)
    applicant_major = db.StringField(null=True)
    applicant_degree = db.StringField(null=True)
    
    # Recruitment Pipeline: Submitted, Under Review, Shortlisted, Offered, Rejected
    status = db.StringField(
        default='Submitted',
        choices=['Submitted', 'Under Review', 'Shortlisted', 'Offered', 'Rejected']
    )
    faculty_notes = db.StringField(null=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)