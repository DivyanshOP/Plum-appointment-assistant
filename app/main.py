from fastapi import FastAPI

from app.api.routes import router as appointment_router

app = FastAPI(
    title="AI-Powered Appointment Scheduler Assistant",
    description=(
        "Parses natural language or document-based appointment requests "
        "into structured scheduling data, via OCR -> entity extraction -> "
        "normalization -> final JSON, with guardrails for ambiguity."
    ),
    version="1.0.0",
)

app.include_router(appointment_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
