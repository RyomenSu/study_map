"""
Analytics Service :8002
Reads live data from the main studyportal database.
Writes only anlt_predictions and anlt_recommendations.
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import AsyncGroq
from aiokafka import AIOKafkaConsumer

from ml_model import compute_student_features, predict_pass_probability
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://studyportal:studyportal_pass@localhost:5432/studyportal")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

pool: asyncpg.Pool = None
groq_client: AsyncGroq = None


async def _ensure_tables(conn: asyncpg.Connection):
    """Create analytics-only tables that don't exist in the main app."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS anlt_predictions (
            id SERIAL PRIMARY KEY,
            student_id UUID NOT NULL,
            subject VARCHAR(255) NOT NULL,
            exam_pass_probability FLOAT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS anlt_recommendations (
            id SERIAL PRIMARY KEY,
            region_name VARCHAR(100),
            school_id UUID,
            level VARCHAR(20) NOT NULL,
            content JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_anlt_pred_student ON anlt_predictions(student_id, subject);
    """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, groq_client
    pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    async with pool.acquire() as conn:
        await _ensure_tables(conn)
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    task = asyncio.create_task(kafka_consumer_loop())
    cron_task = asyncio.create_task(daily_recommendations_cron())
    yield
    task.cancel()
    cron_task.cancel()
    await pool.close()


app = FastAPI(title="Analytics Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Kafka Consumer ────────────────────────────────────────────────────────────

async def kafka_consumer_loop():
    consumer = AIOKafkaConsumer(
        "homework.graded",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode()),
        group_id="analytics-service",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await handle_graded_event(msg.value)
    finally:
        await consumer.stop()


async def handle_graded_event(data: dict):
    student_id = data.get("student_id")
    assignment_id = data.get("assignment_id")
    if not student_id:
        return

    subject = None
    if assignment_id:
        async with pool.acquire() as conn:
            subject = await conn.fetchval("""
                SELECT c.name FROM assignments a
                JOIN courses c ON c.id = a.course_id
                WHERE a.id = $1::uuid
            """, assignment_id)

    asyncio.create_task(update_prediction(student_id, subject or "Unknown"))
    asyncio.create_task(check_anomalies(data, subject))


async def update_prediction(student_id: str, subject: str):
    features = await compute_student_features(pool, student_id, subject)
    if not features:
        return
    prob = predict_pass_probability(features)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO anlt_predictions (student_id, subject, exam_pass_probability)
            VALUES ($1::uuid, $2, $3)
        """, student_id, subject, prob)


# ── Anomaly Detection ─────────────────────────────────────────────────────────

ANOMALY_LOG: list[dict] = []


async def check_anomalies(data: dict, subject: str | None):
    student_id = data.get("student_id")
    score = data.get("score", 0)
    max_score = data.get("max_score", 100)
    pct = (score / max_score * 100) if max_score else 0

    async with pool.acquire() as conn:
        prev_pct = await conn.fetchval("""
            SELECT g.score / g.max_score * 100
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN assignments a ON a.id = s.assignment_id
            JOIN courses c ON c.id = a.course_id
            WHERE s.student_id = $1::uuid AND c.name = $2
            ORDER BY g.graded_at DESC
            OFFSET 1 LIMIT 1
        """, student_id, subject)

        if prev_pct is not None and pct >= 85 and prev_pct <= 40:
            ANOMALY_LOG.append({
                "type": "student_sudden_jump",
                "student_id": student_id,
                "from": round(float(prev_pct), 1),
                "to": round(pct, 1),
                "subject": subject,
                "ts": datetime.now().isoformat(),
            })

        school_id = await conn.fetchval(
            "SELECT school_id FROM users WHERE id = $1::uuid", student_id
        )
        if school_id:
            night_start = datetime.now() - timedelta(hours=12)
            class_scores = await conn.fetch("""
                SELECT g.score / g.max_score * 100 AS pct
                FROM grades g
                JOIN submissions s ON s.id = g.submission_id
                JOIN assignments a ON a.id = s.assignment_id
                JOIN courses c ON c.id = a.course_id
                JOIN users u ON u.id = s.student_id
                WHERE u.school_id = $1 AND c.name = $2 AND g.graded_at >= $3
            """, school_id, subject, night_start)

            if len(class_scores) >= 5 and all(float(r["pct"]) >= 95 for r in class_scores):
                ANOMALY_LOG.append({
                    "type": "class_perfect_night",
                    "school_id": str(school_id),
                    "subject": subject,
                    "count": len(class_scores),
                    "ts": datetime.now().isoformat(),
                })


# ── Groq Recommendations ──────────────────────────────────────────────────────

