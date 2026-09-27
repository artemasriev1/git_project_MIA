# Oral defence: technical choices and their justification

**Why a validated schema rather than free JSON?** A `ValueError` on invalid output is an observable failure that the evaluation counts. Free JSON turns every model slip into a silent downstream bug.

**Why `missing_fields` in the output?** Gives the model a legitimate way to say "not found" that is cheaper than inventing. It is also scorable (recall against ground truth).

**Why is the CV wrapped in `<cv>` tags and everything else in the system prompt?** Role separation. The system turn is the only place values are allowed to come from the rules; the user turn carries data only. Cuts the sycophancy surface to zero in the CLI.

**Why temperature 0?** Extraction is a deterministic task; we want repeatability across peers running the same commit. Temperature 0 does not make outputs identical (top-p and server-side batching still vary) but it removes the sampling noise we would otherwise have to average over.

**Why `mock` mode?** Peers must be able to run the project without paying. Also makes tests and CI possible. Cost: mock responses go stale when prompts change (they are keyed on a prompt hash, so a changed prompt simply has no mock and fails loudly).

**Why exponential backoff with jitter?** 429 is not an error to surface to the user; it is the API asking us to wait. Jitter avoids synchronised retries when a whole class runs the script at once.

**Why ground truth before prompts?** Otherwise the rubric drifts towards whatever the first prompt produced.

**What we would do with two more sessions:** two-pass extraction for long CVs, an adversarial set of user-turn claims to score sycophancy, and a rubric for `confidence` so it stops being noise.

**LLM vs agent vs agentic system:** this is a plain LLM call with validation around it. A conversational agent would let a recruiter ask follow-up questions; an agentic system would fetch the candidate's GitHub and verify claims. Neither is needed for the stated use case and both widen the injection surface.
