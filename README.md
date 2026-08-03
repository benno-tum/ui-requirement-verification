# UI Requirement Verification

Code and repository data for deriving and verifying UI-facing software requirements from screenshot flows.

> **Using the web application:** See the
> [Web Application Guide](docs/web_application_guide.md) for a professor-facing
> walkthrough, the fresh-clone data boundary, verification-run instructions,
> and troubleshooting.

## Licensing and dataset boundary

Original software in this repository is available under the MIT License. The
license does not cover the thesis text, the CC BY-SA thesis template,
Mind2Web/PURE material, or other third-party content. See [`LICENSE`](LICENSE)
and [`NOTICE.md`](NOTICE.md) for the exact scope.

The numbered flows and their annotations are derived from the Mind2Web
`test_task` split. Mind2Web identifies its dataset as CC BY 4.0 but also asks
users not to redistribute unzipped test files online or place benchmark data in
training corpora. Do not commit screenshots, test records, HTML/MHTML, HAR
files, traces, videos, or per-item raw model interactions.

PURE source documents were collected from third-party Web sources whose
individual licensing status is not guaranteed by the PURE curators. Do not
commit PURE PDFs, XML files, extracted figures, substantial source passages, or
per-item prompts and outputs reproducing them.

The release policy and attribution language are documented in
`docs/dataset_licensing_and_release_policy_2026-07-23.md`. The public
`artifacts/thesis_evaluation/` package contains aggregate replication results.
The explicit allowlist under `data/published/` additionally contains one
sanitized Mind2Web-derived run set; it excludes source screenshots and page
text, raw provider interactions, caches, secrets, and absolute paths.

## Repository layout

The repository now separates versioned requirement data from local flow data:

- `data/annotations/requirements_candidate/`: versioned candidate requirement snapshots that should be committed
- `data/annotations/requirements_gold/`: versioned gold requirement annotations
- `data/annotations/flow_manifests/`: versioned manifests for reproducible flow exports
- `data/processed/flows/`: local screenshot flows, not committed
- `data/generated/`: local generated artifacts, prompts, verification runs, and other working files, not committed
- `data/published/`: curated, sanitized verification outputs included for evaluator inspection

If you clone the repo fresh, the requirements are present, but the screenshot flows are not. You must install or export the flows before the flow browser in the backend can show anything useful.
The repository therefore defines one canonical local flow set that can be recreated from versioned manifests.

## Quick start for a fresh clone

Requirements:

- Python 3.12
- Node.js 20.19+ (or 22.12+)

Run this from the repository root:

```bash
git clone https://github.com/benno-tum/ui-requirement-verification.git
cd ui-requirement-verification

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[llm,data,dev]"

# This export scans the Mind2Web split and can take a few minutes.
python scripts/export_mind2web.py --split test_task --max-flows 0 --allowed-flows-file data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt
uvicorn ui_verifier.api.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Optional for generation and verification with Gemini and text-only DeepSeek experiments:

```bash
cp .env.example .env
```

Add:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GEMINI_EUR_PER_USD=0.92
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

`OPENROUTER_API_KEY` is needed only for the hosted Qwen open-weight baseline.
Never commit `.env`; it is ignored by Git.

Gemini API calls through the repository wrapper are logged locally under
`data/generated/gemini_usage/`. The app exposes the aggregate via:

```text
GET http://127.0.0.1:8000/gemini-usage
```

The log stores token counts, model name, image count, estimated USD cost, and
estimated EUR cost if `GEMINI_EUR_PER_USD` is set. Treat this as a local estimate;
Google Billing remains the source of truth for taxes, currency conversion, credits,
and final charges.

Model defaults are role-based and configured in `configs/models.json`. Override the
whole file with `UI_VERIFIER_MODEL_CONFIG` or a single role with variables such as
`UI_VERIFIER_CLAIM_DECOMPOSITION_PROVIDER`,
`UI_VERIFIER_CLAIM_DECOMPOSITION_MODEL`, and
`UI_VERIFIER_CLAIM_DECOMPOSITION_TEMPERATURE`. The backend exposes the active
resolved values via:

```text
GET http://127.0.0.1:8000/model-config
```

See `docs/model_configuration.md` for recommended model choices and evaluation
override examples.

URLs:

- backend: `http://127.0.0.1:8000`
- frontend: `http://127.0.0.1:5173`
- docs: `http://127.0.0.1:8000/docs`

## Install flow data

The backend starts without preinstalled flows, but `/flows` will otherwise be empty because `data/processed/flows/` is intentionally not checked in.

### Export the repository dataset flows