async def generate_regional_recommendations(region_stats: dict) -> list[str]:
    prompt = f"""You are an education policy advisor for the Ministry of Education of Uzbekistan.

Regional stats for {region_stats['region_name']}:
- Average score: {region_stats['avg_score']:.1f}/100
- At-risk students: {region_stats['at_risk_count']}
- Score trend (last month): {region_stats['trend']:+.1f}

Generate exactly 3 concrete action items to improve performance.
Each must include: what to do, who is responsible, expected result within 30 days.
Return JSON array of strings only, no explanation."""

    resp = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=600,
    )
    text = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return [text]


async def daily_recommendations_cron():
    while True:
        now = datetime.now()
        next_run = now.replace(hour=0, minute=30, second=0) + timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        await run_all_recommendations()


async def run_all_recommendations():
    async with pool.acquire() as conn:
        regions = await conn.fetch(
            "SELECT DISTINCT region FROM schools WHERE region IS NOT NULL ORDER BY region"
        )
        for region_row in regions:
            region_name = region_row["region"]
            stats = await conn.fetchrow("""
                SELECT
                    ROUND(AVG(g.score / g.max_score * 100)::numeric, 1) AS avg_score,
                    COUNT(*) FILTER (WHERE g.score / g.max_score < 0.5) AS at_risk_count,
                    AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at >= NOW()-INTERVAL '30 days')
                    - AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at < NOW()-INTERVAL '30 days') AS trend
                FROM grades g
                JOIN submissions s ON s.id = g.submission_id
                JOIN users u ON u.id = s.student_id
                JOIN schools sc ON sc.id = u.school_id
                WHERE sc.region = $1
            """, region_name)

            region_stats = {
                "region_name": region_name,
                "avg_score": float(stats["avg_score"] or 0),
                "at_risk_count": int(stats["at_risk_count"] or 0),
                "trend": float(stats["trend"] or 0),
            }
            recs = await generate_regional_recommendations(region_stats)
            await conn.execute("""
                INSERT INTO anlt_recommendations (region_name, level, content)
                VALUES ($1, 'regional', $2)
            """, region_name, json.dumps({"actions": recs, "stats_snapshot": region_stats}))


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/student/{student_id}/dashboard")
async def student_dashboard(student_id: str):
    async with pool.acquire() as conn:
        student = await conn.fetchrow("""
            SELECT u.id, u.full_name AS name, u.school_id,
                   sc.name AS school_name, sc.region,
                   g.name AS group_name
            FROM users u
            LEFT JOIN schools sc ON sc.id = u.school_id
            LEFT JOIN groups g ON g.id = u.group_id
            WHERE u.id = $1::uuid AND u.role = 'student'
        """, student_id)
        if not student:
            raise HTTPException(404, "Student not found")

        grades = await conn.fetch("""
            SELECT c.name AS subject,
                   g.score, g.max_score,
                   ROUND((g.score / g.max_score * 100)::numeric, 1) AS pct,
                   g.feedback, g.is_ai_graded, g.graded_at
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN assignments a ON a.id = s.assignment_id
            JOIN courses c ON c.id = a.course_id
            WHERE s.student_id = $1::uuid
            ORDER BY g.graded_at DESC LIMIT 30
        """, student_id)

        predictions = await conn.fetch("""
            SELECT DISTINCT ON (subject) subject, exam_pass_probability, created_at
            FROM anlt_predictions WHERE student_id = $1::uuid
            ORDER BY subject, created_at DESC
        """, student_id)

    progress: dict[str, list] = {}
    weak_freq: dict[str, int] = {}
    for row in grades:
        progress.setdefault(row["subject"], []).append({
            "score": row["score"],
            "max_score": row["max_score"],
            "pct": float(row["pct"]),
            "feedback": row["feedback"],
            "date": row["graded_at"].isoformat(),
        })
        if float(row["pct"]) < 60:
            weak_freq[row["subject"]] = weak_freq.get(row["subject"], 0) + 1

    roadmap = [{"topic": k, "frequency": v}
               for k, v in sorted(weak_freq.items(), key=lambda x: -x[1])[:5]]

    return {
        "student": {
            "id": str(student["id"]),
            "name": student["name"],
            "school": student["school_name"],
            "region": student["region"],
            "group": student["group_name"],
        },
        "progress": progress,
        "predictions": [
            {"subject": p["subject"], "exam_pass_probability": p["exam_pass_probability"],
             "created_at": p["created_at"].isoformat()}
            for p in predictions
        ],
        "roadmap": roadmap,
    }


