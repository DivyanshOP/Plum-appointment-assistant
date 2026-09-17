import io
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app
from app.services import entity_service, normalization_service, pipeline
from app.models.schemas import GuardrailResponse, NormalizationResult

client = TestClient(app)


def next_weekday(target_weekday: int, today: date = None) -> date:
    today = today or date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def render_text_image(text: str) -> bytes:
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28
        )
    except OSError:
        font = ImageFont.load_default(size=28)

    dummy = Image.new("RGB", (10, 10))
    width = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)[2] + 60
    img = Image.new("RGB", (width, 100), color="white")
    ImageDraw.Draw(img).text((30, 30), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

class TestEntityExtraction:
    def test_extracts_all_three_fields(self):
        result = entity_service.extract_entities("Book dentist next Friday at 3pm")
        assert result.entities.department == "dentist"
        assert result.entities.date_phrase == "next Friday"
        assert result.entities.time_phrase == "3pm"
        assert result.entities_confidence == 1.0

    def test_missing_department_returns_none(self):
        result = entity_service.extract_entities("Book appointment next Friday at 3pm")
        assert result.entities.department is None

    def test_missing_time_returns_none(self):
        result = entity_service.extract_entities("Book dentist next Friday")
        assert result.entities.time_phrase is None

    def test_bare_weekday_without_next(self):
        result = entity_service.extract_entities("Book dermatologist on Monday at 10am")
        assert result.entities.date_phrase == "Monday"

class TestNormalization:
    def test_next_weekday_resolves_to_future_date(self):
        from app.models.schemas import Entities
        entities = Entities(date_phrase="next friday", time_phrase="3pm", department="dentist")
        result = normalization_service.normalize(entities)
        assert isinstance(result, NormalizationResult)
        expected_date = next_weekday(4)  # Friday = 4
        assert result.normalized.date == expected_date.isoformat()
        assert result.normalized.time == "15:00"
        assert result.normalized.tz == "Asia/Kolkata"

    def test_bare_weekday_resolves_to_future_not_today(self):
        from app.models.schemas import Entities
        entities = Entities(date_phrase="monday", time_phrase="10am", department="dermatologist")
        result = normalization_service.normalize(entities)
        assert isinstance(result, NormalizationResult)
        expected_date = next_weekday(0)  # Monday = 0
        assert result.normalized.date == expected_date.isoformat()

    def test_missing_date_phrase_triggers_guardrail(self):
        from app.models.schemas import Entities
        entities = Entities(date_phrase=None, time_phrase="3pm", department="dentist")
        result = normalization_service.normalize(entities)
        assert isinstance(result, GuardrailResponse)
        assert result.status == "needs_clarification"

    def test_unparseable_time_triggers_guardrail(self):
        from app.models.schemas import Entities
        entities = Entities(date_phrase="next friday", time_phrase="blorp", department="dentist")
        result = normalization_service.normalize(entities)
        assert isinstance(result, GuardrailResponse)

class TestPipeline:
    def test_full_success_path(self):
        result = pipeline.run_pipeline("Book cardiologist next Monday at 10am")
        assert result.status == "ok"
        assert result.appointment.department == "Cardiology"
        assert result.appointment.time == "10:00"

    def test_unknown_department_triggers_guardrail(self):
        result = pipeline.run_pipeline("Book appointment next Friday at 3pm")
        assert isinstance(result, GuardrailResponse)

    def test_absolute_date_phrasing(self):
        result = pipeline.run_pipeline("Schedule pediatrician on 30th September at 11 am")
        assert result.status == "ok"
        assert result.appointment.department == "Pediatrics"
        assert result.appointment.time == "11:00"


# ---------- API ----------

class TestAPI:
    def test_text_endpoint_success(self):
        response = client.post(
            "/api/appointment/text",
            json={"raw_text": "Book cardiologist next Monday at 10am"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["appointment"]["department"] == "Cardiology"

    def test_text_endpoint_guardrail(self):
        response = client.post(
            "/api/appointment/text",
            json={"raw_text": "Book appointment next Friday at 3pm"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "needs_clarification"

    def test_image_endpoint_success(self):
        image_bytes = render_text_image("Book cardiologist next Monday at 10am")
        response = client.post(
            "/api/appointment/image",
            files={"file": ("note.png", image_bytes, "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["appointment"]["department"] == "Cardiology"

    def test_image_endpoint_rejects_non_image(self):
        response = client.post(
            "/api/appointment/image",
            files={"file": ("note.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 400

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}