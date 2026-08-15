import os

import mongomock
from flask import Flask

from app.extensions import db, login_manager
from app.models.resume_analysis import ResumeAnalysis
from app.models.user import User
from app.routes.student import student_bp


def _create_test_app():
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['TESTING'] = True
    app.config['MONGODB_SETTINGS'] = {
        'db': 'resume_test_db_auth',
        'host': 'mongodb://localhost:27017',
        'mongo_client_class': mongomock.MongoClient,
    }

    db.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(student_bp)

    @app.route('/dashboard')
    def dashboard():
        return 'dashboard'

    login_manager.login_view = 'auth.login'
    return app


def _login_client(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def test_student_can_view_own_resume_analysis_detail():
    app = _create_test_app()
    with app.app_context():
        User.drop_collection()
        ResumeAnalysis.drop_collection()

        student = User(
            email='student@example.com',
            password='password123',
            full_name='Student User',
            role='student',
        )
        student.save()

        analysis = ResumeAnalysis(
            user=student,
            filename='student_resume.pdf',
            overall_score=87.5,
            formatting_score=85,
            academic_score=90,
            skills_score=88,
            completeness_score=86,
            extracted_data={'name': 'Student User', 'skills': ['Python', 'Flask']},
            missing_information={'required_missing': []},
            recommendations=['Add a projects section.'],
        )
        analysis.save()

        with app.test_client() as client:
            _login_client(client, student)
            response = client.get(f'/student/resume_analyzer/{analysis.id}')

            assert response.status_code == 200
            assert b'student_resume.pdf' in response.data
            assert b'Resume Analysis Details' in response.data


def test_student_cannot_view_another_students_resume_analysis_detail():
    app = _create_test_app()
    with app.app_context():
        User.drop_collection()
        ResumeAnalysis.drop_collection()

        owner = User(
            email='owner@example.com',
            password='password123',
            full_name='Owner User',
            role='student',
        )
        owner.save()

        attacker = User(
            email='attacker@example.com',
            password='password123',
            full_name='Attacker User',
            role='student',
        )
        attacker.save()

        analysis = ResumeAnalysis(
            user=owner,
            filename='other_resume.pdf',
            overall_score=91,
            formatting_score=90,
            academic_score=95,
            skills_score=92,
            completeness_score=89,
            extracted_data={'name': 'Owner User'},
            missing_information={'required_missing': []},
            recommendations=['Keep the resume concise.'],
        )
        analysis.save()

        with app.test_client() as client:
            _login_client(client, attacker)
            response = client.get(f'/student/resume_analyzer/{analysis.id}', follow_redirects=False)

            assert response.status_code == 302
            assert response.headers['Location'].endswith('/student/resume_analyzer')


def test_non_student_cannot_access_resume_analysis_detail_route():
    app = _create_test_app()
    with app.app_context():
        User.drop_collection()
        ResumeAnalysis.drop_collection()

        professor = User(
            email='professor@example.com',
            password='password123',
            full_name='Professor User',
            role='professor',
        )
        professor.save()

        with app.test_client() as client:
            _login_client(client, professor)
            response = client.get('/student/resume_analyzer/does-not-matter', follow_redirects=False)

            assert response.status_code == 302
            assert response.headers['Location'].endswith('/dashboard')
