import mongomock
from flask import Flask

from app.extensions import db
from app.models.resume_analysis import ResumeAnalysis
from app.models.user import User


def _create_test_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['MONGODB_SETTINGS'] = {
        'db': 'resume_test_db',
        'host': 'mongodb://localhost:27017',
        'mongo_client_class': mongomock.MongoClient,
    }
    db.init_app(app)
    return app


def test_resume_analysis_model_can_be_created_and_retrieved():
    app = _create_test_app()
    with app.app_context():
        ResumeAnalysis.drop_collection()
        User.drop_collection()

        user = User(
            email='student@example.com',
            password='secret-password',
            full_name='Student User',
            role='student',
        )
        user.save()

        analysis = ResumeAnalysis(
            user=user,
            filename='resume.pdf',
            overall_score=84.5,
            formatting_score=80,
            academic_score=90,
            skills_score=85,
            completeness_score=82,
            extracted_data={'name': 'Student User', 'email': 'student@example.com'},
            missing_information={'required_missing': []},
            recommendations=['Add a Projects section.'],
        )
        analysis.save()

        saved = ResumeAnalysis.objects(user=user).first()

        assert saved is not None
        assert saved.filename == 'resume.pdf'
        assert saved.overall_score == 84.5
        assert saved.user.id == user.id

        all_user_analyses = ResumeAnalysis.objects(user=user)
        assert all_user_analyses.count() == 1

        second_analysis = ResumeAnalysis(
            user=user,
            filename='resume-2.pdf',
            overall_score=88,
            formatting_score=85,
            academic_score=92,
            skills_score=89,
            completeness_score=90,
            extracted_data={'name': 'Student User'},
            missing_information={'required_missing': ['email']},
            recommendations=['Add a professional email address.'],
        )
        second_analysis.save()

        assert ResumeAnalysis.objects(user=user).count() == 2
