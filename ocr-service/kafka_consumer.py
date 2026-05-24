import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv

from s3_utils import download_pdf_from_s3
from pdf_utils import has_native_text, extract_native_text, pdf_to_images
from model import extract_text_from_images

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
CONSUME_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "homework.submitted")
PRODUCE_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "homework.extracted")


async def process_message(msg: dict, producer: AIOKafkaProducer):
    """
    Получает сообщение из Кафки:
    {
        "student_id": "123",
        "team_id": "456",
        "s3_path": "bucket/homeworks/file.pdf"
    }
    """
    student_id = msg.get("student_id")
    team_id = msg.get("team_id")
    s3_path = msg.get("s3_path")
    submission_id = msg.get("submission_id")
    assignment_id = msg.get("assignment_id")

    print(f"Processing homework: student={student_id} submission={submission_id} s3={s3_path}")

    try:
        pdf_bytes = download_pdf_from_s3(s3_path)

        if has_native_text(pdf_bytes):
            print("Native text found, skipping OCR model")
            extracted_text = extract_native_text(pdf_bytes)
        else:
            print("No native text, running OCR model")
            images = pdf_to_images(pdf_bytes, dpi=200)
            extracted_text = extract_text_from_images(images)

        result = {
            "submission_id": submission_id,
            "student_id": student_id,
            "assignment_id": assignment_id,
            "team_id": team_id,
            "s3_path": s3_path,
            "extracted_text": extracted_text,
            "status": "success"
        }

    except Exception as e:
        print(f"Error processing {s3_path}: {e}")
        result = {
            "submission_id": submission_id,
            "student_id": student_id,
            "assignment_id": assignment_id,
            "team_id": team_id,
            "s3_path": s3_path,
            "extracted_text": "",
            "status": "error",
            "error": str(e)
        }

    await producer.send_and_wait(
        PRODUCE_TOPIC,
        json.dumps(result).encode("utf-8")
    )
    print(f"Result sent to {PRODUCE_TOPIC}")


async def start_consumer():
    consumer = AIOKafkaConsumer(
        CONSUME_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="ocr-service-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest"
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP
    )

    await consumer.start()
    await producer.start()
    print(f"Listening on topic: {CONSUME_TOPIC}")

    try:
        async for msg in consumer:
            await process_message(msg.value, producer)
    finally:
        await consumer.stop()
        await producer.stop()