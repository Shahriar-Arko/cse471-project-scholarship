import os
import requests
from pymongo import MongoClient
from groq import Groq

# 1. Initialize Mongo & Groq Client
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
mongo_client = MongoClient(MONGO_URI)
sop_collection = mongo_client["scholarship_matcher"]["sop_templates"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_api_embedding(text):
    """Lightweight REST embedding call using Google's active gemini-embedding-001 model."""
    if not GEMINI_API_KEY or not text:
        return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {
            "parts": [{"text": text}]
        },
        "outputDimensionality": 768
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("embedding", {}).get("values", [])
        else:
            print(f"[RAG API ERROR] {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[RAG REQUEST ERROR] {e}")

    return []


def retrieve_reference_sops(user_major: str, user_prompt: str, top_k: int = 2) -> list:
    """Retrieves the closest SOP templates using Gemini Vector Search + Keyword Fallback."""
    search_prompt = f"Statement of Purpose for {user_major}. Student details and goals: {user_prompt}"
    query_vector = get_api_embedding(search_prompt)

    results = []

    # 1. Attempt Vector Search
    if query_vector:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 50,
                    "limit": top_k
                }
            }
        ]
        try:
            aggregated = list(sop_collection.aggregate(pipeline))
            results = [doc["content"] for doc in aggregated if "content" in doc]
        except Exception as e:
            print(f"[RAG ERROR] Vector search exception: {e}")

    # 2. Regex Fallback if Vector Search returns no direct hits
    if not results:
        print(f"[RAG FALLBACK] Vector search empty. Searching text for '{user_major}'...")
        fallback_docs = sop_collection.find({
            "$or": [
                {"major": {"$regex": user_major.strip(), "$options": "i"}},
                {"content": {"$regex": user_major.strip(), "$options": "i"}}
            ]
        }).limit(top_k)
        results = [doc.get("content") for doc in fallback_docs if doc.get("content")]

    # 3. Universal Fallback so RAG never returns 0 SOPs
    if not results:
        print("[RAG ULTIMATE FALLBACK] Pulling reference templates from database.")
        fallback_docs = sop_collection.find().limit(top_k)
        results = [doc.get("content") for doc in fallback_docs if doc.get("content")]

    return results

def generate_custom_sop(student_info: dict) -> str:
    major = student_info.get("major", "")
    user_prompt_text = student_info.get("user_prompt", "")
    target_university = student_info.get("target_university", "the university")
    degree_level = student_info.get("degree_level", "Master's")

    # 1. Retrieve the closest matching SOP templates from MongoDB using Gemini Vector Search
    ref_sops = retrieve_reference_sops(major, user_prompt_text)

    # 2. Terminal Debug Logging
    print("\n==================== [RAG RETRIEVAL DEBUG] ====================")
    print(f"Retrieved {len(ref_sops)} reference SOPs for Major: '{major}'")
    for idx, text in enumerate(ref_sops, 1):
        print(f"\n--- Snippet of Retrieved SOP #{idx} ---")
        print(text[:250].replace('\n', ' ') + "...")
    print("===============================================================\n")

    context_str = ""
    for idx, sop_text in enumerate(ref_sops, 1):
        context_str += f"\n--- DATABASE MATCH #{idx} ({major.upper()} REFERENCE) ---\n{sop_text[:2000]}\n"

    system_instruction = (
        "You are an expert academic writer and admissions consultant. "
        "Your primary job is to analyze the matched reference SOPs retrieved from the database "
        "and learn how successful applicants in this specific major construct their Statement of Purpose. "
        "You adopt their structural flow, section title styles, tone, and domain depth to write a custom SOP for the user."
    )

    user_prompt = f"""
Draft a realistic, highly tailored Statement of Purpose document for a student applying for a {degree_level} in {major} at {target_university}.

=== STUDENT'S PROFILE & INPUT ===
{user_prompt_text}

=== MATCHED DATABASE SOPS (STUDY THESE TO UNDERSTAND THE MAJOR'S SOP STYLE) ===
{context_str}

=== INSTRUCTIONS FOR RAG SYNTHESIS ===

1. DOCUMENT TITLE BLOCK:
   STATEMENT OF PURPOSE
   Applicant Target: {degree_level} in {major} | {target_university}

2. LEARN AND ADAPT THE MATCHED STRUCTURE & HEADERS:
   - Carefully analyze the "MATCHED DATABASE SOPS" above.
   - Look at how essays in {major} are written: Do they use bold section titles like "Research Background", "Previous Research", "Why [University]?" or thematic headers like "Inclusivity:", "Systems & Privacy:"?
   - Adopt similar structural headings and transitions appropriate for {major}.

3. UNDERSTAND THE MAJOR'S CONTEXT & DOMAIN DEPTH:
   - Use the matched database SOPs to understand the vocabulary, key theoretical challenges, and academic tone expected in {major}.
   - Do NOT blindly copy specific personal names or personal paper titles from the database matches, but DO use their style to explain the student's goals in {major} with high technical depth.

4. INTEGRATE STUDENT DETAILS TRUTHFULLY:
   - Blend the student's CGPA/GPA, background, and goals into the learned structure.
   - If the student provided minimal details, intelligently expand on core foundational topics of {major} using the tone and analytical style learned from the database matches.

5. AVOID GENERIC AI FLUFF:
   - Do not use cheesy, repetitive filler phrases ("stand at the precipice", "embark on a journey", "testament to my unwavering passion", "vibrant community").
   - Write with the directness and intellectual maturity of a real graduate applicant.

6. OUTPUT FORMAT:
   - Output ONLY the final Statement of Purpose text directly starting from the Title Block.
"""

    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        model="openai/gpt-oss-20b",
        temperature=0.65,
        max_tokens=2048
    )

    return response.choices[0].message.content