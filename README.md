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
python -m src.extract data/pdf/          # PDF CVs work too
python -m src.evaluate
python -m src.analyst data/cvs/cv_01.txt --role data_analyst  # extract, then write a career report to outputs/analysis/
python -m src.auditor data/pdf/<file>.pdf --job job.txt --market France  # screening audit to outputs/audit/
pytest                                   # unit tests, no API key needed
```

No key? `CV2JSON_MOCK=1 python -m src.extract data/cvs/` replays saved responses, handy for testing without paying.

## The website: Albert Convert

A web front end for the same pipeline (upload a PDF/TXT, paste text, or try a sample CV):

```bash
python -m web.app                    # then open http://127.0.0.1:5000
CV2JSON_MOCK=1 python -m web.app     # no key: demo mode, sample CVs only
```

The page lives in `web/static/index.html`; `web/app.py` calls `src.extract.extract_one`, so the site and the CLI share prompts, retries and schema validation.

After a valid conversion the page offers a **career analysis** (`/api/analyse` → `src.analyst.stream_analysis`): a second call that reads the validated JSON plus the CV numbered line by line (`prompts/analyst.md`) and streams back a Markdown report for the chosen target role (data scientist, data analyst, data engineer, ML engineer, AI engineer; see `ROLES` in `src/analyst.py`). Its claims cite line numbers, clickable on the page. It uses the same key and client; set `CV2JSON_ANALYST_MODEL` to give it a different model. In demo mode it only works for CVs whose analysis was recorded with `CV2JSON_RECORD=1`.

The page also offers a **CV screening audit** (`/api/audit` → `src.auditor.stream_audit`): it checks the CV the way applicant tracking systems, AI rankers and recruiters read it, across 59 dimensions (`prompts/cv_audit.md`), and returns every shortfall as a flag, most critical first, with evidence, the reason and a fix. A pasted job description (optional, strongly recommended) enables the job-specific checks; target role and market are optional too. It only sees the CV's extracted text, so layout and hidden-text checks are reported as not assessable. Set `CV2JSON_AUDIT_MODEL` to give it its own model.

### Deploying (Render)

`render.yaml` describes the service. On render.com: **New → Blueprint**, pick this repo, deploy. It starts in demo mode (`CV2JSON_MOCK=1`). To convert real CVs, set `ANTHROPIC_API_KEY` in the Render dashboard and change `CV2JSON_MOCK` to `0`.

Once live, every visitor's conversion is billed to that key. `/api/convert`, `/api/analyse` and `/api/audit` share one limit per IP (`CV2JSON_RATE_LIMIT`, default `10 per hour`, all calls counted together); also set a monthly spend limit in the Anthropic console.

## Why an API key and not a local model

We thought about running a model locally with Ollama, which would have skipped the key and the credit. In the end we went with the Anthropic API: same code for everyone, no need for a powerful machine, and the few cents it costs are not worth the hours lost installing a model on every laptop.

## What is where

- `web/` the Albert Convert website (Flask server + single-page front end)
- `src/` the code (API call with retry, JSON validation, evaluation, career analyst, screening auditor)
- `tests/` the pytest suite
- `prompts/` the prompts, one file per variant
- `data/cvs/` the test CVs as text, `data/ground_truth/` the correct answers written by hand
- `data/pdf/` sample PDF CVs (fictive) to test PDF input
- `data/mock/` saved responses for running without an API key
- `outputs/` what the model produced
- `docs/` our notes: why each prompt, what breaks, and what we will talk about at the oral
- `scripts/` helper scripts, `notebooks/` exploration only

## Result in two lines

The few-shot prompt is the best one: it stops inventing years of experience and resists instructions hidden inside a CV. Chain-of-thought does the same but breaks on CVs that are too long. Details in `docs/results.md`.
