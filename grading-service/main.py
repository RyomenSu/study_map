import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from grader import grade_submission
from models import GradingRequest, GradingResult
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "homework.extracted")
OUTPUT_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "homework.graded")


async def _run_consumer_once():
    print(f"[KAFKA] Connecting to brokers={KAFKA_BOOTSTRAP} topic={INPUT_TOPIC}")
    consumer = AIOKafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="grading-service-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)

    await consumer.start()
    print("[KAFKA] Consumer started OK")
    await producer.start()
    print("[KAFKA] Producer started OK")

    print(f"[KAFKA] Waiting for messages on topic: {INPUT_TOPIC}")
    try:
        async for msg in consumer:
            print(f"[KAFKA] Message received: partition={msg.partition} offset={msg.offset} key={msg.key}")
            data = msg.value
            print(f"[KAFKA] Message payload: {data}")

            submission_id = data.get("submission_id")
            student_id = data.get("student_id")
            assignment_id = data.get("assignment_id")
            extracted_text = data.get("extracted_text", "")
            status = data.get("status")

            if status != "success":
                print(f"[KAFKA] Skipping: status={status}")
                continue
            if not extracted_text.strip():
                print(f"[KAFKA] Skipping: extracted_text is empty (submission={submission_id})")
                continue

            print(f"[GRADER] Sending to Gemini: submission={submission_id} text_len={len(extracted_text)}")
            try:
                result = await grade_submission(
                    extracted_text=extracted_text,
                    subject=data.get("subject", "общий предмет"),
                )
                print(f"[GRADER] Gemini response OK: score={result.total_score}")

                payload = {
                    "submission_id": submission_id,
                    "student_id": student_id,
                    "assignment_id": assignment_id,
                    "score": result.total_score,
                    "max_score": 100,
                    "feedback": result.summary,
                }
                print(f"[KAFKA] Publishing grade to {OUTPUT_TOPIC}: {payload}")
                await producer.send_and_wait(OUTPUT_TOPIC, json.dumps(payload).encode("utf-8"))
                print(f"[KAFKA] Grade published OK for submission={submission_id}")
            except Exception as e:
                print(f"[GRADER] ERROR grading submission={submission_id}: {e}")
    finally:
        print("[KAFKA] Shutting down consumer and producer")
        await consumer.stop()
        await producer.stop()


async def _kafka_loop():
    retry_delay = 5
    while True:
        try:
            await _run_consumer_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[KAFKA] Consumer crashed: {e}. Restarting in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


def _task_error_handler(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        print(f"[KAFKA] Background task crashed: {task.exception()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] Launching Kafka consumer background task")
    task = asyncio.create_task(_kafka_loop())
    task.add_done_callback(_task_error_handler)
    print("[STARTUP] Kafka consumer task created")
    yield
    print("[SHUTDOWN] Cancelling Kafka consumer task")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("[SHUTDOWN] Kafka consumer stopped cleanly")


app = FastAPI(title="AI Grading Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/grade", response_model=GradingResult)
async def grade(request: Request):
    raw = await request.body()
    # Чистим невалидные control characters перед парсингом
    cleaned = raw.decode("utf-8").replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
    try:
        body_dict = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Невалидный JSON: {e}")

    body = GradingRequest(**body_dict)

    if not body.extracted_text.strip():
        raise HTTPException(status_code=422, detail="extracted_text пустой")
    if not body.subject.strip():
        raise HTTPException(status_code=422, detail="subject пустой")

    result = await grade_submission(
        extracted_text=body.extracted_text,
        subject=body.subject,
    )
    result.student_id = body.student_id
    result.assignment_id = body.assignment_id
    return result

@app.get("/health")
def health():
    return {"status": "ok"}