import json
from pathlib import Path

import pytest

from src.schema import CV, parse_model_output

GT = Path(__file__).resolve().parent.parent / "data" / "ground_truth"


@pytest.mark.parametrize("path", sorted(GT.glob("*.json")))
def test_ground_truth_validates(path):
    CV.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_parse_handles_fences_and_prose():
    text = 'Here is the result:\n```json\n{"full_name": "A B", "skills": ["x"]}\n```'
    cv = parse_model_output(text)
    assert cv.full_name == "A B" and cv.skills == ["x"]


def test_parse_rejects_bad_date():
    with pytest.raises(ValueError, match="date must be"):
        parse_model_output('{"full_name": "A", "experience": [{"start": "March 2020"}]}')


def test_parse_rejects_no_json():
    with pytest.raises(ValueError):
        parse_model_output("I could not extract anything.")
