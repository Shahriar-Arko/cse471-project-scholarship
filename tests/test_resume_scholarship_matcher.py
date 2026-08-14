from app.services.resume_scholarship_matcher import build_resume_match_profile, find_relevant_scholarships


class _FakeScholarship:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'scholarship-1')
        self.title = kwargs.get('title', 'AI Research Scholarship')
        self.university = kwargs.get('university', 'Example University')
        self.country = kwargs.get('country', 'Bangladesh')
        self.major = kwargs.get('major', 'Computer Science')
        self.degree_level = kwargs.get('degree_level', 'Bachelor')
        self.minimum_gpa = kwargs.get('minimum_gpa', 3.5)
        self.funding_amount = kwargs.get('funding_amount', '$2000')
        self.tags = kwargs.get('tags', ['AI', 'Research'])

    def __iter__(self):
        return iter([])


class _FakeScholarshipQuery:
    def __init__(self, scholarships):
        self._scholarships = scholarships

    def filter(self, **kwargs):
        return self

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._scholarships[key]
        return self._scholarships[key]


def test_build_resume_match_profile_extracts_profile_data():
    profile = build_resume_match_profile({
        'name': 'Student Name',
        'gpa': '3.72',
        'major': 'Computer Science',
        'degree': 'Bachelor of Science',
        'skills': ['Python', 'Machine Learning', 'SQL'],
        'academic_achievements': ['Dean\'s List', 'Research assistant'],
    })

    assert profile['gpa'] == 3.72
    assert profile['major'] == 'Computer Science'
    assert profile['degree'] == 'Bachelor of Science'
    assert 'Python' in profile['skills']
    assert profile['research_present'] is True
    assert 'GPA 3.72' in profile['text']


def test_find_relevant_scholarships_returns_deterministic_summary(monkeypatch):
    scholarships = [
        _FakeScholarship(
            id='s1',
            title='AI Research Fellowship',
            major='Computer Science',
            degree_level='Bachelor',
            minimum_gpa=3.5,
            tags=['AI', 'Research', 'Machine Learning'],
        ),
        _FakeScholarship(
            id='s2',
            title='STEM Merit Scholarship',
            major='Engineering',
            degree_level='Bachelor',
            minimum_gpa=3.6,
            tags=['STEM', 'Innovation'],
        ),
    ]

    class _FakeScholarshipModel:
        objects = staticmethod(lambda: _FakeScholarshipQuery(scholarships))

    monkeypatch.setattr('app.services.resume_scholarship_matcher._get_embedding_vector', lambda text: [])
    monkeypatch.setattr('app.services.resume_scholarship_matcher.Scholarship', _FakeScholarshipModel)

    result = find_relevant_scholarships({
        'gpa': 3.72,
        'major': 'Computer Science',
        'degree': 'Bachelor of Science',
        'skills': ['Python', 'Machine Learning', 'SQL'],
        'academic_achievements': ['Research assistant', 'Dean\'s List'],
    }, limit=6)

    assert result['count'] >= 1
    assert 'matches the academic requirements' in result['summary']
    assert any('Research' in item['title'] for item in result['matches'])
    assert any('scholarship' in line.lower() for line in result['recommendation_lines'])


def test_find_relevant_scholarships_handles_missing_profile_data():
    result = find_relevant_scholarships({})

    assert result['count'] == 0
    assert 'No academic or skill data' in result['summary'] or 'No scholarships were matched' in result['summary']
    assert result['recommendation_lines']
