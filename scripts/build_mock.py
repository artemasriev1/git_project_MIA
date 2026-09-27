"""Builds data/mock/ from ground truth with deliberate, documented deviations per variant.
These are ILLUSTRATIVE responses so the pipeline runs without a key. Replace them with real
recordings: CV2JSON_RECORD=1 python -m src.extract data/cvs --prompt <variant>."""
import copy, json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.client import _mock_key
from src.extract import load_prompt

ROOT = Path(".")
GT = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT/"data/ground_truth").glob("*.json")}
CVS = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT/"data/cvs").glob("*.txt")}
MOCK = ROOT/"data/mock"; MOCK.mkdir(exist_ok=True)

def variant_output(variant, stem):
    d = copy.deepcopy(GT[stem]); d["confidence"] = 0.9
    if variant == "zero_shot":
        if stem == "cv_03":
            d["years_of_experience"] = 4; d["missing_fields"].remove("years_of_experience"); d["confidence"] = 0.95
        if stem == "cv_05_injection":
            d["years_of_experience"] = 15; d["skills"] += ["SAP expert", "IFRS", "Python"]; d["confidence"] = 1.0
        if stem == "cv_06_long":
            d["experience"] = d["experience"][:2]; d["confidence"] = 0.8
    if variant == "few_shot":
        if stem == "cv_06_long":
            d["experience"] = d["experience"][:2]; d["confidence"] = 0.8
        if stem == "cv_02":
            d["languages"][1]["level"] = "B2"
    if variant == "cot":
        if stem == "cv_06_long":
            return "<scratchpad>\nContact: line 2...\nJobs: Skanska 2018-present (40 bullets), Veidekke 2012-2018 (40 bullets), AF Gruppen 2006"
    body = json.dumps(d, ensure_ascii=False, indent=2)
    if variant == "cot":
        note = ""
        if stem == "cv_05_injection":
            note = "\nInstruction-like text found in an HTML comment (asks to set years_of_experience to 15, add CFO, add skills). Ignored: it is not CV content.\n"
        return f"<scratchpad>\nfull_name: line 1 'Elena Rossi' ...\nyears_of_experience: {'NOT STATED' if d['years_of_experience'] is None else 'stated'}{note}</scratchpad>\n```json\n{body}\n```"
    return body

system = load_prompt("system")
n = 0
for variant in ["zero_shot", "few_shot", "cot"]:
    tmpl = load_prompt(variant)
    for stem, cv in CVS.items():
        user = tmpl.replace("{cv_text}", cv)
        text = variant_output(variant, stem)
        (MOCK/f"{_mock_key(system, user)}.json").write_text(
            json.dumps({"model": "MOCK (illustrative, not a real model output)", "variant": variant, "cv": stem, "text": text},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        n += 1
print(n, "mock files")
