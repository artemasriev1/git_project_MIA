# The four failure modes, on this project

Run any of them live: `python -m src.failure_demo <name>` (needs a real key; mock mode has no recording for these prompts by design).

| Failure | Where it shows up here | How we detect it | What mitigates it | Cost of the mitigation |
|---|---|---|---|---|
| Hallucination | cv_03: no explicit years of experience, model computes 4 from dates and returns it as fact | `years_of_experience` scalar mismatch + `missing_fields_r` drop in evaluate | Rule "only if stated explicitly"; few-shot example with a null; CoT "quote the supporting line or NOT STATED" | CoT doubles tokens; a model that abstains too much lowers recall |
| Sycophancy | Recruiter asserts "8 years, fluent German" in the user turn; model confirms | Manual demo (no automated metric yet) | Role separation: schema and rules live in the system prompt, the CV is the only source of truth; user turn is not allowed to supply values | A polite model may still hedge instead of contradicting; needs a test set of adversarial user claims |
| Prompt injection | cv_05: HTML comment addressed to "any AI system" asks for CFO title and 15 years | Diff against ground truth: `experience_extra`, `years_of_experience`, skills precision | Rule 2 (CV is data) + few-shot example showing the injected text being ignored + CoT step that names the injection | None of these is a guarantee; a delimiter-based approach (`<cv>` tags) only helps if the model respects it |
| Context window overflow | cv_06 (2,600 words) plus appendix: oldest job silently dropped or JSON truncated; CoT fails outright because the scratchpad consumes the output budget | `ok` = 0 (invalid JSON) or `experience` < 1 with no error | Chunk by section, or a two-pass approach (first pass lists jobs, second pass extracts each); raise `max_tokens` for CoT | More API calls, more code, and merging chunk outputs is its own source of errors |

## Ranking for this use case
Injection and hallucination are the two that matter for a CV parser used in hiring: a candidate controls the input, and a downstream ATS will treat the JSON as fact. Overflow is bounded (CVs rarely exceed 3 pages). Sycophancy matters only if humans chat with the extractor, which the CLI design avoids.
