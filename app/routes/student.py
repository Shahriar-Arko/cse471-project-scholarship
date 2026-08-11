import os
import json
import uuid
import datetime
import threading
import smtplib
from email.message import EmailMessage
from google import genai
from groq import Groq
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
from app.models.user import User
from app.models.scholarship import Scholarship
from app.models.saved_checklist import SavedChecklist, ChecklistItem
from app.models.timeline import ApplicationTimeline, TimelineTask
from dotenv import load_dotenv
load_dotenv()
student_bp = Blueprint('student', __name__, url_prefix='/student')

# Modern Google GenAI Client
gemini_api_key = os.environ.get('GEMINI_API_KEY')
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# Groq Client for fast chat and synthesis
groq_api_key = os.environ.get('GROQ_API_KEY')
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# --- NEW: BACKGROUND EMAIL FUNCTION ---
def send_timeline_email_async(user_email, user_name, scholarship_title, university, timeline_tasks):
    try:
        if not groq_client:
            return

        # 1. Prepare tasks for the prompt
        tasks_str = "\n".join([f"- {t['title']} (Deadline: {t['deadline']})" for t in timeline_tasks])
        
        # 2. Ask Groq to write a beautiful HTML email
        prompt = f"""
        Write a highly professional and encouraging email to a student named {user_name}.
        They just generated a customized application timeline for the "{scholarship_title}" at {university}.
        
        Here are their specific deadlines:
        {tasks_str}
        
        Format the email entirely in clean, modern HTML with inline CSS.
        Include:
        - A professional, warm greeting.
        - A well-structured list or table of their deadlines.
        - 2-3 brief, highly actionable study/preparation tips for this specific type of application.
        - A professional sign-off from "The ScholarMatch AI Team".
        
        DO NOT wrap the output in ```html blocks. Output ONLY raw HTML code.
        """
        
        completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        html_content = completion.choices[0].message.content.strip()
        
        # Clean up markdown formatting if Groq accidentally includes it
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]

        # 3. Send the email via Google SMTP
        sender_email = os.environ.get('MAIL_USERNAME')
        sender_password = os.environ.get('MAIL_PASSWORD')
        
        if not sender_email or not sender_password:
            print("Email failed: MAIL_USERNAME or MAIL_PASSWORD missing in .env")
            return

        msg = EmailMessage()
        msg['Subject'] = f"Your Application Timeline: {scholarship_title}"
        msg['From'] = f"Scholarship Matcher <{sender_email}>"
        msg['To'] = user_email
        msg.set_content("Please enable HTML to view this email.")
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            print(f"Timeline email successfully sent to {user_email}")
            
    except Exception as e:
        print(f"Background email failed: {e}")

# --- EXISTING EMBEDDING FUNCTION ---
def get_text_embedding(text):
    """Utility function to retrieve text embeddings using Google GenAI SDK."""
    if not gemini_client or not text:
        return []
    
    # Prefixing with 'models/' is required for the new google-genai SDK
    candidate_models = ["models/text-embedding-004", "models/embedding-001"]
    
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

    recommended_scholarships = []
    ai_message = None

    if request.method == 'POST':
        try:
            user = User.objects(id=current_user.id).first()
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

        user = User.objects(id=current_user.id).first()
        tracked_ids = [str(s.id) for s in user.tracked_scholarships] if getattr(user, 'tracked_scholarships', None) else []

    return render_template('dashboard/scholarship_discovery.html', 
                           scholarships=recommended_scholarships, 
                           ai_message=ai_message,
                           all_nationalities=all_nationalities,
                           all_majors=all_majors,
                           tracked_ids=tracked_ids)

