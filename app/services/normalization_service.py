
import re
from datetime import timedelta, date as date_cls, datetime
from typing import Optional, Union

import dateparser
import pytz

from app.models.schemas import Entities, NormalizedDateTime, NormalizationResult, GuardrailResponse

TARGET_TZ = "Asia/Kolkata"

WEEKDAY_PREFIXES = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}

RELATIVE_PREFIX_RE = re.compile(r"^(next|this|coming)\s+(\w+)$", re.IGNORECASE)


def _today_in_target_tz() -> date_cls:
    return datetime.now(pytz.timezone(TARGET_TZ)).date()


def _resolve_weekday(word: str, today: date_cls) -> Optional[date_cls]:
    word = word.lower()
    target_wd = None
    for prefix, wd in WEEKDAY_PREFIXES.items():
        if word.startswith(prefix):
            target_wd = wd
            break
    if target_wd is None:
        return None

    days_ahead = (target_wd - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # always the *next* occurrence, not today
    return today + timedelta(days=days_ahead)


def _resolve_date(date_phrase: str) -> Optional[date_cls]:
    phrase = date_phrase.strip().lower()
    today = _today_in_target_tz()

    if phrase == "today":
        return today
    if phrase == "tomorrow":
        return today + timedelta(days=1)
    if phrase == "day after tomorrow":
        return today + timedelta(days=2)

    # "next friday" / "this friday" / "coming friday"
    match = RELATIVE_PREFIX_RE.match(phrase)
    weekday_word = match.group(2) if match else phrase
    resolved = _resolve_weekday(weekday_word, today)
    if resolved:
        return resolved

    parsed = dateparser.parse(
        date_phrase,
        settings={
            "TIMEZONE": TARGET_TZ,
            "TO_TIMEZONE": TARGET_TZ,
            "PREFER_DATES_FROM": "future",
        },
    )
    return parsed.date() if parsed else None


def _resolve_time(time_phrase: str):
    parsed = dateparser.parse(time_phrase)
    return parsed.time() if parsed else None


def normalize(entities: Entities) -> Union[NormalizationResult, GuardrailResponse]:
    if not entities.date_phrase or not entities.time_phrase:
        return GuardrailResponse(
            status="needs_clarification",
            message="Ambiguous date/time or department",
        )

    resolved_date = _resolve_date(entities.date_phrase)
    resolved_time = _resolve_time(entities.time_phrase)

    if resolved_date is None or resolved_time is None:
        return GuardrailResponse(
            status="needs_clarification",
            message="Ambiguous date/time or department",
        )

    normalized = NormalizedDateTime(
        date=resolved_date.isoformat(),
        time=resolved_time.strftime("%H:%M"),
        tz=TARGET_TZ,
    )

    normalization_confidence = 0.90

    return NormalizationResult(
        normalized=normalized,
        normalization_confidence=normalization_confidence,
    )