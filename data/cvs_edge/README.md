# Edge-case CVs

Extra test CVs for the cases that break extraction most often. Kept out of `data/cvs/` so they do not appear as samples on the website (they have no recorded mock responses). Their expected answers are in `data/ground_truth/`, so `pytest` validates them and `python -m src.evaluate` scores them once extracted.

- `cv_07_injection_hidden.txt`: plain-text injections (a fake `[SYSTEM]` line and "ignore all previous instructions"), not hidden in an HTML comment like cv_05.
- `cv_08_missing_fields.txt`: almost empty CV: no contact details, no dates, no education, no languages. Everything absent must be `null` and listed in `missing_fields`.
- `cv_09_long.txt`: 6 jobs with many bullets, certifications, talks, volunteering. Tests that the model keeps all jobs and does not pull skills from non-skill sections.

```bash
python -m src.extract data/cvs_edge/ --prompt few_shot
python -m src.evaluate few_shot
```
