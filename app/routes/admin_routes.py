import random
import datetime
import smtplib
import os
from email.mime.text import MIMEText
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.admin import Admin
from app.extensions import bcrypt

admin_bp = Blueprint('admin', __name__)

def send_otp_email(to_email, otp_code):
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    
    if not sender_email or not sender_password:
        print(f"\n[DEV MODE OTP] Admin Code for {to_email}: {otp_code}\n")
        return True

    try:
        msg = MIMEText(f"Your ScholarMatch Admin 2-Step Verification Code is: {otp_code}\nThis code expires in 10 minutes.")
        msg['Subject'] = 'ScholarMatch Security: Admin Login OTP'
        msg['From'] = sender_email
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and getattr(current_user, 'role', '') == 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        admin = Admin.objects(email=email).first()
        if admin and bcrypt.check_password_hash(admin.password, password):
            otp = str(random.randint(100000, 999999))
            admin.otp_code = otp
            admin.otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
            admin.save()

            session['pending_admin_id'] = str(admin.id)
            send_otp_email(admin.email, otp)
            flash('Verification code sent to your email.', 'info')
            return redirect(url_for('admin.verify_otp'))
        else:
            flash('Invalid Admin Credentials.', 'error')

    return render_template('auth/admin_login.html')

@admin_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    admin_id = session.get('pending_admin_id')
    if not admin_id:
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        admin = Admin.objects(id=admin_id).first()

        if admin and admin.otp_code == entered_otp:
            if admin.otp_expiry and datetime.datetime.utcnow() <= admin.otp_expiry:
                admin.otp_code = None
                admin.otp_expiry = None
                admin.save()

                session.pop('pending_admin_id', None)
                login_user(admin)
                flash('Secure Admin Login Successful!', 'success')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash('OTP has expired. Please log in again.', 'error')
                return redirect(url_for('admin.admin_login'))
        else:
            flash('Invalid verification code.', 'error')

    return render_template('auth/admin_verify_otp.html')

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))
    
    from app.models.user import User
    from app.models.professor import Professor
    from app.models.scholarship import Scholarship

    total_students = User.objects().count()
    total_professors = Professor.objects().count()
    total_scholarships = Scholarship.objects().count()

    # Pass actual data lists to template
    recent_students = User.objects().order_by('-id')[:10]
    recent_professors = Professor.objects().order_by('-id')[:10]
    recent_scholarships = Scholarship.objects()[:15]

    return render_template('dashboard/admin_dashboard.html', 
                           students_count=total_students, 
                           professors_count=total_professors, 
                           scholarships_count=total_scholarships,
                           recent_students=recent_students,
                           recent_professors=recent_professors,
                           scholarships=recent_scholarships)

@admin_bp.route('/delete-user/<user_type>/<user_id>', methods=['POST'])
@login_required
def delete_user(user_type, user_id):
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized action.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    from app.models.user import User
    from app.models.professor import Professor

    if user_type == 'student':
        u = User.objects(id=user_id).first()
        if u:
            u.delete()
            flash('Student account deleted.', 'info')
    elif user_type == 'professor':
        p = Professor.objects(id=user_id).first()
        if p:
            p.delete()
            flash('Professor account deleted.', 'info')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/delete-scholarship/<scholarship_id>', methods=['POST'])
@login_required
def delete_scholarship(scholarship_id):
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized action.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    from app.models.scholarship import Scholarship
    s = Scholarship.objects(id=scholarship_id).first()
    if s:
        s.delete()
        flash('Scholarship removed from database.', 'info')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/logout')
@login_required
def admin_logout():
    if getattr(current_user, 'role', '') == 'admin':
        logout_user()
    return redirect(url_for('admin.admin_login'))



@admin_bp.route('/pending-approvals')
@login_required
def pending_approvals():
    if getattr(current_user, 'role', '') != 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    
    from app.models.user import User
    pending_users = User.objects(is_approved=False)
    
    return render_template('admin/pending_approvals.html', pending_users=pending_users)

@admin_bp.route('/approve-user/<user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if getattr(current_user, 'role', '') != 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    from app.models.user import User
    user = User.objects(id=user_id).first()
    if user:
        user.is_approved = True
        user.save()
        flash(f'Successfully approved account for {user.full_name} ({user.role.capitalize()}).', 'success')
        
    return redirect(url_for('admin.pending_approvals'))





# ... (Keep existing imports and top part of the file)

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))
    
    from app.models.user import User
    from app.models.professor import Professor
    from app.models.scholarship import Scholarship
    from app.models.evaluator import Evaluator # <-- Import Evaluator

    total_students = User.objects().count()
    total_professors = Professor.objects().count()
    total_scholarships = Scholarship.objects().count()

    # --- NEW: Fetch Pending Evaluators ---
    pending_evaluators = Evaluator.objects(is_approved=False)
    pending_evaluators_count = pending_evaluators.count()

    # Pass actual data lists to template
    recent_students = User.objects().order_by('-id')[:10]
    recent_professors = Professor.objects().order_by('-id')[:10]
    recent_scholarships = Scholarship.objects()[:15]

    return render_template('dashboard/admin_dashboard.html', 
                           students_count=total_students, 
                           professors_count=total_professors, 
                           scholarships_count=total_scholarships,
                           pending_evaluators=pending_evaluators, # <-- Pass to UI
                           pending_evaluators_count=pending_evaluators_count, # <-- Pass to UI
                           recent_students=recent_students,
                           recent_professors=recent_professors,
                           scholarships=recent_scholarships)

# --- NEW: Approval Route ---
@admin_bp.route('/approve-evaluator/<evaluator_id>', methods=['POST'])
@login_required
def approve_evaluator(evaluator_id):
    if getattr(current_user, 'role', '') != 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    from app.models.evaluator import Evaluator
    evaluator = Evaluator.objects(id=evaluator_id).first()
    
    if evaluator:
        evaluator.is_approved = True
        evaluator.save()
        flash(f'Evaluator {evaluator.full_name} has been approved to log in!', 'success')
    else:
        flash('Evaluator not found.', 'error')
        
    return redirect(url_for('admin.admin_dashboard'))

# ... (Keep existing delete routes and logout route)