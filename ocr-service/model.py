import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

_processor = None
_model = None

def get_model():
    global _processor, _model
    if _model is None:
        print("Loading TrOCR model...")
        _processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        _model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten"
        )
        _model.eval()
        print("TrOCR model loaded.")
    return _processor, _model


def extract_text_from_image(image: Image.Image) -> str:
    """
    Прогоняет одно изображение через TrOCR.
    """
    processor, model = get_model()

    pixel_values = processor(
        image,
        return_tensors="pt"
    ).pixel_values

    with torch.no_grad():
        generated_ids = model.generate(
            pixel_values,
            max_new_tokens=512
        )

    text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return text.strip()


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