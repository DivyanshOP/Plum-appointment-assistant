

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.services import ocr_service, pipeline
from app.models.schemas import GuardrailResponse

router = APIRouter(prefix="/api/appointment", tags=["appointment"])


class TextRequest(BaseModel):
    raw_text: str


@router.post("/text")
def parse_from_text(payload: TextRequest):
    ocr_result = ocr_service.extract_from_text(payload.raw_text)
    result = pipeline.run_pipeline(ocr_result.raw_text)
    return result


@router.post("/image")
async def parse_from_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    image_bytes = await file.read()
    ocr_result = ocr_service.extract_from_image(image_bytes)

    if not ocr_result.raw_text.strip():
        return GuardrailResponse(
            status="needs_clarification",
            message="Could not read any text from the image",
        )

    result = pipeline.run_pipeline(ocr_result.raw_text)
    return result