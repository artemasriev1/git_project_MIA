# Results

> **Status of these numbers:** produced with `CV2JSON_MOCK=1` on the illustrative mock set in `data/mock/`, which encodes the behaviours we expected to see (see `scripts/build_mock.py`). They demonstrate the evaluation pipeline, not the model. Before the defence, regenerate with a real key:
> ```
> for v in zero_shot few_shot cot; do CV2JSON_RECORD=1 python -m src.extract data/cvs --prompt $v; done
> python -m src.evaluate
> ```
> then replace this table and delete the warning.

| variant | ok | years_of_experience | skills_p | experience | education | missing_fields_r |
|---|---|---|---|---|---|---|
| zero_shot | 1.00 | 0.67 | 0.92 | 0.94 | 1.00 | 0.96 |
| few_shot | 1.00 | 1.00 | 1.00 | 0.94 | 1.00 | 1.00 |
| cot | 0.83 | 0.83 | 0.83 | 0.83 | 0.83 | 0.83 |

Reading: few-shot fixes the two behavioural problems (inferred years on cv_03, injection on cv_05) at negligible token cost. Chain-of-thought fixes the same two but breaks on the long CV because the scratchpad eats the output budget; its 0.83 across the board is one CV out of six failing validation, not a general quality drop. Nobody handles cv_06 fully.

Decision: **few_shot is the default prompt.** CoT is kept as a diagnostic tool (its scratchpad is the fastest way to see *why* a value was produced), not as the production path.
