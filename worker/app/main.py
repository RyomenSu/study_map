import asyncio
import logging
import threading

import uvicorn
from fastapi import FastAPI
from app.routers import health
from app.kafka import consumer

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="StudyMap Worker", version="0.1.0")
app.include_router(health.router)


def _run_health_server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")


async def main() -> None:
    threading.Thread(target=_run_health_server, daemon=True).start()
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())
