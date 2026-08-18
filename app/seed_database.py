import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing app routes
load_dotenv()

from google import genai
from app import create_app
from app.models.scholarship import Scholarship

gemini_api_key = os.environ.get('GEMINI_API_KEY')
if not gemini_api_key:
    print("⚠️ Warning: GEMINI_API_KEY environment variable is missing.")

client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

app = create_app()

def generate_embedding(text):
    if not client:
        return []
    for model_id in ["embedding-001", "text-embedding-004"]:
        try:
            response = client.models.embed_content(
                model=model_id,
                contents=text
            )
            if response and response.embeddings:
                return response.embeddings[0].values
        except Exception:
            continue
    return []

def seed_real_scholarships():
    possible_files = ["real_scholarships_3.json", "real_scholarships_unique.json", "real_scholarships.json"]
    json_filepath = next((f for f in possible_files if os.path.exists(f)), None)

    if not json_filepath:
        print("❌ Error: Could not find any scholarship JSON file in the root directory.")
        return

    with app.app_context():
        print("🗑️ Clearing database collection...")
        Scholarship.objects.delete()

        with open(json_filepath, "r", encoding="utf-8") as f:
            scholarships_data = json.load(f)

        print(f"🔄 Processing {len(scholarships_data)} real scholarship entries from '{json_filepath}'...")
        saved_count = 0

        for item in scholarships_data:
            title = item.get("title", "").strip()
            university = item.get("university", "").strip()
            country = item.get("country", "").strip()
            degree_level = item.get("degree_level", "Masters").strip()
            minimum_gpa = float(item.get("minimum_gpa", 3.0))
            funding_amount = item.get("funding_amount", "Fully Funded").strip()
            official_url = item.get("official_url", "#").strip()
            major = item.get("major", "All Majors").strip()
            institution_type = item.get("institution_type", "Public").strip()

            search_text = f"{title} at {university} in {country}. Degree: {degree_level}. Major: {major}. Funding: {funding_amount}."
            embedding_vector = generate_embedding(search_text)

            scholarship_doc = Scholarship(
                title=title,
                university=university,
                country=country,
                degree_level=degree_level,
                minimum_gpa=minimum_gpa,
                funding_amount=funding_amount,
                official_url=official_url,
                major=major,
                institution_type=institution_type,
                embedding=embedding_vector,
                tags=[country, degree_level, major]
            )

            scholarship_doc.save()
            saved_count += 1

            if saved_count % 10 == 0 or saved_count == len(scholarships_data):
                print(f"✅ Saved [{saved_count}/{len(scholarships_data)}] entries to MongoDB...")

        print(f"\n🎉 STEP 2 COMPLETE! Successfully seeded {saved_count} real scholarships into MongoDB.")

from app.models.cost_reference import CostReference

