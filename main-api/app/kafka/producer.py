import json
from aiokafka import AIOKafkaProducer
from app.config import settings

_producer: AIOKafkaProducer | None = None


async def start() -> None:
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await _producer.start()


async def stop() -> None:
    if _producer:
        await _producer.stop()


async def publish(topic: str, event: dict) -> None:
    if _producer is None:
        raise RuntimeError("Kafka producer not started")
    await _producer.send_and_wait(topic, event)
