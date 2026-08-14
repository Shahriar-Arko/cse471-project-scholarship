from flask import Flask, redirect, url_for, render_template
from .extensions import db, login_manager, bcrypt
from flask_login import login_required, current_user
import os

def create_app(config_name='development'):
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
    app.config['MONGODB_SETTINGS'] = {
        'host': 'mongodb+srv://Admin:admin123@cluster0.1jknqf7.mongodb.net/scholarship_matcher?retryWrites=true&w=majority'
    }

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    try:
        bcrypt.init_app(app)
    except Exception:
        pass
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Auto-seed a Master Admin if one doesn't exist
    with app.app_context():
        from app.models.admin import Admin
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@scholarmatch.com')
        if not Admin.objects(email=admin_email).first():
            hashed_pw = bcrypt.generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'SecureAdmin123!')).decode('utf-8')
            Admin(email=admin_email, password=hashed_pw, full_name="System Administrator", role="admin").save()

    # Register Blueprints
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # This line automatically loads the app/routes/student/__init__.py file!
    from .routes.student import student_bp
    app.register_blueprint(student_bp)

    # REGISTER MODULAR ADMIN PACKAGE
    from .routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    # REGISTER SOP GENERATOR BLUEPRINT
    from .routes.student.sop_routes import sop_bp
    app.register_blueprint(sop_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
        
    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        if current_user.role == 'professor':
            return redirect(url_for('professor_dashboard'))
        return redirect(url_for('student_dashboard'))
        
    @app.route('/dashboard/student')
    @login_required
    def student_dashboard():
        if current_user.role != 'student':
            return redirect(url_for('dashboard'))
        return render_template('dashboard/student_dashboard.html')

    @app.route('/dashboard/professor')
    @login_required
    def professor_dashboard():
        if current_user.role != 'professor':
            return redirect(url_for('dashboard'))
        return render_template('dashboard/professor_dashboard.html')

    return app