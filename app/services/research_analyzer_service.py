import os
import math
from google import genai
from app.models.research_taxonomy import ResearchTaxonomy
from app.models.professor import Professor
from app.models.scholarship import Scholarship

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

def get_gemini_embedding(text):
    """Generates 768-D query vector using the new google-genai SDK."""
    if not GEMINI_API_KEY or not text:
        return []

    try:
        # Initialize the client using the new SDK structure
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Generate the embedding
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text[:3000]
        )
        
        # Extract the numerical values from the new response object
        return response.embeddings[0].values
        
    except Exception as e:
        print(f"[GEMINI EMBEDDING ERROR]: {e}")
        return []

# --- KEEP ALL YOUR OTHER FUNCTIONS BELOW THIS LINE EXACTLY THE SAME ---
# (cosine_similarity, vector_search_taxonomies, match_professors_by_vector, etc.)

def cosine_similarity(vec1, vec2):
    """Calculates cosine similarity between two 768-D vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def vector_search_taxonomies(student_vector, student_skills, top_k=3):
    """
    Performs pure mathematical Vector Search against pre-embedded 
    ResearchTaxonomy documents stored in MongoDB.
    """
    taxonomies = ResearchTaxonomy.objects()
    if not taxonomies:
        return [], [], []

    scored_niches = []
    student_skills_set = {s.strip().lower() for s in (student_skills or [])}

    for tax in taxonomies:
        if not tax.embedding:
            continue
        
        # 1. Cosine Distance Calculation
        raw_sim = cosine_similarity(student_vector, tax.embedding)
        
        # Scale to intuitive percentage (e.g. 0.3 -> 60%, 0.85 -> 96%)
        fit_percentage = round(min(98.5, max(45.0, (raw_sim * 60.0) + 40.0)), 1)

        # 2. Deterministic Skill Gap Analysis (Set Theory)
        core_skills_lower = {s.lower(): s for s in tax.core_skills}
        matched = [core_skills_lower[s] for s in core_skills_lower if s in student_skills_set]
        missing = [core_skills_lower[s] for s in core_skills_lower if s not in student_skills_set]

        scored_niches.append({
            "niche": tax.niche_title,
            "broad_domain": tax.broad_domain,
            "description": tax.description,
            "fit_percentage": fit_percentage,
            "matched_skills": matched,
            "missing_skills": missing,
            "raw_similarity": raw_sim
        })

    # Rank by mathematical vector similarity
    scored_niches.sort(key=lambda x: x["fit_percentage"], reverse=True)
    top_matches = scored_niches[:top_k]

    # Aggregate global strengths and skill gaps from retrieved database nodes
    all_matched = list({s for match in top_matches for s in match["matched_skills"]})
    all_missing = list({s for match in top_matches for s in match["missing_skills"]})

    return top_matches, all_matched, all_missing

def match_professors_by_vector(student_vector, top_niches, limit=5):
    """Matches faculty by computing vector cosine similarity against lab domains."""
    professors = Professor.objects()
    scored_professors = []

    target_niche_titles = [n["niche"].lower() for n in top_niches]

    for prof in professors:
        prof_text = f"{prof.primary_domain} {' '.join(prof.research_interests)} {prof.bio_summary or ''} {prof.lab_name or ''}"
        
        # Calculate cosine similarity with professor corpus
        prof_vec = get_gemini_embedding(prof_text)
        vec_sim = cosine_similarity(student_vector, prof_vec) if prof_vec else 0.5
        
        # Domain keyword alignment
        term_bonus = 10.0 if any(n in prof_text.lower() for n in target_niche_titles) else 0.0
        funding_bonus = 10.0 if (prof.has_funding and prof.accepting_students) else 0.0
        
        total_fit = round(min(99.0, max(50.0, (vec_sim * 70.0) + term_bonus + funding_bonus)), 1)

        scored_professors.append({
            'id': str(prof.id),
            'full_name': prof.full_name,
            'title': prof.title,
            'institution': prof.institution,
            'country': prof.country,
            'primary_domain': prof.primary_domain,
            'lab_name': prof.lab_name or 'Research Lab',
            'has_funding': prof.has_funding,
            'fit_score': total_fit
        })

    scored_professors.sort(key=lambda x: x['fit_score'], reverse=True)
    return scored_professors[:limit]

def match_scholarships_by_domain(top_niches, limit=4):
    """Filters relevant scholarship awards for the matched research niches."""
    try:
        niche_words = [w.lower() for n in top_niches for w in n["niche"].split()]
        matches = []
        for s in Scholarship.objects():
            text = f"{s.title} {getattr(s, 'description', '')}".lower()
            if any(w in text for w in niche_words):
                matches.append({
                    'id': str(s.id),
                    'title': s.title,
                    'deadline': s.deadline.strftime('%b %d, %Y') if getattr(s, 'deadline', None) else 'Upcoming',
                    'amount': getattr(s, 'amount', 'Full Tuition / Grant')
                })
        return matches[:limit]
    except Exception:
        return []