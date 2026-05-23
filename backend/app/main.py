from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.models import Base  # noqa: F401 — ensures all models are registered
from app.routers import analytics, assignments, attendance, auth, courses, grades, groups, schools, submissions, users
from app.services import storage
from app.services.kafka import start_graded_consumer, start_producer, stop_graded_consumer, stop_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES groups(id)"
        ))
        await conn.execute(text(
            "ALTER TABLE grades ADD COLUMN IF NOT EXISTS is_ai_graded BOOLEAN DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE grades ALTER COLUMN graded_by_id DROP NOT NULL"
        ))
    try:
        storage.ensure_bucket()
    except Exception as e:
        print(f"Warning: could not init RustFS bucket: {e}")
    try:
        await start_producer()
        await start_graded_consumer()
    except Exception as e:
        print(f"Warning: could not connect to Kafka: {e}")
    yield
    await stop_graded_consumer()
    await stop_producer()


app = FastAPI(title="Study Portal API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(schools.router)
app.include_router(groups.router)
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(submissions.router)
app.include_router(grades.router)
app.include_router(attendance.router)
app.include_router(analytics.router)
app.include_router(users.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
