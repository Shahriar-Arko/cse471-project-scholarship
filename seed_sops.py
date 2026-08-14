import os
import json
import time
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
mongo_client = MongoClient(MONGO_URI)
collection = mongo_client["scholarship_matcher"]["sop_templates"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

def get_api_embedding(text):
    """Bulletproof REST embedding using Google's active model: gemini-embedding-001."""
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
            print(f"⚠️ API Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Request exception: {e}")

    return []

def seed_database():
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY or GOOGLE_API_KEY not found in .env file.")
        return

    file_path = "scraped_sops.json" if os.path.exists("scraped_sops.json") else "scraped_sops_2.json"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sops_data = json.load(f)
        print(f"📖 Loaded SOP data from '{file_path}'")
    except FileNotFoundError:
        print("❌ Error: Could not find 'scraped_sops.json' or 'scraped_sops_2.json'.")
        return

    documents_to_insert = []
    
    print("Generating Gemini API embeddings (gemini-embedding-001) for MongoDB...")
    for idx, entry in enumerate(sops_data, 1):
        content = entry.get("content", "").strip()
        major = entry.get("major", "General")

        if not content or content.startswith("[REQUIRES") or content.startswith("Error extracting"):
            continue
            
        print(f"[{idx}/{len(sops_data)}] Embedding major: {major}...")
        text_to_embed = f"Major: {major}. Content: {content[:2000]}"
        embedding = get_api_embedding(text_to_embed)

        if embedding:
            documents_to_insert.append({
                "major": major,
                "url": entry.get("url", ""),
                "content": content,
                "embedding": embedding
            })
        else:
            print(f"❌ Failed to get embedding for entry #{idx}")

        time.sleep(0.4)

    if documents_to_insert:
        collection.delete_many({}) 
        collection.insert_many(documents_to_insert)
        print(f"\n✅ Successfully inserted {len(documents_to_insert)} SOP templates into MongoDB!")
    else:
        print("❌ No documents were embedded. Please check your API key in .env.")

if __name__ == "__main__":
    seed_database()