def seed_cost_references():
    with app.app_context():
        print("🗑️ Clearing cost references database collection...")
        CostReference.objects.delete()

        cost_data = [
            {
                "country": "United States",
                "visa_fee": 185.0,
                "language_test_fee": 205.0,
                "average_travel_cost": 1000.0,
                "annual_insurance_cost": 2200.0,
                "monthly_living_cost": 1500.0,
                "average_application_fee": 80.0,
                "currency": "USD",
                "additional_notes": "SEVIS fee of $350 is also required for F-1 students. Health insurance is typically mandatory through the university."
            },
            {
                "country": "United Kingdom",
                "visa_fee": 620.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 850.0,
                "annual_insurance_cost": 1000.0,
                "monthly_living_cost": 1350.0,
                "average_application_fee": 60.0,
                "currency": "GBP",
                "additional_notes": "Visa fee includes NHS Health Surcharge of £776/year. Living costs in London are higher, averaging £1,300-£1,400/month."
            },
            {
                "country": "Germany",
                "visa_fee": 80.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 750.0,
                "annual_insurance_cost": 1300.0,
                "monthly_living_cost": 950.0,
                "average_application_fee": 75.0,
                "currency": "EUR",
                "additional_notes": "A blocked account (Sperrkonto) showing €11,208/year is required for visa purposes. Public health insurance is around €120/month."
            },
            {
                "country": "Canada",
                "visa_fee": 150.0,
                "language_test_fee": 225.0,
                "average_travel_cost": 950.0,
                "annual_insurance_cost": 750.0,
                "monthly_living_cost": 1250.0,
                "average_application_fee": 95.0,
                "currency": "CAD",
                "additional_notes": "A Guaranteed Investment Certificate (GIC) of $20,635 CAD is required to prove financial sufficiency."
            },
            {
                "country": "Australia",
                "visa_fee": 490.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 1100.0,
                "annual_insurance_cost": 650.0,
                "monthly_living_cost": 1450.0,
                "average_application_fee": 110.0,
                "currency": "AUD",
                "additional_notes": "Overseas Student Health Cover (OSHC) is mandatory for the duration of the student visa."
            },
            {
                "country": "Japan",
                "visa_fee": 30.0,
                "language_test_fee": 200.0,
                "average_travel_cost": 900.0,
                "annual_insurance_cost": 250.0,
                "monthly_living_cost": 900.0,
                "average_application_fee": 50.0,
                "currency": "JPY",
                "additional_notes": "National Health Insurance (NHI) is mandatory and very cheap (around $20/month). Part-time work is allowed up to 28 hours/week."
            },
            {
                "country": "France",
                "visa_fee": 100.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 750.0,
                "annual_insurance_cost": 300.0,
                "monthly_living_cost": 900.0,
                "average_application_fee": 50.0,
                "currency": "EUR",
                "additional_notes": "Social Security health cover is free for international students. Rent subsidy (CAF) can offset living costs up to 30%."
            },
            {
                "country": "Netherlands",
                "visa_fee": 210.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 600.0,
                "monthly_living_cost": 1150.0,
                "average_application_fee": 100.0,
                "currency": "EUR",
                "additional_notes": "Proof of financial means (around €12,000/year) is required for the residence permit."
            },
            {
                "country": "Sweden",
                "visa_fee": 150.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 0.0,
                "monthly_living_cost": 1000.0,
                "average_application_fee": 100.0,
                "currency": "SEK",
                "additional_notes": "Students staying more than 12 months receive a personal identity number (personnummer) giving access to Swedish healthcare."
            },
            {
                "country": "Switzerland",
                "visa_fee": 90.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 850.0,
                "annual_insurance_cost": 1800.0,
                "monthly_living_cost": 1900.0,
                "average_application_fee": 120.0,
                "currency": "CHF",
                "additional_notes": "One of the most expensive countries. Health insurance is compulsory for all international students."
            },
            {
                "country": "Ireland",
                "visa_fee": 65.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 700.0,
                "monthly_living_cost": 1250.0,
                "average_application_fee": 60.0,
                "currency": "EUR",
                "additional_notes": "Students must register with the Immigration Service Delivery (ISD) after arrival (€300 fee)."
            },
            {
                "country": "Singapore",
                "visa_fee": 90.0,
                "language_test_fee": 210.0,
                "average_travel_cost": 500.0,
                "annual_insurance_cost": 300.0,
                "monthly_living_cost": 1300.0,
                "average_application_fee": 50.0,
                "currency": "SGD",
                "additional_notes": "Student's Pass (STP) application requires processing and issuance fees. Living costs vary between on-campus and off-campus housing."
            },
            {
                "country": "China",
                "visa_fee": 140.0,
                "language_test_fee": 190.0,
                "average_travel_cost": 650.0,
                "annual_insurance_cost": 120.0,
                "monthly_living_cost": 600.0,
                "average_application_fee": 75.0,
                "currency": "CNY",
                "additional_notes": "Highly affordable study destination. Visa type depends on duration (X1 for long-term, X2 for short-term)."
            },
            {
                "country": "Italy",
                "visa_fee": 60.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 750.0,
                "annual_insurance_cost": 180.0,
                "monthly_living_cost": 850.0,
                "average_application_fee": 40.0,
                "currency": "EUR",
                "additional_notes": "Residence permit (Permesso di Soggiorno) must be applied for within 8 days of arrival (costs around €120)."
            },
            {
                "country": "Norway",
                "visa_fee": 600.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 850.0,
                "annual_insurance_cost": 0.0,
                "monthly_living_cost": 1300.0,
                "average_application_fee": 0.0,
                "currency": "NOK",
                "additional_notes": "Norway has high living standards. Students must deposit a financial guarantee of around NOK 137,907/year in a Norwegian account."
            },
            {
                "country": "South Korea",
                "visa_fee": 60.0,
                "language_test_fee": 190.0,
                "average_travel_cost": 700.0,
                "annual_insurance_cost": 450.0,
                "monthly_living_cost": 900.0,
                "average_application_fee": 65.0,
                "currency": "KRW",
                "additional_notes": "National Health Insurance (NHIS) enrollment is automatic and mandatory for international students after arrival."
            },
            {
                "country": "New Zealand",
                "visa_fee": 230.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 1100.0,
                "annual_insurance_cost": 500.0,
                "monthly_living_cost": 1350.0,
                "average_application_fee": 85.0,
                "currency": "NZD",
                "additional_notes": "International students must show proof of at least $20,000 NZD per year for living expenses."
            },
            {
                "country": "Finland",
                "visa_fee": 350.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 200.0,
                "monthly_living_cost": 900.0,
                "average_application_fee": 0.0,
                "currency": "EUR",
                "additional_notes": "Residence permit requires private health insurance with cover matching the duration of your stay."
            },
            {
                "country": "Denmark",
                "visa_fee": 270.0,
                "language_test_fee": 230.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 0.0,
                "monthly_living_cost": 1100.0,
                "average_application_fee": 100.0,
                "currency": "DKK",
                "additional_notes": "International students get access to free public healthcare (Yellow Health Card) once registered in the Civil Registration System."
            },
            {
                "country": "Belgium",
                "visa_fee": 200.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 150.0,
                "monthly_living_cost": 1050.0,
                "average_application_fee": 75.0,
                "currency": "EUR",
                "additional_notes": "Registration at the local town hall (Maison Communale) is required within 8 days of arrival."
            },
            {
                "country": "Austria",
                "visa_fee": 160.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 800.0,
                "annual_insurance_cost": 800.0,
                "monthly_living_cost": 1000.0,
                "average_application_fee": 50.0,
                "currency": "EUR",
                "additional_notes": "Mandatory student self-insurance (Studentenselbstversicherung) is around €65/month."
            },
            {
                "country": "Saudi Arabia",
                "visa_fee": 80.0,
                "language_test_fee": 200.0,
                "average_travel_cost": 500.0,
                "annual_insurance_cost": 200.0,
                "monthly_living_cost": 750.0,
                "average_application_fee": 30.0,
                "currency": "SAR",
                "additional_notes": "Many Saudi government/university scholarships are fully comprehensive and cover all flights, books, and medical care."
            },
            {
                "country": "Turkey",
                "visa_fee": 100.0,
                "language_test_fee": 180.0,
                "average_travel_cost": 600.0,
                "annual_insurance_cost": 150.0,
                "monthly_living_cost": 550.0,
                "average_application_fee": 30.0,
                "currency": "TRY",
                "additional_notes": "Highly affordable study destination. Public health insurance (GSS) is available at a low cost."
            },
            {
                "country": "Hungary",
                "visa_fee": 60.0,
                "language_test_fee": 210.0,
                "average_travel_cost": 750.0,
                "annual_insurance_cost": 250.0,
                "monthly_living_cost": 650.0,
                "average_application_fee": 50.0,
                "currency": "HUF",
                "additional_notes": "Highly cost-effective European option. Stipendium Hungaricum covers tuition, medical insurance, and a housing allowance."
            },
            {
                "country": "Hong Kong",
                "visa_fee": 30.0,
                "language_test_fee": 210.0,
                "average_travel_cost": 650.0,
                "annual_insurance_cost": 400.0,
                "monthly_living_cost": 1300.0,
                "average_application_fee": 60.0,
                "currency": "HKD",
                "additional_notes": "High living costs, especially for accommodation. University hostels are significantly cheaper than off-campus housing."
            },
            {
                "country": "Taiwan",
                "visa_fee": 80.0,
                "language_test_fee": 180.0,
                "average_travel_cost": 600.0,
                "annual_insurance_cost": 250.0,
                "monthly_living_cost": 700.0,
                "average_application_fee": 45.0,
                "currency": "TWD",
                "additional_notes": "National Health Insurance is outstanding and cheap. Safe, friendly, and very cost-competitive study destination."
            },
            {
                "country": "Poland",
                "visa_fee": 80.0,
                "language_test_fee": 210.0,
                "average_travel_cost": 750.0,
                "annual_insurance_cost": 150.0,
                "monthly_living_cost": 700.0,
                "average_application_fee": 35.0,
                "currency": "PLN",
                "additional_notes": "Very affordable living costs in Central Europe. Voluntary NFZ health insurance is around €15/month."
            },
            {
                "country": "Russia",
                "visa_fee": 80.0,
                "language_test_fee": 180.0,
                "average_travel_cost": 700.0,
                "annual_insurance_cost": 150.0,
                "monthly_living_cost": 500.0,
                "average_application_fee": 30.0,
                "currency": "RUB",
                "additional_notes": "Low cost of living. Government scholarships often cover 100% of tuition and include a small monthly stipend."
            },
            {
                "country": "Romania",
                "visa_fee": 120.0,
                "language_test_fee": 200.0,
                "average_travel_cost": 700.0,
                "annual_insurance_cost": 100.0,
                "monthly_living_cost": 600.0,
                "average_application_fee": 40.0,
                "currency": "RON",
                "additional_notes": "One of the most affordable EU study destinations. Health insurance is compulsory."
            },
            {
                "country": "Default / Global",
                "visa_fee": 150.0,
                "language_test_fee": 220.0,
                "average_travel_cost": 850.0,
                "annual_insurance_cost": 800.0,
                "monthly_living_cost": 1100.0,
                "average_application_fee": 75.0,
                "currency": "USD",
                "additional_notes": "Estimates based on international averages. Check specific country and university guidelines."
            }
        ]

        print(f"🔄 Seeding {len(cost_data)} cost reference guides...")
        for c in cost_data:
            CostReference(**c).save()
        print("🎉 Successfully seeded cost reference guides!")

if __name__ == "__main__":
    # Allow running either one or both
    seed_real_scholarships()
    seed_cost_references()