import fitz  # PyMuPDF
from PIL import Image
import io

def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> list[Image.Image]:
    """
    Конвертирует каждую страницу PDF в изображение.
    DPI 150 — баланс между качеством и скоростью.
    """
    images = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            images.append(image)
    return images


def has_native_text(pdf_bytes: bytes) -> bool:
    """
    Проверяет есть ли в PDF нативный текст (не скан).
    Если да — не нужен TrOCR, берём текст напрямую.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            if page.get_text().strip():
                return True
    return False


def extract_native_text(pdf_bytes: bytes) -> str:
    """
    Извлекает нативный текст из текстового PDF.
    """
    parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)