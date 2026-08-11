import os
from app import create_app
from app.models.scholarship import Scholarship
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

app = create_app()

with app.app_context():
    total = Scholarship.objects.count()
    print(f"1. Total scholarships in DB: {total}")
    
    with_vectors = Scholarship.objects(embedding__exists=True).count()
    print(f"2. Scholarships WITH AI vectors: {with_vectors}")
    
    if with_vectors > 0:
        print("3. Testing MongoDB Vector Search Engine...")
        try:
            # Generate a test vector
            query = genai.embed_content(
                model="models/gemini-embedding-2",
                content="Computer Science Masters",
                task_type="retrieval_query"
            )['embedding']
            # ADD THESE TWO LINES:
            first_scholarship = Scholarship.objects(embedding__exists=True).first()
            print(f"Stored vector dimensions in DB: {len(first_scholarship.embedding)}")
            print(f"Query vector dimensions from AI: {len(query)}")
            # Run the search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query,
                        "numCandidates": 100,
                        "limit": 5
                    }
                }
            ]
            
            results = list(Scholarship._get_collection().aggregate(pipeline))
            print(f"4. Vector Search returned: {len(results)} results.")
            
            if len(results) > 0:
                print(f"   Success! Top match: {results[0]['title']}")
        except Exception as e:
            print(f"4. Vector Search CRASHED: {e}")
    else:
        print("4. Skipping search because there are no vectors!")