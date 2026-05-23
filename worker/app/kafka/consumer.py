import json
import logging
from aiokafka import AIOKafkaConsumer
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.kafka.topics import ALL
from app.handlers import users, attendance, homework

logger = logging.getLogger(__name__)

HANDLERS = {
    "user.create": users.handle_user_create,
    "attendance.mark": attendance.handle_attendance_mark,
    "homework.submit": homework.handle_homework_submit,
}


async def run() -> None:
    consumer = AIOKafkaConsumer(
        *ALL,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="studymap-worker",
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    logger.info("Worker consumer started, subscribed to %s", ALL)

    try:
        async for msg in consumer:
            event = msg.value
            action = event.get("action")
            handler = HANDLERS.get(action)

            if handler is None:
                logger.warning("No handler for action=%s, skipping", action)
                await consumer.commit()
                continue

            try:
                async with AsyncSessionLocal() as db:
                    await handler(event["payload"], db)
                await consumer.commit()
                logger.info("Processed event_id=%s action=%s", event.get("event_id"), action)
            except Exception:
                logger.exception(
                    "Failed to process event_id=%s action=%s", event.get("event_id"), action
                )
    finally:
        await consumer.stop()
