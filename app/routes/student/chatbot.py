from flask import request, Response, stream_with_context
from flask_login import login_required, current_user
from app.models.scholarship import Scholarship
from . import student_bp, groq_client
from .scholarship_discovery import get_text_embedding

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
                model="openai/gpt-oss-20b",
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