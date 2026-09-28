"""Albert Convert: web front end for the CV-to-JSON pipeline.

Run: python -m web.app   then open http://127.0.0.1:5000
Every conversion goes through src.extract.extract_one, so the website and the CLI
share the same prompts, API client, retry logic and schema validation.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from src.client import MOCK, MODEL
from src.extract import extract_one

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "cvs"
STATIC = Path(__file__).resolve().parent / "static"
VARIANTS = ("few_shot", "zero_shot", "cot")
ALLOWED = (".pdf", ".txt")
MAX_BYTES = 5 * 1024 * 1024

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES
# Hosts like Render sit behind one proxy; trust its X-Forwarded-For so limits apply per visitor.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
# In-memory counters: correct as long as the server runs a single worker (see render.yaml).
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
RATE_LIMIT = os.getenv("CV2JSON_RATE_LIMIT", "10 per hour")


def _sample_label(p: Path) -> str:
    first = next((l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()), p.stem)
    return first.title() if first.isupper() else first


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/info")
def info():
    samples = [{"id": p.stem, "label": _sample_label(p)} for p in sorted(SAMPLES.glob("*.txt"))]
    return jsonify({"mock": MOCK, "model": MODEL, "variants": VARIANTS, "samples": samples})


@app.get("/api/samples/<name>")
def sample_text(name: str):
    p = SAMPLES / f"{name}.txt"
    if p.parent != SAMPLES or not p.exists():
        return jsonify({"error": "unknown sample"}), 404
    return jsonify({"id": name, "text": p.read_text(encoding="utf-8")})


@app.post("/api/convert")
@limiter.limit(RATE_LIMIT, exempt_when=lambda: MOCK)  # demo replays cost nothing
def convert():
    variant = request.form.get("prompt", "few_shot")
    if variant not in VARIANTS:
        return jsonify({"error": f"unknown prompt variant {variant!r}"}), 400

    sample = request.form.get("sample")
    upload = request.files.get("file")
    text = request.form.get("text", "").strip()

    tmp = None
    try:
        if sample:
            path = SAMPLES / f"{sample}.txt"
            if path.parent != SAMPLES or not path.exists():
                return jsonify({"error": "unknown sample"}), 404
        elif upload and upload.filename:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in ALLOWED:
                return jsonify({"error": "Only PDF and TXT files are supported."}), 400
            fd, tmp = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as fh:
                upload.save(fh)
            path = Path(tmp)
        elif text:
            fd, tmp = tempfile.mkstemp(suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            path = Path(tmp)
        else:
            return jsonify({"error": "Upload a file, paste text or pick a sample."}), 400

        try:
            rec = extract_one(path, variant, temperature=0.0)
        except FileNotFoundError:
            return jsonify({"error": "Demo mode has no recorded answer for this CV. "
                                     "Pick one of the sample CVs, or set ANTHROPIC_API_KEY "
                                     "and CV2JSON_MOCK=0 to convert your own."}), 422
        except Exception as e:  # API/auth/PDF errors: show them instead of a blank 500
            return jsonify({"error": f"{type(e).__name__}: {e}"}), 502

        rec["source"] = sample + ".txt" if sample else (upload.filename if upload and upload.filename else "pasted text")
        return jsonify(rec)
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)


@app.errorhandler(429)
def rate_limited(_):
    return jsonify({"error": f"Too many conversions from your address (limit: {RATE_LIMIT}). "
                             "Please try again later."}), 429


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "File is larger than 5 MB."}), 413


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
