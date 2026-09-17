import re
from app.models.schemas import Entities, EntityExtractionResult

KNOWN_DEPARTMENTS = [
    "dentist", "dentistry", "doctor", "physician", "dermatologist",
    "cardiologist", "therapist", "physiotherapist", "eye doctor",
    "optometrist", "pediatrician", "gynecologist", "orthopedic",
    "general physician", "clinic",
]

TIME_PATTERN = re.compile(
    r"\b(\d{1,2}(:\d{2})?\s?(am|pm)|noon|midnight|\d{1,2}:\d{2})\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|day after tomorrow|"
    r"(next|this|coming)\s+(mon|tue|wed|thu|fri|sat|sun)\w*|"
    r"(mon|tue|wed|thu|fri|sat|sun)\w*|"
    r"\d{1,2}(st|nd|rd|th)?\s+\w+|"         
    r"\d{1,2}/\d{1,2}(/\d{2,4})?)\b",       
    re.IGNORECASE,
)


def extract_entities(raw_text: str) -> EntityExtractionResult:
    text = raw_text.lower()

    department = next((d for d in KNOWN_DEPARTMENTS if d in text), None)

    time_match = TIME_PATTERN.search(raw_text)
    time_phrase = time_match.group(0) if time_match else None

    date_match = DATE_PATTERN.search(raw_text)
    date_phrase = date_match.group(0) if date_match else None

    entities = Entities(
        date_phrase=date_phrase,
        time_phrase=time_phrase,
        department=department,
    )

    found_count = sum(x is not None for x in (date_phrase, time_phrase, department))
    entities_confidence = round(0.5 + 0.5 * (found_count / 3), 2)

    return EntityExtractionResult(entities=entities, entities_confidence=entities_confidence)