import os
import re
import json
import urllib.request
import urllib.error
import cv2
import easyocr
import numpy as np
import torch
from PIL import Image
from spellchecker import SpellChecker

_reader = None
_spellchecker = None


def _get_ocr_languages() -> list[str]:
    raw = os.getenv("OCR_LANGS", "en")
    langs = [lang.strip() for lang in raw.split(",") if lang.strip()]
    return langs or ["en"]


def _is_english_postprocess_enabled() -> bool:
    return os.getenv("OCR_POSTPROCESS_EN", "true").strip().lower() in {"1", "true", "yes", "on"}


def _is_demo_llm_cleanup_enabled() -> bool:
    return os.getenv("OCR_DEMO_LLM_CLEANUP", "false").strip().lower() in {"1", "true", "yes", "on"}


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")


def get_model():
    global _reader
    if _reader is None:
        print("Loading EasyOCR model...")
        _reader = easyocr.Reader(
            _get_ocr_languages(),
            gpu=torch.cuda.is_available()
        )
        print("EasyOCR model loaded.")
    return _reader


def _get_spellchecker() -> SpellChecker:
    global _spellchecker
    if _spellchecker is None:
        _spellchecker = SpellChecker(language="en", distance=1)
    return _spellchecker


def _preprocess_for_ocr(image_np: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        25,
        9
    )
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)


def _resize_for_memory(image_np: np.ndarray, max_side: int = 1600) -> np.ndarray:
    height, width = image_np.shape[:2]
    side = max(height, width)
    if side <= max_side:
        return image_np
    scale = max_side / float(side)
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image_np, new_size, interpolation=cv2.INTER_AREA)


def _postprocess_english_text(text: str) -> str:
    if not text.strip():
        return text
    if "en" not in _get_ocr_languages():
        return text
    if not _is_english_postprocess_enabled():
        return text

    spell = _get_spellchecker()

    def _normalize_noisy_token(token: str) -> str:
        token_lower = token.lower()
        if not any(ch.isdigit() for ch in token_lower):
            return token

        # Common OCR substitutions in handwritten text.
        char_map = {
            "0": "o",
            "1": "l",
            "3": "e",
            "4": "a",
            "5": "s",
            "6": "g",
            "7": "t",
            "8": "b",
            "9": "g",
        }
        normalized = "".join(char_map.get(ch, ch) for ch in token_lower)
        if token.istitle():
            return normalized.title()
        if token.isupper():
            return normalized.upper()
        return normalized

    def _replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        token = _normalize_noisy_token(token)
        # Avoid over-correcting short words and all-caps tokens.
        if len(token) < 4 or token.isupper():
            return token

        corrected = spell.correction(token.lower())
        if not corrected or corrected == token.lower():
            return token

        # Keep original capitalization style.
        if token.istitle():
            return corrected.title()
        if token.isupper():
            return corrected.upper()
        return corrected

    corrected = re.sub(r"[A-Za-z0-9]+", _replace_token, text)
    corrected = re.sub(r"\s+([.,!?;:])", r"\1", corrected)
    corrected = re.sub(r"\s{2,}", " ", corrected)
    return corrected.strip()


def _cleanup_with_local_llm(text: str) -> str:
    if not _is_demo_llm_cleanup_enabled():
        print("LLM cleanup disabled by OCR_DEMO_LLM_CLEANUP=false")
        return text
    if not text.strip():
        return text

    prompt = (
        "You are cleaning noisy OCR output from handwritten English notes.\n"
        "Task:\n"
        "1) Return ONE cleaned English sentence/paragraph.\n"
        "2) Fix obvious OCR mistakes and punctuation.\n"
        "3) Keep original meaning as much as possible.\n"
        "4) Do not add explanations, only the cleaned text.\n\n"
        f"OCR text:\n{text}"
    )

    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    req = urllib.request.Request(
        _ollama_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        print(f"Sending OCR text to LLM cleanup: model={_ollama_model()}")
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            cleaned = str(parsed.get("response", "")).strip()
            if cleaned:
                print("LLM cleanup succeeded and returned text.")
            else:
                print("LLM cleanup returned empty response, using OCR text.")
            return cleaned or text
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        print("LLM cleanup unavailable/failed, fallback to OCR text.")
        return text


def _extract_with_easyocr(preprocessed_np: np.ndarray) -> str:
    reader = get_model()
    lines = reader.readtext(
        preprocessed_np,
        detail=0,
        paragraph=True,
        decoder="greedy",
        batch_size=1
    )
    return "\n".join(line.strip() for line in lines if line and line.strip()).strip()


def extract_text_from_image(image: Image.Image) -> str:
    """
    Прогоняет одно изображение через EasyOCR.
    """
    image_rgb = image.convert("RGB")
    image_np = _resize_for_memory(np.array(image_rgb))
    preprocessed_np = _preprocess_for_ocr(image_np)
    raw_text = _extract_with_easyocr(preprocessed_np)
    corrected_text = _postprocess_english_text(raw_text)
    return _cleanup_with_local_llm(corrected_text)


def extract_text_from_images(images: list[Image.Image]) -> str:
    """
    Прогоняет список страниц, собирает текст.
    """
    results = []
    for i, image in enumerate(images):
        print(f"Processing page {i + 1}/{len(images)}...")
        text = extract_text_from_image(image)
        if text:
            results.append(text)
    return "\n\n".join(results)