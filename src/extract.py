"""CLI: python -m src.extract <file-or-folder> [--prompt zero_shot|few_shot|cot] [--temperature 0.0]"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .client import complete
from .schema import parse_model_output

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
OUTPUTS = ROOT / "outputs"


def read_cv(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    p = PROMPTS / f"{name}.md"
    if not p.exists():
        sys.exit(f"unknown prompt variant {name!r}; available: "
                 + ", ".join(sorted(x.stem for x in PROMPTS.glob('*.md') if x.stem not in ('system', 'analyst'))))
    return p.read_text(encoding="utf-8")


def extract_one(cv_path: Path, variant: str, temperature: float) -> dict:
    system = load_prompt("system")
    user = load_prompt(variant).replace("{cv_text}", read_cv(cv_path))
    t0 = time.time()
    raw = complete(system, user, temperature=temperature)
    elapsed = round(time.time() - t0, 2)
    record = {"source": cv_path.name, "prompt": variant, "temperature": temperature,
              "elapsed_s": elapsed, "raw": raw}
    try:
        record["data"] = parse_model_output(raw).model_dump()
        record["ok"] = True
    except ValueError as e:
        record["data"] = None
        record["ok"] = False
        record["error"] = str(e)
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--prompt", default="zero_shot")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--out", type=Path, default=None,
                    help="output folder (default outputs/<prompt>/)")
    a = ap.parse_args(argv)

    files = sorted(p for p in a.path.iterdir() if p.suffix.lower() in (".txt", ".pdf")) if a.path.is_dir() else [a.path]
    out_dir = a.out or OUTPUTS / a.prompt
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for f in files:
        rec = extract_one(f, a.prompt, a.temperature)
        (out_dir / f"{f.stem}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "ok " if rec["ok"] else "ERR"
        print(f"[{status}] {f.name:22s} {rec['elapsed_s']:>5}s  -> {out_dir / (f.stem + '.json')}")
        failures += not rec["ok"]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
