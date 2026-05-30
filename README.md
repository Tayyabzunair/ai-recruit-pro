# 🚀 AI Recruit Pro

> **An intelligent job portal powered by RAG (Retrieval-Augmented Generation), semantic search, and Gemini AI** — built to make hiring smarter, faster, and data-driven.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![Gemini](https://img.shields.io/badge/Gemini-2.5-purple) ![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange)

## ✨ Features

- 🤖 **RAG-Powered Chatbot** — Recruiters can query their candidate pool in plain English (or Roman Urdu!) and get instant insights from Gemini-powered AI
- 📄 **AI Resume Parser** — PyMuPDF + Gemini automatically extracts skills, experience, education, and contact info from PDFs
- 🎯 **Smart Match Scoring** — Custom skill-matching algorithm with synonym expansion and partial matching
- 🔍 **Semantic Search** — ChromaDB + sentence-transformers for context-aware candidate ranking
- 📊 **Real-Time Analytics** — Beautiful charts for hiring pipeline insights
- 📧 **Automated Email Notifications** — Welcome, application confirmations, and status updates
- 🌙 **Dark Mode** — Premium UI with smooth transitions
- 🔐 **Multi-Tenant Isolation** — Each recruiter sees only their own candidates (ChromaDB owner_id filtering)

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0, SQLAlchemy 2.0, Flask-Login, Flask-WTF |
| AI/ML | Google Gemini 2.5 Flash, sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB (persistent) |
| Frontend | Tailwind CSS, Alpine.js, GSAP, AOS |
| Database | SQLite (dev), PostgreSQL (prod-ready) |
| PDF | PyMuPDF |
| Email | Flask-Mail with async sending |

## 🏗️ Architecture

```
User Query → Embedding (MiniLM) → ChromaDB Search (filtered by owner_id)
          → Context Builder → Gemini 2.5 → Markdown Response → UI
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11 (required — newer versions may have ML lib issues)
- Gemini API key ([get one free here](https://aistudio.google.com/app/apikey))

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/ai-recruit-pro.git
cd ai-recruit-pro

# 2. Create virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GENAI_API_KEY and mail credentials

# 5. Initialize database
flask --app run db init
flask --app run db migrate -m "initial"
flask --app run db upgrade

# 6. Run!
python run.py
```

Open `http://localhost:5000` and sign up as either a Recruiter or Candidate.


## 🧠 How the RAG Pipeline Works

1. **Indexing:** When a candidate applies, their resume text + metadata is embedded with `all-MiniLM-L6-v2` and stored in ChromaDB with `owner_id` tag
2. **Query Classification:** Incoming queries are routed — stats queries hit SQL directly, candidate queries go through semantic search
3. **Retrieval:** Top-5 most relevant candidates retrieved with cosine similarity (filtered by `owner_id` for tenant isolation)
4. **Generation:** Context + query → Gemini 2.5 Flash → markdown-formatted answer with source pills

## 📁 Project Structure

```
ai-recruit-pro/
├── app/
│   ├── blueprints/        # Auth, Owner, Candidate, Chatbot, Main
│   ├── models/            # User, Job, Application
│   ├── services/          # AI, RAG, Embeddings, Vector Store, Email
│   ├── templates/         # Jinja2 templates with Tailwind
│   ├── utils/             # Decorators, validators, helpers
│   ├── config.py
│   └── __init__.py        # App factory
├── requirements.txt
├── run.py
└── README.md
```

## 🛡️ Security Features

- Bcrypt password hashing
- CSRF protection on all forms (Flask-WTF)
- Role-based access control with custom decorators
- Multi-tenant data isolation in vector store
- Secure file upload with extension validation + safe filenames
- SQL injection protection via SQLAlchemy ORM

## 🌟 Highlights

- **Multi-language support:** Chatbot understands English AND Roman Urdu queries
- **Async email sending:** Background threads, zero HTTP blocking
- **Auto-indexing:** Applications are vectorized at submission time
- **Smart skill matching:** Handles synonyms (js→javascript, ml→machine learning)

## 🚧 Roadmap

- [ ] Cover letter generator
- [ ] Interview scheduling integration
- [ ] Bulk resume upload
- [ ] Advanced analytics dashboard
- [ ] Docker deployment
- [ ] PostgreSQL production migration

## 📝 License

MIT License — feel free to use and adapt.

## 👨‍💻 Author

**Muhammad Tayyab Zunair** — [LinkedIn](www.linkedin.com/in/mtayyabzunair) | [GitHub](https://github.com/Tayyabzunair)

---

⭐ If you found this useful, please star the repo!
