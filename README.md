# Study Map

AI-powered educational platform with automated homework grading and national analytics dashboard.

Built for hackathon demo — runs fully locally with one Docker command.

---

## Quick Start

```bash
# 1. Create .env and add your API keys (see Environment Variables section below)
# 2. Start all services
docker compose up -d --build

# 3. Seed demo data
docker compose exec analytics python generate_demo_data_studyportal.py
```

| Service | URL |
|---|---|
| Student/Teacher Portal | http://localhost:3000 |
| AI Analytics Dashboard | http://localhost:3001 |
| Backend API | http://localhost:8000 |

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Teacher | `kaxramon@gmail.com` | `password123` |
| Student | `arman@gmail.com` | `password123` |
| Admin | `admin2@gmail.com` | `admin1234` |

---

## Portal Features (localhost:3000)

- **Student** — view courses, submit PDF homework, see AI-generated score and feedback
- **Teacher** — manage assignments, view all student grades with feedback
- **Admin** — access to Analytics dashboard via navbar

### Pipeline

```mermaid
flowchart LR
    A([Дз / Тест\nPDF Upload]) --> B([OCR\nEasyOCR + Qwen 2.5])
    B --> C([AI Grading\nGemini / Mistral])
    C --> D([Kafka])
    D --> E([Аналитика + ML\nXGBoost])
    E --> F([Государственный\nDashboard])

    style A fill:#86efac,stroke:#166534,color:#000
    style F fill:#86efac,stroke:#166534,color:#000
    style B fill:#60a5fa,stroke:#1e40af,color:#000
    style C fill:#60a5fa,stroke:#1e40af,color:#000
    style D fill:#60a5fa,stroke:#1e40af,color:#000
    style E fill:#60a5fa,stroke:#1e40af,color:#000
```

---

## AI Analytics Dashboard (localhost:3001)

The analytics service reads live data from the main database and provides three views:

### National View
- Interactive map of Uzbekistan with all 14 regions
- Each region shows: average score, trend (↑↓), at-risk student count
- Color coding: green ≥70, yellow 50–70, red <50
- AI-generated recommendations per region (powered by Groq LLaMA 3.3)

### School View
- Per-subject performance breakdown
- Progress bars for each subject
- School-level AI recommendations

### Student View
- Score history chart across subjects
- Exam pass probability prediction (XGBoost ML model)
- Weekly study roadmap based on weak topics

### How Predictions Work
Features fed into XGBoost classifier:
- Average score (last 5 submissions)
- Score trend
- Weak topic frequency
- Submission rate

---

## Architecture

```
frontend        :3000  React + Vite
backend         :8000  FastAPI + PostgreSQL + Kafka
ocr-service     :8002  EasyOCR + Qwen 2.5 (Ollama)
grading-service :8001  Gemini 2.0 Flash / Mistral 7B fallback
analytics       :8003  FastAPI + XGBoost + Groq
analytics-frontend :3001  React + Leaflet map
kafka                  Apache Kafka (event bus)
postgres               PostgreSQL 16
rustfs          :9000  S3-compatible file storage
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

Get free API keys:
- **Gemini** → https://aistudio.google.com/apikey
- **Groq** → https://console.groq.com/keys

### No API keys? Use local Ollama instead

Install Ollama → https://ollama.com and run:

```bash
ollama serve
ollama pull mistral:7b        # for grading
ollama pull qwen2.5:7b-instruct  # for OCR cleanup
```

The system automatically falls back to local Ollama if API quota is exceeded or keys are not set.
