from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.models.scholarship import Scholarship
from . import student_bp, gemini_client, groq_client

def get_text_embedding(text):
    """Utility function to retrieve text embeddings using Google GenAI SDK."""
    if not gemini_client or not text:
        return []
    
    candidate_models = ["models/embedding-001"]
    
    for model_name in candidate_models:
        try:
            response = gemini_client.models.embed_content(
                model=model_name,
                contents=text
            )
            if response and hasattr(response, 'embeddings') and response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            print(f"Embedding error with {model_name}: {e}")
            continue
            
    return []

@student_bp.route('/discovery', methods=['GET', 'POST'])
@login_required
def scholarship_discovery():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    # FIXED: Initialize these at the top so they always exist!
    recommended_scholarships = []
    ai_message = None
    tracked_ids = []

    # Get user and their tracked scholarships immediately
    user = User.objects(id=current_user.id).first()
    if user and getattr(user, 'tracked_scholarships', None):
        tracked_ids = [str(s.id) for s in user.tracked_scholarships]

    if request.method == 'POST':
        try:
            user.gpa = float(request.form.get('gpa', 3.0))
            user.degree_level = request.form.get('degree_level', 'Masters')
            user.nationality = request.form.get('nationality', '')
            user.major = request.form.get('major', 'Computer Science')
            user.save()
            flash('Academic profile updated! AI is searching...', 'success')
            return redirect(url_for('student.scholarship_discovery'))
        except ValueError:
            flash('Invalid GPA format.', 'error')

    all_nationalities = [
        "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan", "Argentine", "Armenian", 
        "Australian", "Austrian", "Azerbaijani", "Bangladeshi", "Barbadian", "Belarusian", "Belgian", 
        "Belizean", "Beninese", "Bhutanese", "Bolivian", "Bosnian", "Brazilian", "British", "Bruneian", 
        "Bulgarian", "Burkinabe", "Burmese", "Burundian", "Cambodian", "Cameroonian", "Canadian", 
        "Chadian", "Chilean", "Chinese", "Colombian", "Comoran", "Congolese", "Costa Rican", "Croatian", 
        "Cuban", "Cypriot", "Czech", "Danish", "Djiboutian", "Dominican", "Dutch", "Ecuadorian", 
        "Egyptian", "Emirati", "Eritrean", "Estonian", "Ethiopian", "Fijian", "Finnish", "French", 
        "Gabonese", "Gambian", "Georgian", "German", "Ghanaian", "Greek", "Grenadian", "Guatemalan", 
        "Guinean", "Haitian", "Honduran", "Hungarian", "Icelander", "Indian", "Indonesian", "Iranian", 
        "Iraqi", "Irish", "Israeli", "Italian", "Jamaican", "Japanese", "Jordanian", "Kazakh", 
        "Kenyan", "Kuwaiti", "Kyrgyz", "Laotian", "Latvian", "Lebanese", "Liberian", "Libyan", 
        "Lithuanian", "Luxembourger", "Malagasy", "Malawian", "Malaysian", "Maldivian", "Malian", 
        "Maltese", "Mauritian", "Mexican", "Moldovan", "Mongolian", "Montenegrin", "Moroccan", 
        "Mozambican", "Namibian", "Nepalese", "New Zealander", "Nicaraguan", "Nigerian", "North Korean", 
        "Norwegian", "Omani", "Pakistani", "Palauan", "Palestinian", "Panamanian", "Paraguayan", 
        "Peruvian", "Philippine", "Polish", "Portuguese", "Qatari", "Romanian", "Russian", "Rwandan", 
        "Saudi", "Senegalese", "Serbian", "Singaporean", "Slovak", "Slovenian", "Somali", "South African", 
        "South Korean", "Spanish", "Sri Lankan", "Sudanese", "Swazi", "Swedish", "Swiss", "Syrian", 
        "Taiwanese", "Tajik", "Tanzanian", "Thai", "Togolese", "Tongan", "Tunisian", "Turkish", 
        "Turkmen", "Ugandan", "Ukrainian", "Uruguayan", "Uzbek", "Vanuatuan", "Venezuelan", "Vietnamese", 
        "Yemeni", "Zambian", "Zimbabwean"
    ]

    all_majors = [
        "Bachelor of Architecture (ARC)",
        "Bachelor of Arts in Applied English Language Studies (BA in AELS)",
        "Bachelor of Arts in English (BA in English)",
        "Bachelor of Business Administration (BBA)",
        "Bachelor of Disaster Management (BDM)",
        "Bachelor of Laws (LL.B. Hons.) (LLB)",
        "Bachelor of Pharmacy (Hons.) (PHR)",
        "Bachelor of Science in Applied Physics and Electronics (APE)",
        "Bachelor of Science in Biotechnology (BIO)",
        "Bachelor of Science in Computer Science (CS)",
        "Bachelor of Science in Computer Science & Engineering (CSE)",
        "Bachelor of Science in Electrical and Electronic Engineering (EEE)",
        "Bachelor of Science in Electronic And Communication Engineering (ECE)",
        "Bachelor of Science in Mathematics (MAT)",
        "Bachelor of Science in Microbiology (MIC)",
        "Bachelor of Science in Physics (PHY)",
        "Bachelor of Social Science in Economics (ECO)",
        "Bachelor of Social Sciences in Anthropology (ANT)"
    ]

    if current_user.gpa:
        search_query = f"Scholarship for {current_user.degree_level} in {current_user.major} from {current_user.nationality}."
        query_embedding = get_text_embedding(search_query)

        if query_embedding:
            try:
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "vector_index",
                            "path": "embedding",
                            "queryVector": query_embedding,
                            "numCandidates": 100,
                            "limit": 50
                        }
                    },
                    {
                        "$match": {
                            "minimum_gpa": {"$lte": current_user.gpa}
                        }
                    }
                ]
                recommended_scholarships = list(Scholarship._get_collection().aggregate(pipeline))
                for s in recommended_scholarships:
                    s['id'] = str(s['_id'])
            except Exception as vector_err:
                print(f"Vector search index exception (falling back to GPA match): {vector_err}")
                recommended_scholarships = []

        if not recommended_scholarships:
            query_objects = Scholarship.objects(
                minimum_gpa__lte=current_user.gpa,
                degree_level__icontains=current_user.degree_level,
                major__icontains="English" if "English" in (current_user.major or "") else current_user.major
            )[:20]

            if not query_objects:
                query_objects = Scholarship.objects(
                    minimum_gpa__lte=current_user.gpa,
                    degree_level__icontains=current_user.degree_level
                )[:20]

            if not query_objects:
                query_objects = Scholarship.objects(minimum_gpa__lte=current_user.gpa)[:20]

            recommended_scholarships = []
            for item in query_objects:
                s_dict = item.to_mongo().to_dict()
                s_dict['id'] = str(item.id)
                recommended_scholarships.append(s_dict)

        if groq_client and recommended_scholarships:
            context = "\n".join([f"- {s.get('title')} at {s.get('university')} ({s.get('country')})" for s in recommended_scholarships[:5]])
            prompt = f"Act as an academic advisor. A student with a {current_user.gpa} GPA wants to study {current_user.major}. I matched these top scholarships:\n{context}\nWrite 2 encouraging sentences explaining why these opportunities fit their academic profile."
            try:
                chat_res = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    max_tokens=150
                )
                ai_message = chat_res.choices[0].message.content
            except Exception as groq_err:
                print(f"Groq summary error: {groq_err}")
                ai_message = "Our AI matched these top international scholarships based on your academic GPA profile!"
        else:
            ai_message = "Here are top scholarship matches for your academic GPA profile:"

    return render_template('dashboard/scholarship_discovery.html', 
                           scholarships=recommended_scholarships, 
                           ai_message=ai_message,
                           all_nationalities=all_nationalities,
                           all_majors=all_majors,
                           tracked_ids=tracked_ids)