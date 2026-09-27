# Prompt log

Every change to a prompt is a commit; this file records *why*.

## v1 zero_shot (Session 2)
System prompt states the schema, forbids invention, declares CV text as data.
Observation on first run (see outputs/zero_shot/): hallucination of `years_of_experience` on cv_03 (model computed 4 from dates although the CV never states it). Fixed by adding "only if stated explicitly" to the schema comment.

## v2 few_shot (Session 3)
Two examples. Second one embeds an injected instruction whose expected JSON ignores it, so the model sees the desired behaviour instead of only reading a rule about it.
Merge conflict with the concurrent skill-normalisation rule on main; resolved by keeping both (docs/pr_001_few_shot.md).

## v3 cot (Session 4)
Scratchpad forces a "quote the supporting line or write NOT STATED" step before the JSON. Costs roughly 2x tokens and latency; hypothesis is that it buys abstention on cv_03 and resistance on cv_05. Measured, not assumed: see docs/results.md.
