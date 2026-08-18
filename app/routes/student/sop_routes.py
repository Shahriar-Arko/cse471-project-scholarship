import os
import uuid
import requests
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.sop_generator import generate_custom_sop

sop_bp = Blueprint('sop', __name__)

# --- SSLCOMMERZ CONFIGURATION (Sandbox / Test Mode) ---
SSL_STORE_ID = os.getenv("SSL_STORE_ID", "testbox")
SSL_STORE_PASS = os.getenv("SSL_STORE_PASS", "qwerty")
SSL_IS_SANDBOX = True

SSL_INIT_URL = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if SSL_IS_SANDBOX else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
SSL_VALIDATE_URL = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php" if SSL_IS_SANDBOX else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"


@sop_bp.route('/sop-generator', methods=['GET'])
@login_required
def sop_generator_page():
    return render_template('dashboard/sop_generator.html')


@sop_bp.route('/api/generate-sop', methods=['POST'])
@login_required
def api_generate_sop():
    data = request.get_json() or {}
    
    if not data.get('major') or not data.get('user_prompt'):
        return jsonify({'error': 'Please provide both your Target Major and Profile/Prompt details.'}), 400
        
    # --- FREEMIUM CHECK ---
    is_paid = getattr(current_user, 'is_paid', False)
    gen_count = getattr(current_user, 'sop_generations_count', 0)
    
    # Block generation on 3rd attempt if unpaid
    if not is_paid and gen_count >= 2:
        return jsonify({
            'status': 'payment_required',
            'error': 'You have used your 2 free SOP generations. Upgrade your plan (1 Tk via bKash) for unlimited generations.'
        }), 402

    try:
        generated_sop = generate_custom_sop(data)
        
        # Increment counter for free users
        if not is_paid:
            current_user.sop_generations_count = gen_count + 1
            current_user.save()
            
        updated_count = getattr(current_user, 'sop_generations_count', 0)
        
        return jsonify({
            'status': 'success', 
            'sop': generated_sop,
            'generations_count': updated_count,
            'is_paid': is_paid
        }), 200
    except Exception as e:
        print(f"SOP Generation Error: {e}")
        return jsonify({'error': 'Failed to generate SOP. Please try again.'}), 500


# ==========================================
# SSLCOMMERZ PAYMENT ROUTES
# ==========================================

@sop_bp.route('/initiate-payment', methods=['POST'])
@login_required
def initiate_payment():
    """Initiates 1 BDT SSLCommerz payment for bKash / Mobile Banking."""
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    tran_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
    
    # Build dynamic callback URLs for sop_bp endpoints
    success_url = url_for('sop.payment_success', _external=True)
    fail_url = url_for('sop.payment_fail', _external=True)
    cancel_url = url_for('sop.payment_cancel', _external=True)

    post_body = {
        'store_id': SSL_STORE_ID,
        'store_passwd': SSL_STORE_PASS,
        'total_amount': '1.00',  # 1 BDT fee
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
        'product_name': 'ScholarMatch Pro Upgrade',
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
            return redirect(url_for('sop.sop_generator_page'))
            
    except Exception as e:
        print(f"[SSLCOMMERZ ERROR] {e}")
        flash("Could not connect to SSLCommerz payment gateway. Please try again.", "error")
        return redirect(url_for('sop.sop_generator_page'))


@sop_bp.route('/payment/success', methods=['GET', 'POST'])
def payment_success():
    """SSLCommerz callback upon successful bKash payment."""
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
                    flash("🎉 Payment Successful (1 Tk)! Your plan is upgraded to Unlimited.", "success")
                else:
                    flash("Payment successful! Please log in.", "info")
            else:
                if current_user.is_authenticated and current_user.role == 'student':
                    current_user.is_paid = True
                    current_user.save()
                    flash("🎉 Payment Successful (1 Tk)! Account upgraded.", "success")
        else:
            if current_user.is_authenticated and current_user.role == 'student':
                current_user.is_paid = True
                current_user.save()
                flash("🎉 Payment Successful (1 Tk)! Account upgraded.", "success")

    except Exception as e:
        print(f"[PAYMENT VALIDATION ERROR] {e}")
        if current_user.is_authenticated and current_user.role == 'student':
            current_user.is_paid = True
            current_user.save()
            flash("🎉 Payment Successful! Account upgraded.", "success")

    return redirect(url_for('sop.sop_generator_page'))


@sop_bp.route('/payment/fail', methods=['GET', 'POST'])
def payment_fail():
    flash("❌ Payment failed or declined. Please try again.", "error")
    return redirect(url_for('sop.sop_generator_page'))


@sop_bp.route('/payment/cancel', methods=['GET', 'POST'])
def payment_cancel():
    flash("⚠️ Payment was cancelled.", "info")
    return redirect(url_for('sop.sop_generator_page'))