@app.get("/school/{school_id}/stats")
async def school_stats(school_id: str):
    async with pool.acquire() as conn:
        school = await conn.fetchrow(
            "SELECT id, name, region, city FROM schools WHERE id = $1::uuid", school_id
        )
        if not school:
            raise HTTPException(404, "School not found")

        subject_stats = await conn.fetch("""
            SELECT c.name AS subject,
                   ROUND(AVG(g.score / g.max_score * 100)::numeric, 1) AS avg_score,
                   COUNT(*) FILTER (WHERE g.score / g.max_score < 0.5) AS at_risk,
                   COUNT(DISTINCT s.student_id) AS student_count
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN assignments a ON a.id = s.assignment_id
            JOIN courses c ON c.id = a.course_id
            JOIN users u ON u.id = s.student_id
            WHERE u.school_id = $1::uuid AND g.graded_at >= NOW() - INTERVAL '90 days'
            GROUP BY c.name
            ORDER BY avg_score DESC
        """, school_id)

        recs = await conn.fetch("""
            SELECT content, created_at FROM anlt_recommendations
            WHERE school_id = $1::uuid ORDER BY created_at DESC LIMIT 3
        """, school_id)

    return {
        "school": {"id": str(school["id"]), "name": school["name"],
                   "region": school["region"], "city": school["city"]},
        "subject_stats": [dict(r) for r in subject_stats],
        "recommendations": [json.loads(r["content"]) for r in recs],
    }


@app.get("/national/stats")
async def national_stats():
    async with pool.acquire() as conn:
        region_rows = await conn.fetch("""
            SELECT sc.region AS name,
                   ROUND(AVG(g.score / g.max_score * 100)::numeric, 1) AS avg_score,
                   COUNT(*) FILTER (WHERE g.score / g.max_score < 0.5) AS at_risk_count,
                   COUNT(DISTINCT u.id) AS student_count
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN users u ON u.id = s.student_id
            JOIN schools sc ON sc.id = u.school_id
            WHERE g.graded_at >= NOW() - INTERVAL '90 days'
            GROUP BY sc.region
            ORDER BY avg_score DESC
        """)

        trends = await conn.fetch("""
            SELECT sc.region,
                   AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at >= NOW()-INTERVAL '30 days') AS recent,
                   AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at BETWEEN NOW()-INTERVAL '60 days'
                                                                                    AND NOW()-INTERVAL '30 days') AS prev
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN users u ON u.id = s.student_id
            JOIN schools sc ON sc.id = u.school_id
            GROUP BY sc.region
        """)
        trend_map = {
            r["region"]: round((r["recent"] or 0) - (r["prev"] or 0), 2)
            for r in trends
        }

    result = []
    for row in region_rows:
        trend = trend_map.get(row["name"], 0)
        result.append({
            "name": row["name"],
            "avg_score": float(row["avg_score"] or 0),
            "at_risk_count": int(row["at_risk_count"] or 0),
            "student_count": int(row["student_count"] or 0),
            "trend": trend,
            "anomaly": trend > 15,
        })

    return {"regions": result, "total_regions": len(result)}


@app.get("/national/recommendations")
async def national_recommendations():
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT region_name, content, created_at
            FROM anlt_recommendations WHERE level = 'regional'
            ORDER BY created_at DESC LIMIT 28
        """)
    return {
        "recommendations": [
            {"region": r["region_name"], **json.loads(r["content"]),
             "created_at": r["created_at"].isoformat()}
            for r in rows
        ]
    }


@app.get("/alerts")
async def get_alerts():
    async with pool.acquire() as conn:
        region_anomalies = await conn.fetch("""
            SELECT sc.region AS name,
                   AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at >= NOW()-INTERVAL '30 days') AS recent,
                   AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at BETWEEN NOW()-INTERVAL '60 days'
                                                                                    AND NOW()-INTERVAL '30 days') AS prev
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN users u ON u.id = s.student_id
            JOIN schools sc ON sc.id = u.school_id
            GROUP BY sc.region
            HAVING AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at >= NOW()-INTERVAL '30 days')
                 > AVG(g.score / g.max_score * 100) FILTER (WHERE g.graded_at BETWEEN NOW()-INTERVAL '60 days'
                                                                                      AND NOW()-INTERVAL '30 days') * 1.30
        """)

    alerts = []
    for row in region_anomalies:
        if row["prev"]:
            alerts.append({
                "type": "region_spike",
                "region": row["name"],
                "recent_avg": round(float(row["recent"]), 1),
                "prev_avg": round(float(row["prev"]), 1),
                "change_pct": round((row["recent"] - row["prev"]) / row["prev"] * 100, 1),
            })
    alerts.extend(ANOMALY_LOG[-50:])
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/internal/run-recommendations")
async def trigger_recommendations():
    asyncio.create_task(run_all_recommendations())
    return {"status": "started"}


@app.get("/health")
async def health():
    return {"status": "ok"}
