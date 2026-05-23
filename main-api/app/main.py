from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.kafka import producer
from app.routers import dev, health, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await producer.start()
    yield
    await producer.stop()


app = FastAPI(title="StudyMap API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(users.router)
app.include_router(dev.router)
