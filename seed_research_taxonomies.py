import time
import requests
from pymongo import MongoClient

# --- HARDCODED CREDENTIALS (Bypassing .env entirely) ---
MONGO_URI = os.getenv("MONGO_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["scholarship_matcher"]
collection = db["research_taxonomies"]

TAXONOMY_RECORDS = [
    # --- ORIGINAL RECORDS ---
    {
        "niche_title": "Federated Learning for Edge Healthcare Devices",
        "broad_domain": "Artificial Intelligence & Digital Health",
        "description": "Privacy-preserving distributed machine learning, on-device model training, decentralized optimization, wearable biosensors, and TinyML for medical monitoring.",
        "core_skills": ["PyTorch", "Federated Optimization", "C++", "Differential Privacy", "TinyML"]
    },
    {
        "niche_title": "Medical Image Computing & Clinical Vision",
        "broad_domain": "Biomedical Engineering & AI",
        "description": "Computer vision for diagnostic pathology, MRI and CT organ segmentation, DICOM processing, tumor boundary detection, and convolutional neural networks in oncology.",
        "core_skills": ["PyTorch", "OpenCV", "SimpleITK", "Deep Learning", "Python"]
    },
    {
        "niche_title": "Autonomous Aerial Robotics & Visual SLAM",
        "broad_domain": "Robotics & Control Systems",
        "description": "Simultaneous localization and mapping, state estimation, drone swarm coordination, LiDAR-inertial odometry in GPS-denied environments, and ROS navigation pipelines.",
        "core_skills": ["ROS2", "C++", "Kalman Filters", "Computer Vision", "Gazebo", "Python"]
    },
    {
        "niche_title": "Post-Quantum Cryptography & Lattice Security",
        "broad_domain": "Cybersecurity & Quantum Computing",
        "description": "Lattice-based encryption, quantum-resistant key exchange algorithms, side-channel attack mitigation, mathematical number theory, and hardware crypto acceleration.",
        "core_skills": ["C++", "Abstract Algebra", "Cryptographic Protocols", "Information Theory", "Python"]
    },
    {
        "niche_title": "Computational Structural Biology & Protein Folding",
        "broad_domain": "Bioinformatics & Biophysics",
        "description": "Molecular dynamics simulations, AlphaFold transformer architectures, cryo-EM density mapping, genomic sequence alignment, and protein-ligand docking.",
        "core_skills": ["Python", "Biopython", "PyMOL", "Statistical Mechanics", "Deep Learning"]
    },
    {
        "niche_title": "Reinforcement Learning for Smart Energy Grids",
        "broad_domain": "Energy Systems & AI",
        "description": "Dynamic pricing optimization, multi-agent reinforcement learning, renewable power load balancing, microgrid dispatch, and grid stability analysis.",
        "core_skills": ["Python", "Reinforcement Learning", "Power Systems Modeling", "PyTorch", "MATLAB"]
    },
    {
        "niche_title": "Neuromorphic Computing & Spiking Neural Networks",
        "broad_domain": "Computer Architecture & Neuroscience",
        "description": "Event-driven spike-based hardware, memristor circuits, ultra-low power neuromorphic chips, bio-inspired sensory processing, and synaptic plasticity modeling.",
        "core_skills": ["Python", "SNNs", "Verilog", "VLSI Design", "PyTorch"]
    },
    {
        "niche_title": "Natural Language Processing for Clinical Text Mining",
        "broad_domain": "NLP & Health Informatics",
        "description": "Electronic health record parsing, clinical entity extraction, bio-transformers, medical question answering, and relation extraction from biomedical literature.",
        "core_skills": ["Python", "HuggingFace Transformers", "spaCy", "PyTorch", "BioBERT"]
    },
    
    # --- NEWLY ADDED RECORDS ---
    {
        "niche_title": "Adversarial Machine Learning & Model Defense",
        "broad_domain": "Cybersecurity & Artificial Intelligence",
        "description": "Evaluating neural network vulnerabilities, crafting adversarial perturbations, robust model training, and mitigating data poisoning attacks in AI systems.",
        "core_skills": ["Python", "PyTorch", "Adversarial Robustness", "Threat Modeling", "TensorFlow"]
    },
    {
        "niche_title": "Zero Trust Network Architecture & Identity Management",
        "broad_domain": "Cybersecurity & Network Engineering",
        "description": "Implementing continuous authentication, micro-segmentation, role-based access control (RBAC), and securing cloud-native infrastructures.",
        "core_skills": ["Network Protocols", "Identity and Access Management (IAM)", "Cloud Security", "Wireshark", "Python"]
    },
    {
        "niche_title": "Zero-Knowledge Proofs & Blockchain Scalability",
        "broad_domain": "Cryptography & Distributed Systems",
        "description": "zk-SNARKs/zk-STARKs protocol design, layer-2 blockchain rollups, smart contract auditing, and privacy-preserving decentralized applications.",
        "core_skills": ["Solidity", "Cryptography", "Rust", "Abstract Algebra", "Distributed Systems"]
    },
    {
        "niche_title": "Digital Forensics & Incident Response (DFIR)",
        "broad_domain": "Cybersecurity",
        "description": "Analyzing malware payloads, network traffic anomalies, memory forensics, threat hunting, and reverse engineering malicious binaries.",
        "core_skills": ["Reverse Engineering", "Wireshark", "Python", "Malware Analysis", "EnCase"]
    },
    {
        "niche_title": "AI-Driven Drug Discovery & Cheminformatics",
        "broad_domain": "Pharmacology & Artificial Intelligence",
        "description": "High-throughput virtual screening, deep learning for molecular property prediction, quantitative structure-activity relationship (QSAR) modeling, and generative chemistry.",
        "core_skills": ["Python", "RDKit", "PyTorch", "Cheminformatics", "Molecular Dynamics"]
    },
    {
        "niche_title": "Targeted Nanoparticle Drug Delivery Systems",
        "broad_domain": "Pharmaceutics & Nanotechnology",
        "description": "Formulation of lipid nanoparticles, polymeric drug carriers, controlled release kinetics, and overcoming biological barriers for precision medicine.",
        "core_skills": ["Nanofabrication", "Pharmacokinetics", "Biomaterials", "HPLC", "Cell Culture"]
    },
    {
        "niche_title": "CRISPR-Cas9 Gene Editing & Microbiome Engineering",
        "broad_domain": "Molecular Biology & Biotechnology",
        "description": "Precision genome editing, synthetic gene circuits, gut microbiome therapeutics, plasmid design, and off-target effect analysis.",
        "core_skills": ["CRISPR Design", "PCR", "Flow Cytometry", "Bioinformatics", "Genomics"]
    },
    {
        "niche_title": "Host-Pathogen Interactions & Antimicrobial Resistance",
        "broad_domain": "Microbiology & Infectious Diseases",
        "description": "Investigating bacterial virulence factors, mechanism of antibiotic resistance, biofilm formation, and discovering novel antimicrobial peptides.",
        "core_skills": ["Microbial Culturing", "Transcriptomics", "Assay Development", "Microscopy", "Virology"]
    },
    {
        "niche_title": "Synthetic Biology & Metabolic Pathway Optimization",
        "broad_domain": "Biotechnology & Systems Biology",
        "description": "Designing artificial metabolic pathways, microbial fermentation for biofuel production, enzyme engineering, and multi-omics data integration.",
        "core_skills": ["Systems Biology", "Bioprocess Engineering", "MATLAB", "Python", "Gene Expression Analysis"]
    },
    {
        "niche_title": "Generative AI & Multimodal Foundation Models",
        "broad_domain": "Artificial Intelligence & Machine Learning",
        "description": "Training large language models, retrieval-augmented generation (RAG), vision-language integration, prompt engineering, and model fine-tuning (LoRA).",
        "core_skills": ["Python", "HuggingFace", "PyTorch", "LLMs", "NLP"]
    }
]

def get_api_embedding(text):
    """Generates 768-D embedding via Gemini API using the new AQ header auth."""
    if not GEMINI_API_KEY or not text:
        return []

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
    
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 768
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json().get("embedding", {}).get("values", [])
        else:
            print(f"⚠️ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return []

def seed_taxonomies():
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY missing in script")
        return

    print("🚀 Seeding Academic Research Taxonomies with Gemini Embeddings...")
    documents = []

    for idx, item in enumerate(TAXONOMY_RECORDS, 1):
        text_to_embed = f"{item['niche_title']}. Domain: {item['broad_domain']}. Description: {item['description']}. Core Skills: {', '.join(item['core_skills'])}"
        print(f"[{idx}/{len(TAXONOMY_RECORDS)}] Embedding: {item['niche_title']}...")
        
        vec = get_api_embedding(text_to_embed)
        if vec:
            item["embedding"] = vec
            documents.append(item)
        else:
            print(f"❌ Failed to embed {item['niche_title']}")
        
        time.sleep(0.4)

    if documents:
        collection.delete_many({})
        collection.insert_many(documents)
        print(f"\n✅ Successfully inserted {len(documents)} pre-embedded research taxonomies into MongoDB!")

if __name__ == "__main__":
    seed_taxonomies()