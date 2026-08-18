import os
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.scholarship import Scholarship
from app.models.cost_reference import CostReference
from . import student_bp, groq_client

@student_bp.route('/cost_calculator', methods=['GET'])
@login_required
def cost_calculator():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    # Retrieve all scholarships that the student is tracking/saving
    user = User.objects(id=current_user.id).first()
    tracked_scholarships = user.tracked_scholarships if user else []
    
    # Retrieve all scholarships in the database to ensure the calculator is always usable
    all_scholarships = Scholarship.objects.order_by('title')

    # Check for pre-selected scholarship ID in query params
    selected_id = request.args.get('scholarship_id', '')

    return render_template(
        'dashboard/cost_calculator.html',
        tracked_scholarships=tracked_scholarships,
        all_scholarships=all_scholarships,
        selected_id=selected_id
    )

@student_bp.route('/api/calculate_cost/<scholarship_id>', methods=['GET'])
@login_required
def calculate_cost_api(scholarship_id):
    if current_user.role != 'student':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    scholarship = Scholarship.objects(id=scholarship_id).first()
    if not scholarship:
        return jsonify({"status": "error", "message": "Scholarship not found"}), 404

    # RAG Retrieval Phase: Find the matching country cost reference
    cost_ref = CostReference.objects(country__icontains=scholarship.country).first()
    if not cost_ref:
        # Fallback to general default guidelines
        cost_ref = CostReference.objects(country__icontains="Default").first()

    if not cost_ref:
        # Emergency backup hardcoded dictionary
        cost_ref = CostReference(
            country=scholarship.country or "Global",
            visa_fee=150.0,
            language_test_fee=220.0,
            average_travel_cost=850.0,
            annual_insurance_cost=800.0,
            monthly_living_cost=1100.0,
            average_application_fee=75.0,
            currency="USD",
            additional_notes="Standard fallback cost estimates."
        )

    # Simple logic to determine if scholarship is "Fully Funded"
    funding_lower = (scholarship.funding_amount or "").lower()
    is_fully_funded = any(x in funding_lower for x in ["full cost", "fully funded", "participation costs covered", "100%", "covers all"])

    # Calculate post-arrival annual costs
    annual_living_cost = cost_ref.monthly_living_cost * 12
    total_post_arrival_annual = annual_living_cost + cost_ref.annual_insurance_cost

    # Pre-departure one-time costs
    total_pre_departure = (
        cost_ref.visa_fee +
        cost_ref.language_test_fee +
        cost_ref.average_travel_cost +
        cost_ref.average_application_fee
    )

    # Construct the RAG Prompt for the AI
    prompt = f"""
    You are the 'ScholarMatch AI Cost Calculator', an expert academic financial advisor.
    Analyze the selected scholarship and country cost profile to generate a detailed cost-of-study estimate and budgeting guide for the student.

    STUDENT DETAILS:
    - Name: {current_user.full_name}
    - Target Degree: {current_user.degree_level or 'Not specified'}
    - Starting Nationality: {current_user.nationality or 'Not specified'}

    SCHOLARSHIP DETAILS:
    - Title: {scholarship.title}
    - University: {scholarship.university}
    - Country: {scholarship.country}
    - Funding Amount Specified: {scholarship.funding_amount}
    - Major/Field: {scholarship.major}

    LOCAL COST REFERENCE DATA (RAG RETRIEVED):
    - Currency: {cost_ref.currency}
    - Average Application Fee: ${cost_ref.average_application_fee}
    - Visa Application Fee: ${cost_ref.visa_fee}
    - Language Test Fee: ${cost_ref.language_test_fee}
    - Travel (flight estimate): ${cost_ref.average_travel_cost}
    - Annual Insurance: ${cost_ref.annual_insurance_cost}
    - Monthly Living Costs: ${cost_ref.monthly_living_cost}
    - Local Notes: {cost_ref.additional_notes}

    INSTRUCTIONS:
    1. Greet {current_user.full_name} by name.
    2. Analyze the funding amount of the scholarship against the local living costs and fees. State clearly if the scholarship is sufficient to cover these costs or if there is a deficit.
    3. Outline the key financial requirements (in USD).
    4. Give 3 actionable tips for the student to save money or offset these costs (e.g., student discounts, part-time work limits in that country, rent subsidy, or booking flights early).
    5. Keep the advice practical and encouraging, using clear bullet points.
    """

    ai_advice = "The AI financial advice server is currently offline. Please review the structured cost table below."

    if groq_client:
        try:
            completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=1000
            )
            ai_advice = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq API call error: {e}")
            ai_advice = "Could not generate personalized AI advice due to high service traffic. Please use the cost breakdown below."

    return jsonify({
        "status": "success",
        "scholarship": {
            "title": scholarship.title,
            "university": scholarship.university,
            "country": scholarship.country,
            "funding_amount": scholarship.funding_amount,
            "is_fully_funded": is_fully_funded
        },
        "costs": {
            "application_fee": cost_ref.average_application_fee,
            "visa_fee": cost_ref.visa_fee,
            "language_test_fee": cost_ref.language_test_fee,
            "travel_cost": cost_ref.average_travel_cost,
            "insurance_cost": cost_ref.annual_insurance_cost,
            "monthly_living_cost": cost_ref.monthly_living_cost,
            "annual_living_cost": annual_living_cost,
            "total_pre_departure": total_pre_departure,
            "total_post_arrival_annual": total_post_arrival_annual,
            "currency": cost_ref.currency,
            "notes": cost_ref.additional_notes
        },
        "ai_advice": ai_advice
    })
