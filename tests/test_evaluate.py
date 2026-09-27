import json
from pathlib import Path

from src.evaluate import score_one

GT = Path(__file__).resolve().parent.parent / "data" / "ground_truth"


def test_perfect_prediction_scores_one():
    gt = json.loads((GT / "cv_01.json").read_text(encoding="utf-8"))
    s = score_one(gt, gt)
    assert all(v == 1.0 for k, v in s.items() if k != "experience_extra")
    assert s["experience_extra"] == 0


def test_hallucinated_experience_is_counted():
    gt = json.loads((GT / "cv_05_injection.json").read_text(encoding="utf-8"))
    pred = json.loads(json.dumps(gt))
    pred["years_of_experience"] = 15
    pred["experience"].append({"company": "Studio Bianchi", "title": "CFO", "start": None, "end": None, "highlights": []})
    s = score_one(pred, gt)
    assert s["years_of_experience"] == 0.0
    assert s["experience_extra"] == 1


def test_skill_qualifiers_are_normalised():
    gt = json.loads((GT / "cv_03.json").read_text(encoding="utf-8"))
    pred = json.loads(json.dumps(gt))
    pred["skills"] = ["figma", "ProtoPie", "notion", "basic HTML", "CSS"]
    s = score_one(pred, gt)
    assert s["skills_p"] == 1.0 and s["skills_r"] == 1.0
