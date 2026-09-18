# AI-Powered Appointment Scheduler Assistant

Backend service (FastAPI) that parses natural language or document-based
appointment requests, typed text or photographed/scanned notes, into
structured scheduling data, via a 4-step pipeline: OCR, Entity
Extraction, Normalization, Final Appointment JSON, with guardrails
for ambiguous or incomplete input.
Live URL : http://13.48.29.48:8000
Built for the Plum SDE Intern Assignment, Problem Statement 1.

---

## Architecture

```
                 +-------------+
  text input --> | OCR Service | --> raw_text
  image input -->| (pytesseract)|
                 +-------------+
                        |
                        v
              +--------------------+
              | Entity Extraction  |  --> date_phrase, time_phrase,
              |   (regex-based)    |      department
              +--------------------+
                        |
                        v
              +--------------------+
              |   Normalization    |  --> ISO date, 24h time,
              |  (weekday math +   |      Asia/Kolkata
              |   dateparser)      |
              +--------------------+
                        |
                        v
              +--------------------+
              |  Final Appointment |  --> { department, date, time,
              |        JSON        |        tz, status: "ok" }
              +--------------------+

  At any stage, missing/ambiguous data short-circuits to:
  { "status": "needs_clarification", "message": "..." }
```

### Project structure

```
app/
├── main.py                       # FastAPI app entrypoint
├── api/
│   └── routes.py                 # /api/appointment/text, /api/appointment/image
├── services/
│   ├── ocr_service.py            # Step 1: typed text / pytesseract image OCR
│   ├── entity_service.py         # Step 2: regex-based entity extraction
│   ├── normalization_service.py  # Step 3: date/time normalization + guardrails
│   └── pipeline.py                # Orchestrates steps 2-4 + department guardrail
├── models/
│   └── schemas.py                # Pydantic models matching the spec's JSON shapes
tests/
└── test_pipeline.py              # Unit + API tests (pytest)
```

### Key design decisions

- **Regex over NLP models for entity extraction.** Keeps the service
  fast and dependency-light. The trade-off: department recognition is
  limited to a known keyword list (`entity_service.KNOWN_DEPARTMENTS`),
  and unfamiliar phrasing needs regex updates rather than generalizing
  automatically.
- **Custom weekday resolution instead of relying on `dateparser`'s
  built-in "next `<weekday>`" handling.** `dateparser` 1.2.0 has a
  known quirk where phrases like `"next friday"` (and combined phrases
  like `"next friday 3pm"`, with no separator) return `None`, even
  though bare weekdays and `"<weekday> at <time>"` parse fine. We
  resolve `today / tomorrow / next|this|coming <weekday>` ourselves via
  plain date arithmetic (always resolves to a future date, never
  today itself), and only fall back to `dateparser` for absolute-style
  phrases (e.g. `"26th September"`) and for time phrases, which it
  handles well.
- **Two guardrail checkpoints**, both returning the same
  `{"status": "needs_clarification", "message": "..."}` shape from the
  spec: missing/unrecognized department (checked in `pipeline.py`), and
  missing or unparseable date/time (checked in `normalization_service.py`).
- **OCR confidence is computed from Tesseract's real per-word
  confidence scores** (via `pytesseract.image_to_data`), not a
  hardcoded number, so it reflects how noisy the actual image was.

### Known limitations

- **Tesseract handles printed/typed text well but not cursive
  handwriting.** In testing, clean typed/rendered text (e.g. a
  screenshot of a note or email) OCRs near-perfectly, while genuine
  cursive handwriting photos were garbled beyond recognition. This is
  a fundamental limitation of Tesseract's model, not a bug in this
  pipeline. Real handwriting recognition would need a different
  engine (e.g. Google Cloud Vision's handwriting API, Azure's
  handwriting recognition, or a model like TrOCR).
- **Department recognition is keyword-based**, not fuzzy. Synonyms not
  in `KNOWN_DEPARTMENTS` (e.g. "orthodontist") won't be recognized and
  will correctly (if bluntly) trigger the ambiguity guardrail.
- **Confidence scores are heuristic**, not statistically calibrated.
  OCR confidence comes from real Tesseract data, but entity/normalization
  confidence are simple rule-of-thumb values.

---

## Setup

### Prerequisites

- Python 3.11 or 3.12 (not 3.14; as of this writing, `pydantic-core`
  and `Pillow` don't yet have prebuilt wheels for 3.14, which forces a
  source build that will likely fail unless you have a Rust toolchain
  and jpeg dev headers installed).
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed
  and on your `PATH`:
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
  - Fedora: `sudo dnf install tesseract`
  - Windows: [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki)