@student_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return "Message is required", 400

    context_text = ""
    query_embedding = get_text_embedding(user_message)
    
    if query_embedding:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 20,
                    "limit": 3
                }
            }]
            matches = list(Scholarship._get_collection().aggregate(pipeline))
            if matches:
                context_text = "Verified database information matching the query:\n"
                for s in matches:
                    context_text += f"- {s.get('title')} at {s.get('university')} in {s.get('country')}. Funding: {s.get('funding_amount')}. Official Link: {s.get('official_url')}\n"
        except Exception as e:
            print(f"Vector search fallback note: {e}")

    if not context_text:
        fallback_matches = Scholarship.objects()[:3]
        context_text = "Featured active scholarships from our database:\n"
        for s in fallback_matches:
            context_text += f"- {s.title} at {s.university} in {s.country}. Funding: {s.funding_amount}. Official Link: {s.official_url}\n"

    system_prompt = f"""
    You are the 'ScholarMatch RAG Chatbot', a helpful, highly knowledgeable academic advisor.
    Student Name: {current_user.full_name}
    Student Profile: Degree={current_user.degree_level or 'Not specified'}, Major={current_user.major or 'Not specified'}

    INSTRUCTIONS:
    1. Greet the student by name warmly.
    2. Answer general questions or greetings conversationally.
    3. Use the database context below to provide accurate scholarship names, universities, funding amounts, and official URLs.
    
    DATABASE CONTEXT:
    {context_text}
    """

    def generate_stream():
        if not groq_client:
            yield f"Hello {current_user.full_name}! The AI chat backend is currently initializing."
            return

        try:
            stream = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            print(f"Groq streaming error: {e}")
            yield f"Hello {current_user.full_name}! I am currently processing high traffic. Please try again shortly."

    return Response(stream_with_context(generate_stream()), content_type='text/plain')

# --- APP TRACKER & TIMELINE PLANNER ---

