import os
import re
from collections import Counter

from google import genai

from app.models.scholarship import Scholarship


def _normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_skill_name(skill):
    skill_text = _normalize_text(skill)
    if not skill_text:
        return ""
    return re.sub(r"[^a-zA-Z0-9+#./ -]", "", skill_text).strip()


def _flatten_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            items.extend(_flatten_list(item))
        return items
    return [_normalize_text(value)]


def build_resume_match_profile(extracted_data):
    raw_skills = extracted_data.get('skills', []) if isinstance(extracted_data, dict) else []
    skills = []
    seen = set()
    for skill in _flatten_list(raw_skills):
        cleaned = _normalize_skill_name(skill)
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            skills.append(cleaned)

    value_keys = ['academic_achievements', 'awards', 'research', 'projects', 'experience']
    achievements = []
    for key in value_keys:
        achievements.extend(_flatten_list((extracted_data or {}).get(key, [])))

    gpa = extracted_data.get('gpa') if isinstance(extracted_data, dict) else None
    try:
        gpa_value = float(str(gpa).replace('CGPA', '').replace('GPA', '').strip())
        if gpa_value < 0:
            gpa_value = None
    except (TypeError, ValueError):
        gpa_value = None

    returned = {
        'name': _normalize_text((extracted_data or {}).get('name')),
        'gpa': gpa_value,
        'major': _normalize_text((extracted_data or {}).get('major')),
        'degree': _normalize_text((extracted_data or {}).get('degree')),
        'university': _normalize_text((extracted_data or {}).get('university')),
        'skills': skills,
        'achievements': [item for item in achievements if item],
        'research_present': any('research' in item.lower() for item in achievements),
        'text': " ".join([
            _normalize_text((extracted_data or {}).get('name')),
            f"GPA {gpa_value}" if gpa_value is not None else "",
            _normalize_text((extracted_data or {}).get('major')),
            _normalize_text((extracted_data or {}).get('degree')),
            " ".join(skills),
            " ".join(achievements),
        ]).strip(),
    }
    return returned


def _get_embedding_vector(text):
    if not text:
        return []

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return []

    try:
        client = genai.Client(api_key=api_key)
        for model_name in ("models/text-embedding-004", "models/embedding-001"):
            try:
                response = client.models.embed_content(model=model_name, contents=text)
                if response and getattr(response, 'embeddings', None):
                    embedding = response.embeddings[0].values
                    if embedding:
                        return embedding
            except Exception:
                continue
    except Exception:
        return []
    return []


def _scholarship_keyword_tokens(scholarship):
    text = " ".join([
        scholarship.get('title', ''),
        scholarship.get('major', ''),
        scholarship.get('degree_level', ''),
        " ".join(scholarship.get('tags', [])),
    ]).lower()
    return re.findall(r"[a-z0-9+#.]+", text)


def _score_scholarship_match(profile, scholarship):
    score = 0
    major_value = profile.get('major', '').lower()
    degree_value = profile.get('degree', '').lower()
    scholarship_major = (scholarship.get('major') or '').lower()
    scholarship_degree = (scholarship.get('degree_level') or '').lower()
    scholarship_tags = [str(item).lower() for item in scholarship.get('tags', [])]
    scholarship_text = (scholarship.get('title') or ' ').lower() + ' ' + scholarship_major + ' ' + scholarship_degree + ' ' + ' '.join(scholarship_tags)
    skill_overlap = set(skill.lower() for skill in profile.get('skills', [])) & set(re.findall(r"[a-z0-9+#.]+", scholarship_text))

    if profile.get('gpa') is not None and scholarship.get('minimum_gpa') is not None:
        if profile['gpa'] >= scholarship['minimum_gpa']:
            score += 35
        elif profile['gpa'] >= (scholarship['minimum_gpa'] - 0.25):
            score += 15

    if major_value and major_value in scholarship_text:
        score += 20
    elif major_value and any(token in scholarship_text for token in re.findall(r"[a-z0-9]+", major_value)):
        score += 10

    if degree_value and degree_value in scholarship_degree:
        score += 20
    elif degree_value and any(token in scholarship_degree for token in re.findall(r"[a-z0-9]+", degree_value)):
        score += 10

    if skill_overlap:
        score += min(20, 5 * len(skill_overlap))

    if profile.get('research_present') and any(term in scholarship_text for term in ['research', 'innovation', 'ai', 'machine learning', 'technology', 'engineering']):
        score += 10

    if profile.get('achievements') and any(term in scholarship_text for term in ['achievement', 'award', 'scholarship', 'merit', 'leadership']):
        score += 5

    return min(100, max(0, score))


