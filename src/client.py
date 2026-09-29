"""Thin wrapper around the Anthropic API with retry and an offline mock mode."""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("CV2JSON_MODEL", "claude-sonnet-4-5")
MOCK = os.getenv("CV2JSON_MOCK", "0") == "1"
MOCK_DIR = Path(__file__).resolve().parent.parent / "data" / "mock"

RETRYABLE_STATUS = {429, 500, 502, 503, 529}
# Models that reject sampling parameters (temperature 0 would be a 400): Opus 4.7+, Sonnet 5, Fable, Mythos.
NO_SAMPLING = ("claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5", "claude-fable", "claude-mythos")


def _mock_key(system: str, user: str) -> str:
    return hashlib.sha1((system + "\n---\n" + user).encode("utf-8")).hexdigest()[:16]


def _load_mock(system: str, user: str) -> str:
    f = MOCK_DIR / f"{_mock_key(system, user)}.json"
    if not f.exists():
        raise FileNotFoundError(
            f"no mock response for this prompt ({f.name}). Run once with a real key and "
            f"CV2JSON_RECORD=1 to record it.")
    return json.loads(f.read_text(encoding="utf-8"))["text"]


def _sampling(model: str, temperature: float | None) -> dict:
    """SDK 1.x dropped `temperature` from its signatures; the API still honours it on older models."""
    if temperature is None or model.startswith(NO_SAMPLING):
        return {}
    return {"extra_body": {"temperature": temperature}}


def _maybe_record(system: str, user: str, model: str, text: str) -> None:
    if os.getenv("CV2JSON_RECORD") == "1":
        MOCK_DIR.mkdir(parents=True, exist_ok=True)
        (MOCK_DIR / f"{_mock_key(system, user)}.json").write_text(
            json.dumps({"model": model, "text": text}, ensure_ascii=False, indent=2),
            encoding="utf-8")


def complete(system: str, user: str, *, temperature: float = 0.0, max_tokens: int = 4000,
             max_retries: int = 5, model: str | None = None) -> str:
    """Return the model's text for a system + user prompt.

    Retries on rate limit (429), overload (529) and 5xx with exponential backoff + jitter.
    In mock mode, replays a saved response keyed on the prompt hash (see data/mock/).
    `model` overrides CV2JSON_MODEL for this call (the analyst can use its own model).
    """
    model = model or MODEL
    if MOCK:
        return _load_mock(system, user)

    import anthropic

    client = anthropic.Anthropic()
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **_sampling(model, temperature),
            )
            text = "".join(b.text for b in resp.content if b.type == "text")
            _maybe_record(system, user, model, text)
            return text
        except anthropic.APIStatusError as e:
            if e.status_code not in RETRYABLE_STATUS or attempt == max_retries:
                raise
            sleep = delay + random.uniform(0, 0.5)
            print(f"[client] {e.status_code} on attempt {attempt}, retrying in {sleep:.1f}s")
            time.sleep(sleep)
            delay = min(delay * 2, 30)
        except anthropic.APIConnectionError:
            if attempt == max_retries:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise RuntimeError("unreachable")


def stream(system: str, user: str, *, temperature: float = 0.0, max_tokens: int = 4000,
           max_retries: int = 5, model: str | None = None) -> Iterator[str]:
    """Like complete(), but yields the text as the model writes it.

    Retries only before the first chunk arrives, so a caller never receives text twice;
    a failure mid-answer is raised to the caller. Mock mode replays the saved text in chunks.
    """
    model = model or MODEL
    if MOCK:
        text = _load_mock(system, user)
        for i in range(0, len(text), 80):
            yield text[i:i + 80]
        return

    import anthropic

    client = anthropic.Anthropic()
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        parts: list[str] = []
        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **_sampling(model, temperature),
            ) as s:
                for chunk in s.text_stream:
                    parts.append(chunk)
                    yield chunk
                if s.get_final_message().stop_reason == "max_tokens":  # say so instead of ending mid-sentence
                    note = f"\n\n> **Note:** the answer was cut off at the {max_tokens}-token limit."
                    parts.append(note)
                    yield note
            _maybe_record(system, user, model, "".join(parts))
            return
        except anthropic.APIStatusError as e:
            if parts or e.status_code not in RETRYABLE_STATUS or attempt == max_retries:
                raise
            sleep = delay + random.uniform(0, 0.5)
            print(f"[client] {e.status_code} on attempt {attempt}, retrying in {sleep:.1f}s")
            time.sleep(sleep)
            delay = min(delay * 2, 30)
        except anthropic.APIConnectionError:
            if parts or attempt == max_retries:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 30)