@student_bp.route('/track_scholarship/<scholarship_id>', methods=['GET', 'POST'])
@login_required
def track_scholarship(scholarship_id):
    try:
        user = User.objects(id=current_user.id).first()
        scholarship = Scholarship.objects(id=scholarship_id).first()
        
        if not scholarship:
            return jsonify({"status": "error", "message": "Scholarship not found."}), 404
            
        if scholarship and scholarship not in user.tracked_scholarships:
            user.tracked_scholarships.append(scholarship)
            user.save()
            return jsonify({"status": "success", "message": "Added to Application Tracker!"}), 200
        return jsonify({"status": "info", "message": "Already in your tracker."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@student_bp.route('/untrack_scholarship/<scholarship_id>', methods=['POST'])
@login_required
def untrack_scholarship(scholarship_id):
    """Removes a scholarship from the user's tracker and deletes its timeline."""
    try:
        user = User.objects(id=current_user.id).first()
        scholarship = Scholarship.objects(id=scholarship_id).first()
        
        if scholarship in user.tracked_scholarships:
            # Remove from saved list
            user.tracked_scholarships.remove(scholarship)
            user.save()
            
            # Delete the associated timeline to keep the database clean
            ApplicationTimeline.objects(user_id=str(current_user.id), scholarship_id=scholarship_id).delete()
            
            return jsonify({"status": "success", "message": "Removed from Tracker"}), 200
        return jsonify({"status": "error", "message": "Not found in your tracker."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500






@student_bp.route('/app_tracker', methods=['GET'])
@login_required
def app_tracker():
    user = User.objects(id=current_user.id).first()
    return render_template('dashboard/app_tracker.html', saved_scholarships=user.tracked_scholarships)

@student_bp.route('/api/timeline/<scholarship_id>', methods=['GET'])
@login_required
def get_timeline(scholarship_id):
    """Fetches the saved timeline from the database if it exists."""
    timeline = ApplicationTimeline.objects(user_id=str(current_user.id), scholarship_id=scholarship_id).first()
    if timeline:
        return jsonify({"tasks": [{"task_id": t.task_id, "column": t.column, "title": t.title, "deadline": t.deadline} for t in timeline.tasks]})
    return jsonify({"tasks": []})

@student_bp.route('/api/generate_timeline/<scholarship_id>', methods=['POST'])
@login_required
def generate_timeline(scholarship_id):
    """Generates a new AI timeline and SAVES it to the database."""
    scholarship = Scholarship.objects(id=scholarship_id).first()
    if not scholarship:
        return jsonify({"error": "Scholarship not found"}), 404

    today = datetime.datetime.utcnow().strftime('%B %d, %Y')
    real_deadline = scholarship.deadline.strftime('%B %d, %Y') if getattr(scholarship, 'deadline', None) else "December 31, 2026"

    fallback_timeline = {
        "tasks": [
            {"column": "todo", "title": f"Draft Statement of Purpose for {scholarship.university}", "deadline": "1 Month Before"},
            {"column": "todo", "title": "Obtain Official Academic Transcripts", "deadline": "3 Weeks Before"},
            {"column": "in_progress", "title": "Contact Professors for Reference Letters", "deadline": "2 Weeks Before"},
            {"column": "done", "title": "Create Portal Account & Register", "deadline": today}
        ]
    }

    generated_data = fallback_timeline
    if groq_client:
            prompt = f"""
            Act as an expert scholarship application planner.
            The user wants to apply to "{scholarship.title}" at "{scholarship.university}".
            The target deadline is: {real_deadline}. Today's date is: {today}.
            
            Generate a Kanban timeline working backwards from the deadline.
            Return ONLY a raw valid JSON object in this exact structure:
            {{
                "tasks": [
                    {{"column": "todo", "title": "Draft Statement of Purpose", "deadline": "Oct 1"}},
                    {{"column": "todo", "title": "Contact Recommenders", "deadline": "Sep 15"}},
                    {{"column": "done", "title": "Create Application Account", "deadline": "Aug 1"}}
                ]
            }}
            
            CRITICAL RULES:
            1. Columns must be exactly: 'todo', 'in_progress', or 'done'.
            2. Provide 5-7 tasks.
            3. NEVER put a task in the 'done' or 'in_progress' column if its deadline is in the future (after {today}).
            4. By default, assign all future tasks to the 'todo' column so the student can track their own progress manually.
            """
            try:
                completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                generated_data = json.loads(completion.choices[0].message.content.strip())
            except Exception as e:
                print(f"Timeline generation error: {e}")

    # Process and Save to Database
    tasks = []
    for item in generated_data.get('tasks', []):
        tasks.append(TimelineTask(
            task_id=str(uuid.uuid4()),
            column=item.get('column', 'todo'),
            title=item.get('title', 'Task'),
            deadline=item.get('deadline', '')
        ))

    # Overwrite if exists, otherwise create new
    existing = ApplicationTimeline.objects(user_id=str(current_user.id), scholarship_id=scholarship_id).first()
    if existing:
        existing.tasks = tasks
        existing.save()
    else:
        ApplicationTimeline(user_id=str(current_user.id), scholarship_id=scholarship_id, tasks=tasks).save()

    # --- NEW: TRIGGER BACKGROUND EMAIL ---
    threading.Thread(
        target=send_timeline_email_async, 
        args=(current_user.email, current_user.full_name, scholarship.title, scholarship.university, generated_data.get('tasks', []))
    ).start()

    return jsonify({"tasks": [{"task_id": t.task_id, "column": t.column, "title": t.title, "deadline": t.deadline} for t in tasks]})

@student_bp.route('/api/update_timeline_task/<scholarship_id>', methods=['POST'])
@login_required
def update_timeline_task(scholarship_id):
    """Updates the database when a user drags and drops a task."""
    data = request.json
    task_id = data.get('task_id')
    new_column = data.get('column')
    
    timeline = ApplicationTimeline.objects(user_id=str(current_user.id), scholarship_id=scholarship_id).first()
    if timeline:
        for t in timeline.tasks:
            if t.task_id == task_id:
                t.column = new_column
                break
        timeline.save()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

# --- 4. AI DOCUMENT CHECKLIST ROUTES ---

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