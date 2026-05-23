import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from pdf_utils import has_native_text, extract_native_text, pdf_to_images
from model import extract_text_from_images
from kafka_consumer import start_consumer

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем Kafka консьюмер в фоне при старте
    task = asyncio.create_task(start_consumer())
    print("Kafka consumer started in background")
    yield
    # При остановке отменяем
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Kafka consumer stopped")


app = FastAPI(
    title="OCR Service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ocr"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    """
    HTTP эндпоинт для прямого вызова (например от grading сервиса).
    Принимает PDF, возвращает извлечённый текст.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:
        pdf_bytes = await file.read()

        if has_native_text(pdf_bytes):
            print("Native text detected, skipping TrOCR")
            extracted_text = extract_native_text(pdf_bytes)
        else:
            print("Handwritten/scanned PDF, running TrOCR")
            images = pdf_to_images(pdf_bytes, dpi=150)
            extracted_text = await asyncio.get_event_loop().run_in_executor(
                None,
                extract_text_from_images,
                images
            )

        return JSONResponse(content={"extracted_text": extracted_text})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )