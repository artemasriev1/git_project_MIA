"""Output schema. If the model's JSON does not validate here, the extraction is a failure."""
from __future__ import annotations

import json
import re
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class Experience(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)

    @field_validator("start", "end")
    @classmethod
    def _date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "present":
            return v
        if not re.fullmatch(r"\d{4}(-\d{2})?", v):
            raise ValueError(f"date must be YYYY, YYYY-MM or 'present', got {v!r}")
        return v


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[int] = None


class Language(BaseModel):
    language: str
    level: Optional[str] = None


class CV(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    years_of_experience: Optional[int] = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_model_output(text: str) -> CV:
    """Extract the first JSON object from raw model text and validate it.

    Tolerates markdown fences and leading prose (common in chain-of-thought outputs);
    everything else raises so the failure is visible instead of silently wrong.
    """
    m = _FENCE.search(text)
    candidate = m.group(1) if m else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    data = json.loads(candidate[start : end + 1])
    try:
        return CV.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"schema validation failed: {e}") from e
