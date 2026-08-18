import os
from werkzeug.security import generate_password_hash
from mongoengine import connect
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017/scholarship_matcher"
connect(host=MONGO_URI)

from app.models.professor import Professor, Publication, GrantProject

professors_data = [
    {
        "full_name": "Dr. Andrew Ng",
        "email": "andrew.ng@stanford.edu",
        "password": generate_password_hash("password123"),
        "title": "Adjunct Professor",
        "institution": "Stanford University",
        "department": "Department of Computer Science",
        "country": "United States",
        "office_location": "Gates Computer Science Building 3A",
        "website_url": "https://www.andrewng.org",
        "primary_domain": "Artificial Intelligence & Machine Learning",
        "research_interests": ["Deep Learning", "Generative AI", "Computer Vision", "AI Healthcare"],
        "bio_summary": "Focusing on democratizing AI, foundational LLMs, and scalable machine learning applications for global health and education.",
        "lab_name": "Stanford AI Lab (SAIL)",
        "lab_website": "https://ai.stanford.edu",
        "accepting_students": True,
        "has_funding": True,
        "funding_types": ["RA", "TA", "Fully-Funded Fellowship"],
        "open_positions_count": 3,
        "publications": [
            Publication(title="Building Scalable Foundation Models with Reinforcement Learning", year=2024, venue="NeurIPS", citation_url="https://scholar.google.com", citations_count=1420),
            Publication(title="Deep Learning for Low-Resource Medical Diagnostics", year=2023, venue="Nature Medicine", citation_url="https://scholar.google.com", citations_count=980)
        ],
        "grant_projects": [
            GrantProject(title="NSF Expeditions in Distributed Healthcare AI", agency="National Science Foundation", amount="$2.5M", status="Active")
        ]
    },
    {
        "full_name": "Dr. Yueqi Song",
        "email": "yueqis@andrew.cmu.edu",
        "password": generate_password_hash("password123"),
        "title": "Assistant Professor",
        "institution": "Carnegie Mellon University",
        "department": "Language Technologies Institute",
        "country": "United States",
        "office_location": "Newell-Simon Hall 4202",
        "website_url": "https://www.cmu.edu/lti",
        "primary_domain": "Natural Language Processing",
        "research_interests": ["NLP", "Inclusive AI Agents", "Multimodal Language Models", "Human-AI Interaction"],
        "bio_summary": "Pioneering interactive NLP systems and multimodal agents that communicate robustly across diverse, multilingual populations.",
        "lab_name": "Language Intelligence & Interaction Lab",
        "lab_website": "https://lti.cs.cmu.edu",
        "accepting_students": True,
        "has_funding": True,
        "funding_types": ["RA", "Fellowship"],
        "open_positions_count": 2,
        "publications": [
            Publication(title="Robust Generalist Agents via Multi-Turn Dialogue Tuning", year=2025, venue="ACL 2025", citation_url="https://arxiv.org", citations_count=410),
            Publication(title="Cross-Lingual Representation in Large Language Models", year=2024, venue="EMNLP 2024", citation_url="https://arxiv.org", citations_count=320)
        ],
        "grant_projects": [
            GrantProject(title="Inclusive Language Technologies for Underserved Dialects", agency="DARPA", amount="$1.1M", status="Active")
        ]
    },
    {
        "full_name": "Dr. Sarah Jenkins",
        "email": "s.jenkins@ox.ac.uk",
        "password": generate_password_hash("password123"),
        "title": "Associate Professor",
        "institution": "University of Oxford",
        "department": "Department of Engineering Science",
        "country": "United Kingdom",
        "office_location": "Thom Building Room 204",
        "website_url": "https://www.eng.ox.ac.uk",
        "primary_domain": "Biomedical Engineering & Robotics",
        "research_interests": ["Surgical Robotics", "Biomechatronics", "Haptic Feedback", "Prosthetics"],
        "bio_summary": "Designing next-generation micro-robotic instruments for minimally invasive surgical procedures and intelligent prosthetics.",
        "lab_name": "Oxford Biorobotics & Smart Sensing Lab",
        "lab_website": "https://eng.ox.ac.uk/biorobotics",
        "accepting_students": True,
        "has_funding": True,
        "funding_types": ["RA", "TA"],
        "open_positions_count": 2,
        "publications": [
            Publication(title="Adaptive Haptic Teleoperation for Precision Micro-Surgery", year=2024, venue="IEEE Trans. Robotics", citation_url="https://ieeexplore.ieee.org", citations_count=215)
        ],
        "grant_projects": [
            GrantProject(title="Horizon Europe Micro-Robotic Surgical Autonomy", agency="European Research Council", amount="€1.8M", status="Active")
        ]
    },
    {
        "full_name": "Dr. Kenji Takahashi",
        "email": "takahashi@is.u-tokyo.ac.jp",
        "password": generate_password_hash("password123"),
        "title": "Full Professor",
        "institution": "University of Tokyo",
        "department": "Graduate School of Information Science",
        "country": "Japan",
        "office_location": "Hongo Campus Engineering Bldg 7",
        "website_url": "https://www.u-tokyo.ac.jp",
        "primary_domain": "Quantum Computing & Information Security",
        "research_interests": ["Quantum Algorithms", "Post-Quantum Cryptography", "Cybersecurity", "Distributed Ledgers"],
        "bio_summary": "Investigating fault-tolerant quantum algorithms, quantum error correction codes, and cryptosystems resilient to quantum attacks.",
        "lab_name": "Quantum Information & Cryptography Laboratory",
        "lab_website": "https://is.u-tokyo.ac.jp/quantum",
        "accepting_students": True,
        "has_funding": True,
        "funding_types": ["RA", "MEXT Sponsorship"],
        "open_positions_count": 4,
        "publications": [
            Publication(title="Lattice-Based Cryptographic Protocols for Decentralized Networks", year=2024, venue="IEEE S&P (Oakland)", citation_url="https://ieeexplore.ieee.org", citations_count=530)
        ],
        "grant_projects": [
            GrantProject(title="JST Moonshot R&D Quantum Information Security", agency="Japan Science and Technology", amount="¥180M", status="Active")
        ]
    }
]

def seed_professors():
    print("🌱 Seeding Professor & Lab Database...")
    for data in professors_data:
        existing = Professor.objects(email=data["email"]).first()
        if not existing:
            prof = Professor(**data)
            prof.save()
            print(f"✅ Created Professor: {prof.full_name} ({prof.institution})")
        else:
            print(f"ℹ️ Already exists: {existing.full_name}")
    print("\n🎉 Seeding complete! Database is ready.")

if __name__ == "__main__":
    seed_professors()