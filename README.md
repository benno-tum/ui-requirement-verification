# UI Requirement Verification

Code and sample outputs for deriving and verifying UI-facing software requirements from screenshot flows.

## Setup

### Prerequisites

- Python 3.12 is the current working target for this repository.
- Node.js 18+ is recommended for the frontend.
- The checked-in `.python-version` is `tech`, so if you use `pyenv` with `pyenv-virtualenv`, create an environment with that name.

### Python environment with pyenv

On macOS with Homebrew:

```bash
brew install pyenv pyenv-virtualenv
pyenv install 3.12.13
pyenv virtualenv 3.12.13 tech
pyenv local tech
python -m pip install --upgrade pip
pip install -e ".[llm,data,dev]"
```

If you do not use `pyenv`, a plain virtual environment also works:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[llm,data,dev]"
```

### Environment variables

Model-backed requirement generation and verification use Gemini. Create a local `.env` file from the example and add your API key:

```bash
cp .env.example .env
```

`.env` should contain:

```bash
GEMINI_API_KEY=your_api_key_here
```

If you only want to browse existing flows and annotations locally, the backend can start without `GEMINI_API_KEY`. You only need it for generation and verification flows.

## Backend

Run the FastAPI server from the repository root:

```bash
uvicorn ui_verifier.api.main:app --reload
```

Useful endpoints include:

- `GET /health`
- `GET /flows`
- `GET /flows/{flow_id}`
- `GET /flows/{flow_id}/steps`
- `GET /flows/{flow_id}/harvested`
- `GET /flows/{flow_id}/candidates`
- `GET /flows/{flow_id}/gold`
- `GET /flows/{flow_id}/verification/latest`
- `POST /flows/{flow_id}/harvested/generate`

The API docs are available at `http://127.0.0.1:8000/docs`.

Static screenshots are served under `/static/flows/...`, and generated candidate artifacts are served under `/static/candidate_artifacts/...`.

## Frontend

A lightweight React + Vite + TypeScript frontend is available in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

By default the frontend calls `http://127.0.0.1:8000`. To override this, set `VITE_API_BASE_URL`.

## Tests

Run the Python test suite from the repository root:

```bash
pytest
```

## Data and helper scripts

- Processed sample flows already live under `data/processed/flows/`.
- Candidate artifacts and verification outputs are written under `data/generated/`.
- Gold annotations live under `data/annotations/requirements_gold/`.

Export a small Mind2Web sample:

```bash
python scripts/export_mind2web.py --split test_task --max-flows 10
```

Backfill original Mind2Web screenshots for existing exported flows:

```bash
python scripts/backfill_mind2web_originals.py --flows-root data/processed/flows/mind2web
```

Generate harvested and candidate requirements for one flow from the CLI:

```bash
python scripts/generate_candidate_requirements.py \
  --flow-dir data/processed/flows/mind2web/<flow_id> \
  --max-images 6
```
