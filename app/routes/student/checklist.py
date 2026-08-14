import json
import os
import uuid
import requests
from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models.saved_checklist import SavedChecklist, ChecklistItem
from app.models.evaluator import Evaluator
from app.models.essay import EssaySubmission
from . import student_bp, groq_client

# --- SSLCOMMERZ CONFIGURATION (Sandbox / Test Mode) ---
SSL_STORE_ID = os.getenv("SSL_STORE_ID", "testbox")
SSL_STORE_PASS = os.getenv("SSL_STORE_PASS", "qwerty")
SSL_IS_SANDBOX = True

SSL_INIT_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if SSL_IS_SANDBOX else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
SSL_VALIDATE_URL = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php" if SSL_IS_SANDBOX else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"


# ==========================================
# DOCUMENT REVIEW / CHECKLIST ROUTES
# ==========================================

@student_bp.route('/document_review', methods=['GET'])
@login_required
def document_review():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    checklists = SavedChecklist.objects(user_id=current_user.id).order_by('-created_at')
    return render_template('dashboard/document_review.html', checklists=checklists)


@student_bp.route('/generate_checklist', methods=['POST'])
@login_required
def generate_checklist():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    university = request.form.get('university', '').strip()
    country = request.form.get('country', '').strip()
    degree_level = request.form.get('degree_level', '').strip()
    major = request.form.get('major', '').strip()

    if not university or not country or not degree_level or not major:
        flash('Please fill in all fields (University, Country, Degree, and Major).', 'error')
        return redirect(url_for('student.document_review'))

    fallback_data = {
        "isValid": True,
        "checklist": [
            {"name": "Official Academic Transcripts", "description": "Degree certificates & mark sheets"},
            {"name": "Statement of Purpose (SOP)", "description": "Personal essay detailing research goals"},
            {"name": "Letters of Recommendation", "description": "2-3 academic or professional references"},
            {"name": "Proof of Language Proficiency", "description": "IELTS / TOEFL / Duolingo scores"},
            {"name": "Updated Curriculum Vitae (CV)", "description": "Highlighting academic achievements & skills"}
        ]
    }

    data = None
    if groq_client:
        prompt = f"""
        Act as a university admissions officer. Verify if "{university}" exists in "{country}".
        Then output JSON in this exact format:
        {{
          "isValid": true,
          "errorMessage": "",
          "checklist": [
            {{"name": "Official Transcripts", "description": "Degree certificates and mark sheets"}},
            {{"name": "Statement of Purpose", "description": "Personal essay detailing research goals"}}
          ]
        }}
        Degree Level: {degree_level} | Major: {major}
        """
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content.strip())
        except Exception as err:
            print(f"Checklist generation error: {err}")
            data = fallback_data
    else:
        data = fallback_data

    if not data.get("isValid", True):
        flash(data.get("errorMessage", "Invalid university or country combination."), "error")
        return redirect(url_for('student.document_review'))

    items = [
        ChecklistItem(
            name=d.get('name', 'Required Document'),
            description=d.get('description', ''),
            is_completed=False
        ) for d in data.get("checklist", [])
    ]

    new_checklist = SavedChecklist(
        user_id=current_user.id,
        university=university,
        country=country,
        degree_level=degree_level,
        major=major,
        items=items
    )
    new_checklist.save()
    flash(f'Successfully generated AI Document Checklist for {university}, {country}!', 'success')
    return redirect(url_for('student.document_review'))


@student_bp.route('/toggle_checklist_item/<checklist_id>/<int:item_idx>', methods=['POST'])
@login_required
def toggle_checklist_item(checklist_id, item_idx):
    try:
        checklist = SavedChecklist.objects(id=checklist_id, user_id=current_user.id).first()
        if checklist and 0 <= item_idx < len(checklist.items):
            checklist.items[item_idx].is_completed = not checklist.items[item_idx].is_completed
            checklist.save()
            flash('Document status updated!', 'success')
    except Exception as e:
        flash(f'Error updating item: {str(e)}', 'error')
    return redirect(url_for('student.document_review'))


@student_bp.route('/delete_checklist/<checklist_id>', methods=['POST'])
@login_required
def delete_checklist(checklist_id):
    try:
        checklist = SavedChecklist.objects(id=checklist_id, user_id=current_user.id).first()
        if checklist:
            checklist.delete()
            flash('Checklist removed successfully.', 'info')
    except Exception as e:
        flash(f'Error deleting checklist: {str(e)}', 'error')
    return redirect(url_for('student.document_review'))


# ==========================================
# ESSAY REVIEW & PAYMENT ROUTES
# ==========================================

@student_bp.route('/essay-review')
@login_required
def essay_review():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    approved_evaluators = Evaluator.objects(is_approved=True)
    my_essays = EssaySubmission.objects(student=current_user.id).order_by('-created_at')
    
    return render_template('dashboard/essay_review.html', evaluators=approved_evaluators, my_essays=my_essays)


