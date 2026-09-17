
import io
from PIL import Image
import pytesseract

from app.models.schemas import OCRResult

TYPED_TEXT_CONFIDENCE = 0.95


def extract_from_text(raw_text: str) -> OCRResult:
    cleaned = raw_text.strip()
    return OCRResult(raw_text=cleaned, confidence=TYPED_TEXT_CONFIDENCE)


def extract_from_image(image_bytes: bytes) -> OCRResult:
    image = Image.open(io.BytesIO(image_bytes))

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    confidences = []
    for word, conf in zip(data["text"], data["conf"]):
        word = word.strip()
        if not word:
            continue
        conf = float(conf)
        if conf < 0:  
            continue
        words.append(word)
        confidences.append(conf)

    raw_text = " ".join(words)
    avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

    return OCRResult(raw_text=raw_text, confidence=round(avg_confidence, 2))