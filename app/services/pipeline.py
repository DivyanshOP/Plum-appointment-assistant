
from typing import Union

from app.models.schemas import AppointmentResult, Appointment, GuardrailResponse
from app.services import entity_service, normalization_service

DEPARTMENT_DISPLAY_NAMES = {
    "dentist": "Dentistry",
    "dentistry": "Dentistry",
    "doctor": "General Medicine",
    "physician": "General Medicine",
    "general physician": "General Medicine",
    "dermatologist": "Dermatology",
    "cardiologist": "Cardiology",
    "therapist": "Therapy",
    "physiotherapist": "Physiotherapy",
    "eye doctor": "Ophthalmology",
    "optometrist": "Ophthalmology",
    "pediatrician": "Pediatrics",
    "gynecologist": "Gynecology",
    "orthopedic": "Orthopedics",
    "clinic": "General Medicine",
}


def run_pipeline(raw_text: str) -> Union[AppointmentResult, GuardrailResponse]:
    entity_result = entity_service.extract_entities(raw_text)
    entities = entity_result.entities

    if not entities.department:
        return GuardrailResponse(
            status="needs_clarification",
            message="Ambiguous date/time or department",
        )

    normalization_result = normalization_service.normalize(entities)

    if isinstance(normalization_result, GuardrailResponse):
        return normalization_result

    department_display = DEPARTMENT_DISPLAY_NAMES.get(
        entities.department, entities.department.title()
    )

    appointment = Appointment(
        department=department_display,
        date=normalization_result.normalized.date,
        time=normalization_result.normalized.time,
        tz=normalization_result.normalized.tz,
    )

    return AppointmentResult(appointment=appointment, status="ok")