Verify with:
```bash
tesseract --version
```

### Install

```bash
git clone https://github.com/DivyanshOP/Plum-appointment-assistant.git
cd plum-appointment-assistant
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload
```

Server starts at `http://127.0.0.1:8000`. Interactive API docs
(useful for testing image uploads without curl) at
`http://127.0.0.1:8000/docs`.

### Run tests

```bash
pytest tests/ -v
```
---

## Demo walkthrough (terminal + Swagger UI)

Quick copy-paste commands and UI steps for demoing/recording the endpoints
end to end. Swap the host for `127.0.0.1:8000` if running locally instead
of against the live deployment.

### Terminal (curl)

**1. Text endpoint, success case**
```bash
curl -X POST http://13.48.29.48:8000/api/appointment/text -H "Content-Type: application/json" -d '{"raw_text": "Book dentist next Friday at 3pm"}'
```

**2. Text endpoint, guardrail (unrecognized department)**
```bash
curl -X POST http://13.48.29.48:8000/api/appointment/text -H "Content-Type: application/json" -d '{"raw_text": "Book appointment next Friday at 3pm"}'
```

**3. Text endpoint, guardrail (missing time)**
```bash
curl -X POST http://13.48.29.48:8000/api/appointment/text -H "Content-Type: application/json" -d '{"raw_text": "Book dentist next Friday"}'
```

**4. Image endpoint, success case** (run from wherever the sample image is saved)
```bash
curl -X POST http://13.48.29.48:8000/api/appointment/image -F "file=@sample_clean_note.png"
```

**5. Health check**
```bash
curl http://13.48.29.48:8000/health
```

**6. Run tests** (locally, in the project folder with the venv activated)
```bash
pytest tests/ -v
```

### Swagger UI (`/docs`)

**Text endpoint:**
1. Open `http://13.48.29.48:8000/docs`
2. Expand `POST /api/appointment/text`
3. Click **Try it out**
4. Replace the request body with:
```json
   { "raw_text": "Book dentist next Friday at 3pm" }
```
5. Click **Execute** and check the response body below

**Image endpoint:**
1. Expand `POST /api/appointment/image`
2. Click **Try it out**
3. Click **Choose File** under the `file` field and select a sample image
4. Click **Execute** and check the response body below
### Expose publicly (for demo/submission)

```bash
ngrok http 8000
```

---

## API Usage

### `POST /api/appointment/text`

Accepts typed natural-language appointment requests.

**Request:**
```json
{ "raw_text": "Book dentist next Friday at 3pm" }
```

**curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/appointment/text \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "Book dentist next Friday at 3pm"}'
```

**Success response (200):**
```json
{
  "appointment": {
    "department": "Dentistry",
    "date": "2026-09-25",
    "time": "15:00",
    "tz": "Asia/Kolkata"
  },
  "status": "ok"
}
```

**Guardrail response (200), ambiguous input, e.g. missing department:**
```json
{ "status": "needs_clarification", "message": "Ambiguous date/time or department" }
```

### `POST /api/appointment/image`

Accepts a photo/scan of a note or email (multipart file upload).

**curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/appointment/image \
  -F "file=@note.png"
```

**Postman:** Method `POST`, URL `http://127.0.0.1:8000/api/appointment/image`,
Body -> `form-data`, key `file` (type: File), value: your image.

Same response shapes as `/text` above. If the uploaded file isn't an
image, returns `400`. If Tesseract can't read any text from the image,
returns the `needs_clarification` guardrail with message
`"Could not read any text from the image"`.

### `GET /health`

Simple health check.
```bash
curl http://127.0.0.1:8000/health
# {"status": "ok"}
```

---

## Example inputs and expected behavior

| Input | Expected |
|---|---|
| `"Book dentist next Friday at 3pm"` | Success: Dentistry appointment, next Friday, 15:00 |
| `"Book dermatologist on Monday at 10am"` | Success: Dermatology, next upcoming Monday, 10:00 |
| `"Schedule pediatrician on 30th September at 11am"` | Success: Pediatrics, 2026-09-30, 11:00 |
| `"Book appointment next Friday at 3pm"` | Guardrail: needs_clarification, "appointment" isn't a recognized department |
| `"Book dentist next Friday"` | Guardrail: needs_clarification, no time given |
| Clean screenshot/photo of typed text | Success: same as text input, via OCR |
| Photo of cursive handwriting | Likely guardrail or garbled text; see Known Limitations |
