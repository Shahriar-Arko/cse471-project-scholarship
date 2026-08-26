from flask import Flask, app, redirect, url_for, render_template, request, flash
from .extensions import db, login_manager, bcrypt
from flask_login import login_required, current_user
import os
from flask import Flask, redirect, url_for, render_template, request, flash
from flask import send_from_directory




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

    from app.routes.professor_routes import professor_bp
    # ... inside your create_app() function ...
    app.register_blueprint(professor_bp)

    from app.routes.forum_routes import forum_bp
    app.register_blueprint(forum_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
        
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # --- ADD THIS INTERCEPTOR ---
        if current_user.role == 'professor':
            if getattr(current_user, 'institution', '') == "Pending Configuration":
                flash("Please complete your academic profile to continue.", "info")
                return redirect(url_for('professor.setup_profile'))
            return render_template('dashboard/professor_dashboard.html')
        # ----------------------------

        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
            
        # ADD THIS: Properly route Evaluators
        if current_user.role == 'evaluator':
            return redirect(url_for('evaluator_dashboard'))
        
        # Otherwise, render student dashboard
        return render_template('dashboard/student_dashboard.html')



    from app.routes.student.analyzer_routes import analyzer_bp
    app.register_blueprint(analyzer_bp)
        
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

    @app.route('/dashboard/evaluator')
    @login_required
    def evaluator_dashboard():
        if current_user.role != 'evaluator':
            return redirect(url_for('dashboard'))
            
        from app.models.essay import EssaySubmission
        
        # Fetch all essays assigned to this specific evaluator object
        assigned_essays = EssaySubmission.objects(evaluator=current_user).order_by('-created_at')
        
        return render_template(
            'evaluators/evaluator_dashboard.html', 
            assigned_essays=assigned_essays
        )



    @app.route('/evaluate-essay/<essay_id>', methods=['POST'])
    @login_required
    def evaluate_essay(essay_id):
        if current_user.role != 'evaluator':
            flash('Unauthorized access.', 'error')
            return redirect(url_for('dashboard'))
            
        from app.models.essay import EssaySubmission
        essay = EssaySubmission.objects(id=essay_id, evaluator=current_user.id).first()
        
        if not essay:
            flash('Essay not found.', 'error')
            return redirect(url_for('evaluator_dashboard'))
            
        # Get data from the form
        score = request.form.get('score')
        feedback = request.form.get('feedback')
        
        if score and feedback:
            essay.score = int(score)
            essay.feedback = feedback
            essay.status = 'reviewed'
            essay.save()
            flash('Evaluation submitted successfully!', 'success')
            
        return redirect(url_for('evaluator_dashboard'))

    @app.route('/evaluator/edit-profile', methods=['GET', 'POST'])
    @login_required
    def edit_evaluator_profile():
        if current_user.role != 'evaluator':
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            # Get data from the form and update the database
            current_user.full_name = request.form.get('full_name')
            current_user.university = request.form.get('university')
            current_user.major = request.form.get('major')
            current_user.experience = request.form.get('experience')
            current_user.nationality = request.form.get('nationality')
            current_user.save()
            
            flash('Profile successfully updated!', 'success')
            return redirect(url_for('evaluator_dashboard'))
            
        return render_template('evaluators/edit_profile.html')


    @app.route('/download-essay/<essay_id>')
    @login_required
    def download_essay(essay_id):
        # Security check: only the assigned evaluator can download it
        if current_user.role != 'evaluator':
            flash('Unauthorized access.', 'error')
            return redirect(url_for('dashboard'))
            
        from app.models.essay import EssaySubmission
        essay = EssaySubmission.objects(id=essay_id, evaluator=current_user.id).first()
        
        if not essay:
            flash('Essay not found.', 'error')
            return redirect(url_for('evaluator_dashboard'))
            
        upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'essays')
        
        # as_attachment=False allows PDFs to preview in the browser!
        # DOCX files will automatically download.
        return send_from_directory(upload_dir, essay.file_path, as_attachment=False, download_name=essay.original_filename)

    return app