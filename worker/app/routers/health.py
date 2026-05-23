import time
from typing import Any

import boto3
import botocore.exceptions
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.config import settings

router = APIRouter(tags=["health"])


async def _check_postgres() -> dict[str, Any]:
    try:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _check_kafka() -> dict[str, Any]:
    consumer = AIOKafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="worker-healthcheck",
    )
    try:
        await consumer.start()
        return {"status": "ok"}
    except KafkaConnectionError as e:
        return {"status": "error", "detail": str(e)}
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass


def _check_s3() -> dict[str, Any]:
    try:
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        client.list_buckets()
        return {"status": "ok"}
    except botocore.exceptions.EndpointResolutionError as e:
        return {"status": "error", "detail": str(e)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/health")
async def health() -> dict[str, Any]:
    start = time.monotonic()

    postgres, kafka, s3 = (
        await _check_postgres(),
        await _check_kafka(),
        _check_s3(),
    )

    all_ok = all(c["status"] == "ok" for c in (postgres, kafka, s3))

    return {
        "status": "ok" if all_ok else "degraded",
        "uptime_ms": round((time.monotonic() - start) * 1000, 2),
        "checks": {
            "postgres": postgres,
            "kafka": kafka,
            "s3": s3,
        },
    }
