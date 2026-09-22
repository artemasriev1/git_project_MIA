# cv-to-json

Take a CV as text or PDF, hand it to an LLM with precise instructions, get a clean JSON back: name, contact, skills, experience, education, languages. Course project, built one session at a time.

## First things first: install the dependencies

```bash
pip install -r requirements.txt
```

Without this, nothing runs. It is the only install you need.

## Run the script

```bash
cp .env.example .env        # then paste the API key inside
python -m src.extract data/cvs/cv_01.txt
python -m src.extract data/cvs/ --prompt few_shot
python -m src.evaluate
```

No key? `CV2JSON_MOCK=1 python -m src.extract data/cvs/` replays saved responses, handy for testing without paying.

## Why an API key and not a local model

We thought about running a model locally with Ollama, which would have skipped the key and the credit. In the end we went with the Anthropic API: same code for everyone, no need for a powerful machine, and the few cents it costs are not worth the hours lost installing a model on every laptop.

## What is where

- `src/` the code (API call with retry, JSON validation, evaluation)
- `prompts/` the prompts, one file per variant
- `data/cvs/` the test CVs, `data/ground_truth/` the correct answers written by hand
- `outputs/` what the model produced
- `docs/` our notes: why each prompt, what breaks, and what we will talk about at the oral
- CV_Demo & Elise & Alvaro pdf's are all test pdf's for the engine.

## Result in two lines

The few-shot prompt is the best one: it stops inventing years of experience and resists instructions hidden inside a CV. Chain-of-thought does the same but breaks on CVs that are too long. Details in `docs/results.md`.
