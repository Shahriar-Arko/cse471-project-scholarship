from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import register_user, authenticate_user, find_or_create_google_user
from app.models.user import User
import requests
import os
import random
import smtplib
from email.message import EmailMessage
import threading

auth_bp = Blueprint('auth', __name__)

RESTRICTED_BRACU_DOMAIN = "@g.bracu.ac.bd"

def send_otp_email_async(user_email, otp_code):
    try:
        sender_email = os.environ.get('MAIL_USERNAME')
        sender_password = os.environ.get('MAIL_PASSWORD')
        
        if not sender_email or not sender_password:
            print("Email failed: MAIL_USERNAME or MAIL_PASSWORD missing in .env")
            return

        msg = EmailMessage()
        msg['Subject'] = "Your ScholarMatch Login Verification Code"
        msg['From'] = f"ScholarMatch Security <{sender_email}>"
        msg['To'] = user_email
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px; background-color: #f8fafc;">
            <h2 style="color: #4f46e5; text-align: center;">ScholarMatch Security</h2>
            <p style="color: #334155; font-size: 16px;">Hello,</p>
            <p style="color: #334155; font-size: 16px;">Please use the verification code below to securely log into your account:</p>
            <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; border: 2px dashed #cbd5e1;">
                <span style="font-size: 32px; font-weight: bold; color: #0f172a; letter-spacing: 4px;">{otp_code}</span>
            </div>
            <p style="color: #64748b; font-size: 14px; text-align: center;">This code will expire shortly. If you did not request this, please ignore this email.</p>
        </div>
        """
        
        msg.set_content("Your OTP is: " + otp_code)
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            
    except Exception as e:
        print(f"Background OTP email failed: {e}")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        remember = True if request.form.get('remember') else False

        if role == 'professor' and not email.endswith(RESTRICTED_BRACU_DOMAIN):
            flash(f"Only official '{RESTRICTED_BRACU_DOMAIN}' emails can log in as a Professor.", 'error')
            return render_template('auth/login.html')

        if role == 'student' and email.endswith(RESTRICTED_BRACU_DOMAIN):
            flash(f"'{RESTRICTED_BRACU_DOMAIN}' emails are reserved for Professors.", 'error')
            return render_template('auth/login.html')

        user, error = authenticate_user(email, password, role)
        if user:
            # Check Admin Approval for Evaluators and Professors
            if getattr(user, 'is_approved', True) is False:
                flash('Your profile request is currently pending Admin approval.', 'warning')
                return redirect(url_for('auth.login'))
            
            # OTP trigger for Students and Evaluators
            if role in ['student', 'evaluator']:
                otp_code = str(random.randint(100000, 999999))
                session['pending_otp'] = otp_code
                session['pending_user_id'] = str(user.id)
                session['pending_remember'] = remember
                
                threading.Thread(target=send_otp_email_async, args=(user.email, otp_code)).start()
                
                flash('Please check your email for the 6-digit verification code.', 'info')
                return redirect(url_for('auth.verify_otp'))
            else:
                login_user(user, remember=remember)
                return redirect(url_for('dashboard'))
        else:
            flash(error, 'error')

    return render_template('auth/login.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if 'pending_user_id' not in session or 'pending_otp' not in session:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        
        if entered_otp == session.get('pending_otp'):
            user = User.objects(id=session.get('pending_user_id')).first()
            if user:
                remember = session.get('pending_remember', False)
                login_user(user, remember=remember)
                
                session.pop('pending_otp', None)
                session.pop('pending_user_id', None)
                session.pop('pending_remember', None)
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('User not found. Please try again.', 'error')
                return redirect(url_for('auth.login'))
        else:
            flash('Invalid verification code. Please try again.', 'error')

    return render_template('auth/verify_otp.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'student')
        institution = request.form.get('institution')
        department = request.form.get('department')

        if role == 'professor' and not email.endswith(RESTRICTED_BRACU_DOMAIN):
            flash(f"Professors must register using an official email ending in '{RESTRICTED_BRACU_DOMAIN}'.", 'error')
            return render_template('auth/register.html')

        if role == 'student' and email.endswith(RESTRICTED_BRACU_DOMAIN):
            flash(f"'{RESTRICTED_BRACU_DOMAIN}' emails cannot be registered as Student accounts.", 'error')
            return render_template('auth/register.html')

        user, error = register_user(email, password, full_name, role, institution, department)
        
        if user:
            # Set to False to require admin approval
            if role in ['evaluator', 'professor']:
                user.is_approved = False
                user.save()
                flash('Registration successful! Your request is pending Admin approval.', 'info')
                return redirect(url_for('auth.login'))

            flash('Registration complete! Please log in to securely access your account.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'error')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/google/login')
def google_login():
    google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not google_client_id or google_client_id == 'your-google-client-id':
        flash('Google Login is not configured yet. Please set it up in .env', 'error')
        return redirect(url_for('auth.login'))
        
    role = request.args.get('role', 'student')
    session['oauth_role'] = role
        
    redirect_uri = url_for('auth.google_callback', _external=True)
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={google_client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile&prompt=consent"
    
    return redirect(google_auth_url)


@auth_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        flash('Google Login was cancelled.', 'error')
        return redirect(url_for('auth.login'))
        
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'code': code,
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        'redirect_uri': url_for('auth.google_callback', _external=True),
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(token_url, data=data)
    token_info = response.json()
    
    if 'access_token' not in token_info:
        flash('Failed to connect to Google.', 'error')
        return redirect(url_for('auth.login'))
        
    access_token = token_info.get('access_token')
    
    user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    user_info_response = requests.get(user_info_url, headers=headers)
    google_user_info = user_info_response.json()
    
    role = session.get('oauth_role', 'student')
    email = google_user_info.get('email', '').lower()

    if role == 'professor' and not email.endswith(RESTRICTED_BRACU_DOMAIN):
        flash(f"Access denied. Only official BRACU emails ('{RESTRICTED_BRACU_DOMAIN}') can log in as a Professor.", 'error')
        return redirect(url_for('auth.login'))

    if role == 'student' and email.endswith(RESTRICTED_BRACU_DOMAIN):
        flash(f"Access denied. '{RESTRICTED_BRACU_DOMAIN}' emails are restricted from logging in as a Student.", 'error')
        return redirect(url_for('auth.login'))
    
    try:
        user = find_or_create_google_user(google_user_info, role)
        
        # Make sure users created via Google OAuth respect the admin approval rule 
        if role in ['evaluator', 'professor'] and getattr(user, 'is_approved', True) is False:
            flash('Your profile is currently pending Admin approval.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=True)
        flash(f"Welcome, {user.full_name}!", "success")
        return redirect(url_for('dashboard'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('auth.login'))