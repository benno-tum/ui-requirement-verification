# UI Requirement Verification

Code and sample outputs for deriving and verifying UI-facing software requirements from screenshot flows.

## Repository layout

The repository now separates versioned requirement data from local flow data:

- `data/annotations/requirements_candidate/`: versioned candidate requirement snapshots that should be committed
- `data/annotations/requirements_gold/`: versioned gold requirement annotations
- `data/annotations/flow_manifests/`: versioned allowlists for reproducible flow exports
- `data/processed/flows/`: local screenshot flows, not committed
- `data/generated/`: local generated artifacts, prompts, verification runs, and other working files, not committed

If you clone the repo fresh, the requirements are present, but the screenshot flows are not. You must install or export the flows before the flow browser in the backend can show anything useful.

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

## Quick start for a fresh clone

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[llm,data,dev]"
python scripts/export_mind2web.py --split test_task --max-flows 0 --allowed-flows-file data/annotations/flow_manifests/mind2web_sample_annotation_ids.txt
uvicorn ui_verifier.api.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Expected result:

- backend: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

## Install flow data

The backend starts without preinstalled flows, but `/flows` will otherwise be empty because `data/processed/flows/` is intentionally not checked in.

### Export the repository sample flows

The checked-in requirement annotations correspond to the numbered Mind2Web sample flows `01_...` to `13_...`. Export exactly that sample set with:

```bash
python scripts/export_mind2web.py --split test_task --max-flows 0 --allowed-flows-file data/annotations/flow_manifests/mind2web_sample_annotation_ids.txt
```

If you copy commands into an IDE run configuration or a shell manually, prefer the single-line command above. A trailing `\` only works as a shell line continuation when it is the final character on the line.

This keeps the local flow install aligned with the committed requirement annotations and avoids downloading unrelated sample flows. The export script still scans the full Hugging Face split metadata, so seeing totals such as `177` grouped flows is expected; the allowlist then reduces the exported set to the repository sample.

The export already writes both:

- downscaled screenshots as `step_XX.png`
- original screenshots under `original/`

So for a fresh export, no separate backfill step is needed. The backfill script is only useful for older exports that were created without original screenshots:

```bash
python scripts/backfill_mind2web_originals.py --flows-root data/processed/flows/mind2web
```

### Export a different local flow set

If you want a larger or different local dataset, you can export arbitrary Mind2Web flows:

```bash
python scripts/export_mind2web.py --split test_task --max-flows 10
```

Those flows remain local-only unless you deliberately derive and commit requirement annotations for them.

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

If `npm run dev` fails with `vite: command not found`, you have not installed the frontend dependencies in that clone yet. Run:

```bash
cd frontend
npm install
```

## Tests

Run the Python test suite from the repository root:

```bash
pytest
```

## Data workflows

### Versioned requirement data

- Candidate requirement snapshots are read from `data/annotations/requirements_candidate/` when present.
- Gold annotations are read from `data/annotations/requirements_gold/`.
- Editing or rebuilding candidate requirements through the app writes the candidate JSON snapshots back into `data/annotations/requirements_candidate/`.

### Local generated artifacts

- Harvested requirements, prompt bundles, Gemini raw outputs, and verification runs are written under `data/generated/`.
- These files are intentionally ignored by Git and are treated as local working state.

### CLI generation

Generate harvested and candidate requirements for one flow from the CLI:

```bash
python scripts/generate_candidate_requirements.py --flow-dir data/processed/flows/mind2web/<flow_id> --max-images 6
```

## Troubleshooting

- `export_mind2web.py: error: unrecognized arguments: \\`
  You passed a literal trailing backslash as an argument. Use the single-line command from the README, or make sure `\` is only used as a shell line continuation with no trailing characters after it.
- `ValueError: 'data/...' is not in the subpath of '...repo...'`
  Update to the current branch head and rerun the export. Older versions of `scripts/export_mind2web.py` mishandled relative allowlist paths.
- `sh: vite: command not found`
  Run `npm install` inside `frontend/` first.
- Backend starts but `/flows` is empty
  You have not exported the local flow data yet. Run the sample export command from `Install flow data`.
