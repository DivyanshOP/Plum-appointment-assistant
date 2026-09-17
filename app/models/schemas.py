from typing import Optional
from pydantic import BaseModel, Field




class OCRResult(BaseModel):
    raw_text: str
    confidence: float = Field(..., ge=0.0, le=1.0)

class Entities(BaseModel):
    date_phrase: Optional[str] = None
    time_phrase: Optional[str] = None
    department: Optional[str] = None


class EntityExtractionResult(BaseModel):
    entities: Entities
    entities_confidence: float = Field(..., ge=0.0, le=1.0)



class NormalizedDateTime(BaseModel):
    date: str   
    time: str   
    tz: str = "Asia/Kolkata"


class NormalizationResult(BaseModel):
    normalized: NormalizedDateTime
    normalization_confidence: float = Field(..., ge=0.0, le=1.0)


class GuardrailResponse(BaseModel):
    status: str = "needs_clarification"
    message: str



class Appointment(BaseModel):
    department: str
    date: str
    time: str
    tz: str = "Asia/Kolkata"


class AppointmentResult(BaseModel):
    appointment: Appointment
    status: str = "ok"