The checked-in requirement annotations correspond to the numbered Mind2Web repository dataset flows `01_...` to `13_...`. Recreate that local flow set with:

```bash
python scripts/export_mind2web.py --split test_task --max-flows 0 --allowed-flows-file data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt
```

This keeps the local flow install aligned with the committed requirement annotations. The export script still scans the full Hugging Face split metadata, so seeing totals such as `177` grouped flows is expected; the manifest then reduces the exported set to the repository dataset.

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

Those flows remain local-only unless you deliberately add them to the repository dataset manifest and commit their requirement annotations.

## Frontend

A lightweight React + Vite + TypeScript frontend is available in `frontend/`.

```bash
cd frontend
npm ci
npm run dev
```

By default the frontend calls `http://127.0.0.1:8000`. To override this, set `VITE_API_BASE_URL`.

### Ad-hoc screenshot verification

Open `http://127.0.0.1:5173/verify/new` (or choose **New screenshot verification** in the workbench) to:

- upload and order up to 20 screenshots;
- paste requirements or import a JSON, TXT, or Markdown requirements file;
- run the deterministic or Gemini image verification pipeline; and
- inspect requirement decisions, claim evidence, run history, and localized bounding boxes.

Uploaded flows are stored locally under `data/processed/flows/uploads/`. Their normalized requirements and pipeline outputs stay under `data/generated/`.

## Tests

Run the Python test suite from the repository root:

```bash
pytest
```

Validate the frontend production build:

```bash
cd frontend
npm ci
npm run build
```

For the exact evaluation environment used on 23 July 2026, install the regular
project extras with the pinned constraints:

```bash
pip install -e ".[llm,data,dev]" -c constraints-thesis-eval.txt
```

Local SmolVLM experiments use the separate pinned
`requirements-open-vlm.txt` environment because PyTorch and Transformers are
not runtime requirements of the main application.

## Build the thesis

The thesis uses the TUM LaTeX template and is built independently from the
application. A complete TeX installation with `latexmk` is required:

```bash
cd thesis
make all
```

The resulting PDF is written to `thesis/build/main.pdf` and is intentionally
ignored by Git. See [`thesis/README.md`](thesis/README.md) for template
attribution and additional build details.

## Thesis experiment reproduction

The current experiment definitions are:

- `configs/thesis_final_experiments.json`: completed controlled matrix and model roles;
- `configs/thesis_remaining_runs.json`: prepared stability repetitions and optional oracle diagnostics.

Generate a preflight manifest without making API calls:

```bash
python scripts/run_thesis_final_experiments.py \
  --config configs/thesis_remaining_runs.json \
  --tiers core \
  --manifest-out data/generated/thesis_final_experiments/stability_preflight_manifest.json
```

The manifest records the Git state, benchmark and source hashes, exact commands,
model parameters, expected coverage, and conservative cost bounds. Paid calls
require both `--execute` and an explicit `--cost-ceiling-usd`. The ceiling is an
authorization guard, not a provider-side billing limit.

Each repeated execution has a separate output and verifier-cache directory.
Do not use `--force` to create a reported repetition from an already completed
directory; use a new repetition ID instead. After the prepared `r2` and `r3`
runs finish, summarize them with:

```bash
python scripts/analyze_thesis_run_stability.py
```

In the current lexical top-k implementation, `top-4` means a shared four-image
cap for a batch of up to eight claims. It must not be described as an
independent per-requirement top-4 condition.

Newly generated runs remain under `data/generated/` and are not committed
wholesale. A curated sanitized run set is versioned under `data/published/` so
the web application can display representative predictions and bounding boxes
in a fresh clone.
The release-facing replication package is curated under
`artifacts/thesis_evaluation/`; its README defines the licensing, privacy, and
path-sanitization gate that must be satisfied before publishing model traces or
Mind2Web-derived artifacts.

## Data workflows

Optional PURE experiments require a separately obtained local copy of PURE;
the source documents are intentionally not included in a fresh clone. See
[`docs/claim_decomposition_external_eval.md`](docs/claim_decomposition_external_eval.md)
for the expected directory layout and extraction commands.

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
  You passed a literal trailing backslash as an argument. Use the one-line Python command from the README, or make sure `\` is only used as a shell line continuation with no trailing characters after it.
- `ValueError: 'data/...' is not in the subpath of '...repo...'`
  Update to the current branch head and rerun the export. Older versions of `scripts/export_mind2web.py` mishandled relative allowlist paths.
- `sh: vite: command not found`
  Run `npm ci` inside `frontend/` first.
- Backend starts but `/flows` is empty
  You have not exported the local flow data yet. Run the one-line `python scripts/export_mind2web.py ...` command from `Install flow data`.