def find_relevant_scholarships(extracted_data, limit=6):
    profile = build_resume_match_profile(extracted_data or {})
    if not profile.get('text'):
        return {
            'count': 0,
            'matches': [],
            'summary': 'No academic or skill data was available to evaluate scholarship matches.',
            'recommendation_lines': ['Add your GPA, major, degree, and skills to improve scholarship matching suggestions.'],
        }

    query_embedding = _get_embedding_vector(profile['text'])
    matched_scholarships = []

    if query_embedding:
        try:
            pipeline = [
                {
                    '$vectorSearch': {
                        'index': 'vector_index',
                        'path': 'embedding',
                        'queryVector': query_embedding,
                        'numCandidates': 100,
                        'limit': limit * 5,
                    }
                }
            ]
            candidates = list(Scholarship._get_collection().aggregate(pipeline))
            for scholarship in candidates:
                scholarship_data = {
                    'id': str(scholarship.get('_id')),
                    'title': scholarship.get('title', 'Untitled Scholarship'),
                    'university': scholarship.get('university', 'N/A'),
                    'country': scholarship.get('country', 'N/A'),
                    'major': scholarship.get('major', 'All Majors'),
                    'degree_level': scholarship.get('degree_level', 'All Levels'),
                    'minimum_gpa': scholarship.get('minimum_gpa'),
                    'funding_amount': scholarship.get('funding_amount', 'N/A'),
                    'tags': scholarship.get('tags', []),
                }
                if profile.get('gpa') is not None and scholarship_data.get('minimum_gpa') is not None and profile['gpa'] < scholarship_data['minimum_gpa']:
                    continue
                match_score = _score_scholarship_match(profile, scholarship_data)
                if match_score <= 0:
                    continue
                scholarship_data['match_score'] = match_score
                matched_scholarships.append(scholarship_data)
        except Exception:
            matched_scholarships = []

    if not matched_scholarships:
        query_set = Scholarship.objects()
        if profile.get('gpa') is not None:
            query_set = query_set.filter(minimum_gpa__lte=profile['gpa'])
        if profile.get('degree'):
            query_set = query_set.filter(degree_level__icontains=profile['degree'])
        if profile.get('major'):
            query_set = query_set.filter(major__icontains=profile['major'])

        for scholarship in query_set[:limit * 5]:
            scholarship_data = {
                'id': str(scholarship.id),
                'title': scholarship.title,
                'university': scholarship.university,
                'country': scholarship.country,
                'major': scholarship.major,
                'degree_level': scholarship.degree_level,
                'minimum_gpa': scholarship.minimum_gpa,
                'funding_amount': scholarship.funding_amount,
                'tags': scholarship.tags,
            }
            match_score = _score_scholarship_match(profile, scholarship_data)
            if match_score > 0:
                scholarship_data['match_score'] = match_score
                matched_scholarships.append(scholarship_data)

    seen_ids = set()
    deduped_matches = []
    for scholarship in sorted(matched_scholarships, key=lambda item: item.get('match_score', 0), reverse=True):
        scholarship_id = scholarship.get('id')
        if scholarship_id in seen_ids:
            continue
        seen_ids.add(scholarship_id)
        deduped_matches.append(scholarship)
        if len(deduped_matches) >= limit:
            break

    if not deduped_matches:
        return {
            'count': 0,
            'matches': [],
            'summary': 'No scholarships were matched from your current academic profile.',
            'recommendation_lines': ['Improve your academic profile by adding a clearer major, GPA, and research or project experience.'],
        }

    research_emphasis = sum(1 for item in deduped_matches if any(keyword in (item.get('title', '') + ' ' + (item.get('major', '') or '')).lower() for keyword in ['research', 'innovation', 'ai', 'technology', 'data', 'engineering']))
    summary = f"Your resume matches the academic requirements for {len(deduped_matches)} scholarship(s)."
    if research_emphasis:
        summary += f" {research_emphasis} matching scholarship(s) emphasize research or technical innovation."
    if not profile.get('research_present'):
        summary += " Your resume does not clearly contain a Research section yet."

    recommendation_lines = [
        f"Your resume matches the academic requirements for {len(deduped_matches)} scholarship(s).",
    ]
    if research_emphasis:
        recommendation_lines.append(f"{research_emphasis} matching scholarship(s) emphasize research experience or technical innovation.")
    if not profile.get('research_present'):
        recommendation_lines.append('Add a Research or project section to make your academic work more visible to scholarship reviewers.')
    if profile.get('gpa') is not None:
        recommendation_lines.append(f"Your GPA of {profile['gpa']} aligns with the academic thresholds for the listed opportunities.")

    return {
        'count': len(deduped_matches),
        'matches': deduped_matches,
        'summary': summary,
        'recommendation_lines': recommendation_lines,
    }
