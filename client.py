"""Thin wrapper around the Anthropic API with retry and an offline mock mode."""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("CV2JSON_MODEL", "claude-sonnet-4-5")
MOCK = os.getenv("CV2JSON_MOCK", "0") == "1"
MOCK_DIR = Path(__file__).resolve().parent.parent / "data" / "mock"

RETRYABLE_STATUS = {429, 500, 502, 503, 529}


def _mock_key(system: str, user: str) -> str:
    return hashlib.sha1((system + "\n---\n" + user).encode("utf-8")).hexdigest()[:16]


def complete(system: str, user: str, *, temperature: float = 0.0, max_tokens: int = 4000,
             max_retries: int = 5) -> str:
    """Return the model's text for a system + user prompt.

    Retries on rate limit (429), overload (529) and 5xx with exponential backoff + jitter.
    In mock mode, replays a saved response keyed on the prompt hash (see data/mock/).
    """
    if MOCK:
        f = MOCK_DIR / f"{_mock_key(system, user)}.json"
        if not f.exists():
            raise FileNotFoundError(
                f"no mock response for this prompt ({f.name}). Run once with a real key and "
                f"CV2JSON_RECORD=1 to record it.")
        return json.loads(f.read_text(encoding="utf-8"))["text"]

    import anthropic

    client = anthropic.Anthropic()
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text")
            if os.getenv("CV2JSON_RECORD") == "1":
                MOCK_DIR.mkdir(parents=True, exist_ok=True)
                (MOCK_DIR / f"{_mock_key(system, user)}.json").write_text(
                    json.dumps({"model": MODEL, "text": text}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
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
