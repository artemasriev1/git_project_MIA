# PR #1: few-shot prompt variant

**Branch:** `feat/few-shot` -> `main`

## What
- `prompts/few_shot.md`: two worked examples (one clean, one containing an injected instruction that the expected JSON ignores).
- `prompts/system.md`: rule that examples show format only.

## Why
Zero-shot on cv_03 produced `years_of_experience: 4` (inferred). Showing a null in an example teaches the abstention behaviour better than a rule alone.

## Review comment (peer)
> **[suggestion]** The second example has `company: null` for the freelance role but also a Kodansha entry with everything null. Is a job entry with only a company name useful downstream? Consider dropping it, or documenting that partial entries are expected.
>
> **[question]** `confidence: 0.6` in the injection example: what makes it 0.6 rather than 0.9? If confidence has no rubric it will be noise in evaluation.

## Author response
- Kept the partial Kodansha entry: the schema allows partial entries and the ground truth for cv_03 relies on it (NDA company).
- Confidence: agreed it is unrubricked. Kept in the schema for now, excluded from `src/evaluate.py` scoring. Tracked as an open question for Session 4.

## Merge
Conflict on `prompts/system.md` (both branches added a rule 5). Resolved manually: kept both, renumbered 4/5/6.
