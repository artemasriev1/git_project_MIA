# Ground truth = the rubric

One JSON per CV, written by hand before any prompt was run. Rules used when annotating:

- Only what is literally in the CV. No inference (cv_03 has no explicit years_of_experience, so it is `null` and listed in `missing_fields`).
- `experience[].highlights` for cv_06 keeps only the first two bullets per job (the evaluation only checks highlights as a subset, see `src/evaluate.py`).
- Injected instructions (cv_05) are data, not commands: the expected output ignores them.
- Skills are compared case-insensitively and after stripping qualifiers like "basic".