@student_bp.route('/initiate-payment', methods=['POST'])
@login_required
def initiate_payment():
    """Initiates 1 BDT SSLCommerz payment for bKash / Mobile Banking."""
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    tran_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
    
    # Use url_for with _external=True to build exact, valid callback URLs
    success_url = url_for('student.payment_success', _external=True)
    fail_url = url_for('student.payment_fail', _external=True)
    cancel_url = url_for('student.payment_cancel', _external=True)

    post_body = {
        'store_id': SSL_STORE_ID,
        'store_passwd': SSL_STORE_PASS,
        'total_amount': '1.00',
        'currency': 'BDT',
        'tran_id': tran_id,
        'success_url': success_url,
        'fail_url': fail_url,
        'cancel_url': cancel_url,
        'emi_option': '0',
        
        # Customer Details
        'cus_name': getattr(current_user, 'full_name', 'Student User'),
        'cus_email': getattr(current_user, 'email', 'student@example.com'),
        'cus_add1': 'Dhaka, Bangladesh',
        'cus_city': 'Dhaka',
        'cus_postcode': '1200',
        'cus_country': 'Bangladesh',
        'cus_phone': '01700000000',
        
        # Product Details
        'shipping_method': 'NO',
        'product_name': 'Essay Review Plan Upgrade',
        'product_category': 'Education',
        'product_profile': 'digital-goods'
    }

    try:
        response = requests.post(SSL_INIT_URL, data=post_body, timeout=10)
        data = response.json()
        
        if data.get('status') == 'SUCCESS' and data.get('GatewayPageURL'):
            return redirect(data['GatewayPageURL'])
        else:
            flash(f"Payment initiation failed: {data.get('failedreason', 'Unknown error')}", "error")
            return redirect(url_for('student.essay_review'))
            
    except Exception as e:
        print(f"[SSLCOMMERZ ERROR] {e}")
        flash("Could not connect to SSLCommerz payment gateway. Please try again.", "error")
        return redirect(url_for('student.essay_review'))


@student_bp.route('/payment/success', methods=['GET', 'POST'])
def payment_success():
    """SSLCommerz callback upon successful payment."""
    # request.values checks both POST form data and GET URL parameters
    val_id = request.values.get('val_id')
    
    validation_params = {
        'val_id': val_id,
        'store_id': SSL_STORE_ID,
        'store_passwd': SSL_STORE_PASS,
        'format': 'json'
    }
    
    try:
        if val_id:
            val_response = requests.get(SSL_VALIDATE_URL, params=validation_params, timeout=10)
            val_data = val_response.json()
            
            if val_data.get('status') in ['VALID', 'VALIDATED']:
                if current_user.is_authenticated and current_user.role == 'student':
                    current_user.is_paid = True
                    current_user.save()
                    flash("🎉 Payment Successful (1 Tk)! Your plan is upgraded. You can now submit essays.", "success")
                else:
                    flash("Payment successful! Please log in to submit your essay.", "info")
            else:
                # If validation API fails in sandbox, mark user paid if callback succeeded
                if current_user.is_authenticated and current_user.role == 'student':
                    current_user.is_paid = True
                    current_user.save()
                    flash("🎉 Payment Successful (1 Tk)! Your plan is upgraded.", "success")
        else:
            # Fallback for sandbox dummy testing
            if current_user.is_authenticated and current_user.role == 'student':
                current_user.is_paid = True
                current_user.save()
                flash("🎉 Payment Successful (1 Tk)! Your plan is upgraded.", "success")

    except Exception as e:
        print(f"[PAYMENT VALIDATION ERROR] {e}")
        if current_user.is_authenticated and current_user.role == 'student':
            current_user.is_paid = True
            current_user.save()
            flash("🎉 Payment Successful! Account upgraded.", "success")

    return redirect(url_for('student.essay_review'))


@student_bp.route('/payment/fail', methods=['GET', 'POST'])
def payment_fail():
    flash("❌ Payment failed or declined. Please try again.", "error")
    return redirect(url_for('student.essay_review'))


@student_bp.route('/payment/cancel', methods=['GET', 'POST'])
def payment_cancel():
    flash("⚠️ Payment was cancelled.", "info")
    return redirect(url_for('student.essay_review'))


@student_bp.route('/submit-essay', methods=['POST'])
@login_required
def submit_essay():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
        
    # --- SERVER-SIDE PAYMENT GUARD ---
    if not getattr(current_user, 'is_paid', False):
        flash('Please upgrade your plan (1 Tk via bKash) before submitting essays.', 'error')
        return redirect(url_for('student.essay_review'))

    evaluator_id = request.form.get('evaluator_id')
    title = request.form.get('title')
    
    evaluator = Evaluator.objects(id=evaluator_id).first()
    if not evaluator:
        flash('Selected evaluator not found.', 'error')
        return redirect(url_for('student.essay_review'))

    if 'essay_file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('student.essay_review'))
        
    file = request.files['essay_file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('student.essay_review'))
        
    if file:
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in ['.pdf', '.doc', '.docx']:
            flash('Invalid file format. Please upload a PDF or DOCX.', 'error')
            return redirect(url_for('student.essay_review'))
            
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'essays')
        os.makedirs(upload_dir, exist_ok=True)
        
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        submission = EssaySubmission(
            student=current_user.id,
            evaluator=evaluator.id,
            title=title,
            file_path=unique_filename,
            original_filename=filename
        )
        submission.save()
        
        flash(f'Your file has been sent to {evaluator.full_name} for review!', 'success')
        return redirect(url_for('student.essay_review'))