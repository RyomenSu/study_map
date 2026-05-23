import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import select

from app.config import settings

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None
_consumer_task: asyncio.Task | None = None


# ── Producer ──────────────────────────────────────────────────────────────────

async def start_producer() -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await _producer.start()
    logger.info("Kafka producer started")


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish_submission(
    submission_id: str,
    student_id: str,
    assignment_id: str,
    file_path: str,
) -> None:
    if _producer is None:
        logger.warning("Kafka producer not running — skipping publish")
        return
    # OCR service expects s3_path as "bucket/key"
    s3_path = f"{settings.RUSTFS_BUCKET}/{file_path}"
    payload = {
        "submission_id": submission_id,
        "student_id": student_id,
        "assignment_id": assignment_id,
        "s3_path": s3_path,
    }
    await _producer.send(settings.KAFKA_SUBMISSION_TOPIC, payload)
    logger.info("Published to %s: submission=%s", settings.KAFKA_SUBMISSION_TOPIC, submission_id)


# ── Consumer (homework.graded) ────────────────────────────────────────────────

async def _graded_consumer_loop() -> None:
    from app.database import AsyncSessionLocal
    from app.models import Grade, Submission, SubmissionStatus

    consumer = AIOKafkaConsumer(
        settings.KAFKA_GRADED_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="study-portal-backend",
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Kafka graded consumer started on topic '%s'", settings.KAFKA_GRADED_TOPIC)

    try:
        async for msg in consumer:
            data = msg.value
            logger.info("Received graded event: %s", data)
            try:
                await _apply_grade(data)
            except Exception as e:
                logger.error("Failed to apply grade from event %s: %s", data, e)
    finally:
        await consumer.stop()


async def _apply_grade(data: dict) -> None:
    import uuid as _uuid
    from app.database import AsyncSessionLocal
    from app.models import Grade, Submission, SubmissionStatus

    async with AsyncSessionLocal() as db:
        submission = None

        if "submission_id" in data:
            try:
                sid = _uuid.UUID(str(data["submission_id"]))
            except ValueError:
                logger.error("Invalid submission_id UUID: %s", data["submission_id"])
                return
            result = await db.execute(
                select(Submission).where(Submission.id == sid)
            )
            submission = result.scalar_one_or_none()

        if submission is None and "student_id" in data and "assignment_id" in data:
            try:
                stud = _uuid.UUID(str(data["student_id"]))
                asgn = _uuid.UUID(str(data["assignment_id"]))
            except ValueError:
                logger.error("Invalid student_id/assignment_id UUID in event: %s", data)
                return
            result = await db.execute(
                select(Submission).where(
                    Submission.student_id == stud,
                    Submission.assignment_id == asgn,
                ).order_by(Submission.submitted_at.desc())
            )
            submission = result.scalar_one_or_none()

        if submission is None:
            logger.warning("Could not find submission for graded event: %s", data)
            return

        score = float(data.get("score", 0))
        max_score = float(data.get("max_score", 100.0))
        feedback = data.get("feedback")

        existing = await db.execute(
            select(Grade).where(Grade.submission_id == submission.id)
        )
        grade = existing.scalar_one_or_none()

        if grade:
            grade.score = score
            grade.max_score = max_score
            grade.feedback = feedback
            grade.is_ai_graded = True
        else:
            grade = Grade(
                submission_id=submission.id,
                score=score,
                max_score=max_score,
                feedback=feedback,
                graded_by_id=None,
                is_ai_graded=True,
            )
            db.add(grade)

        submission.status = SubmissionStatus.graded
        await db.commit()
        logger.info("Auto-graded submission %s → score %s / %s", submission.id, score, max_score)


async def start_graded_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_graded_consumer_loop())


async def stop_graded_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
