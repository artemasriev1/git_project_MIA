"""Score outputs/<variant>/*.json against data/ground_truth/*.json.

Usage: python -m src.evaluate [variant ...]   (default: every folder under outputs/)

Rubric (per CV):
  scalar fields  full_name, email, phone, location, years_of_experience -> exact match (case-insensitive, stripped)
  skills         set precision / recall after normalisation (lowercase, strip "basic"/"advanced")
  experience     each ground-truth job matched on (company, title); start/end must match; highlights are a subset check
  education      each ground-truth entry matched on (institution, degree, year)
  languages      set match on language name
  missing_fields recall (did the model declare what it truly could not find?)
  ok             did the output validate against the schema at all
`confidence` is deliberately not scored (no rubric for it yet, see docs/pr_001_few_shot.md).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GT_DIR = ROOT / "data" / "ground_truth"
OUT_DIR = ROOT / "outputs"

SCALARS = ["full_name", "email", "phone", "location", "years_of_experience"]
QUALIFIERS = ("basic ", "advanced ", "intermediate ", "expert ")


def norm(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    for q in QUALIFIERS:
        if s.startswith(q):
            s = s[len(q):]
    return s


def set_prf(pred: set, true: set) -> tuple[float, float]:
    if not true and not pred:
        return 1.0, 1.0
    tp = len(pred & true)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(true) if true else 1.0
    return p, r


def score_one(pred: dict, gt: dict) -> dict:
    s = {}
    for f in SCALARS:
        s[f] = float(norm(pred.get(f)) == norm(gt.get(f)))
    s["skills_p"], s["skills_r"] = set_prf({norm(x) for x in pred.get("skills", [])},
                                           {norm(x) for x in gt["skills"]})
    hits = 0
    pred_jobs = pred.get("experience", [])
    for job in gt["experience"]:
        for pj in pred_jobs:
            if norm(pj.get("company")) == norm(job["company"]) and norm(pj.get("title")) == norm(job["title"]):
                dates_ok = pj.get("start") == job["start"] and pj.get("end") == job["end"]
                hl_ok = all(any(norm(h) == norm(ph) for ph in pj.get("highlights", [])) for h in job["highlights"])
                hits += 1.0 if (dates_ok and hl_ok) else 0.5
                break
    s["experience"] = hits / len(gt["experience"]) if gt["experience"] else 1.0
    s["experience_extra"] = max(0, len(pred_jobs) - len(gt["experience"]))
    hits = 0
    for e in gt["education"]:
        if any(norm(pe.get("institution")) == norm(e["institution"]) and norm(pe.get("degree")) == norm(e["degree"])
               and pe.get("year") == e["year"] for pe in pred.get("education", [])):
            hits += 1
    s["education"] = hits / len(gt["education"]) if gt["education"] else 1.0
    s["languages_p"], s["languages_r"] = set_prf({norm(x["language"]) for x in pred.get("languages", [])},
                                                 {norm(x["language"]) for x in gt["languages"]})
    _, s["missing_fields_r"] = set_prf(set(pred.get("missing_fields", [])), set(gt["missing_fields"]))
    return s


def evaluate(variant: str) -> dict:
    folder = OUT_DIR / variant
    rows, agg = [], defaultdict(list)
    for gt_path in sorted(GT_DIR.glob("*.json")):
        out_path = folder / gt_path.name
        if not out_path.exists():
            continue
        rec = json.loads(out_path.read_text(encoding="utf-8"))
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        if not rec.get("ok"):
            row = {k: 0.0 for k in ["ok"] + SCALARS + ["skills_p", "skills_r", "experience", "education",
                                     "languages_r", "missing_fields_r"]}
            row["experience_extra"] = 0
        else:
            row = {"ok": 1.0, **score_one(rec["data"], gt)}
        row["cv"] = gt_path.stem
        rows.append(row)
        for k, v in row.items():
            if k != "cv":
                agg[k].append(v)
    means = {k: sum(v) / len(v) for k, v in agg.items()} if rows else {}
    return {"variant": variant, "n": len(rows), "rows": rows, "mean": means}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    variants = argv or sorted(p.name for p in OUT_DIR.iterdir() if p.is_dir())
    results = [evaluate(v) for v in variants]
    results = [r for r in results if r["n"]]
    if not results:
        sys.exit("no outputs found; run python -m src.extract first")
    cols = ["ok", "full_name", "email", "phone", "location", "years_of_experience", "skills_p", "skills_r",
            "experience", "experience_extra", "education", "languages_r", "missing_fields_r"]
    print(f"{'variant':12s} n  " + " ".join(f"{c[:9]:>9s}" for c in cols))
    for r in results:
        print(f"{r['variant']:12s} {r['n']:<2d} " + " ".join(f"{r['mean'].get(c, 0):9.2f}" for c in cols))
    print("\nper-CV detail (experience score):")
    for r in results:
        print(f"  {r['variant']}: " + ", ".join(f"{row['cv']}={row['experience']:.1f}" for row in r["rows"]))
    (OUT_DIR / "evaluation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
