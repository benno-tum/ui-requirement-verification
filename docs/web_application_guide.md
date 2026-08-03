# Web Application Guide

This guide is intended for thesis evaluators and other first-time users of the
local UI Verifier web application. It explains what is available in a fresh
clone, how to inspect the benchmark, and how to create verification results.

## 1. What a Fresh Clone Contains

A fresh clone contains the application, the reviewed requirement annotations,
the verification benchmark for the 13 numbered Mind2Web flows, three curated
published Mind2Web verification-run sets, and the reviewed
PURE-derived annotations and aggregate exploratory summary. It does not contain
the following local artifacts:

- Mind2Web screenshots, which must be exported locally;
- additional generated verification runs, raw model responses, caches, and
  usage logs;
- uploaded user projects; or
- PURE source documents, screenshot flows, or per-flow verification runs.

Consequently, the flow list and reviewed benchmark become available after the
Mind2Web export. **Verification runs** then includes the three curated published
runs for each numbered Mind2Web flow. Installing PURE makes its original documents
available to the extraction scripts, but does not add PURE flows to the viewer;
the sidebar states this limitation. Locally generated runs are additional
reproducible outputs under `data/generated/`, which remains intentionally
ignored by Git.

## 2. Install and Start

Requirements:

- Python 3.12;
- Node.js 20.19+ or 22.12+; and
- an internet connection for the initial dependency and Mind2Web download.

From a parent directory:

```bash
git clone https://github.com/benno-tum/ui-requirement-verification.git
cd ui-requirement-verification

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[llm,data,dev]"

python scripts/export_mind2web.py --split test_task --max-flows 0 --allowed-flows-file data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt
```

Wait until the export reports `Exported flows: 13`. Then start the backend:

```bash
python -m uvicorn ui_verifier.api.main:app --reload
```

In a second terminal, from the same repository:

```bash
cd frontend
npm ci
npm run dev
```

Open:

- web application: <http://127.0.0.1:5173>;
- backend health check: <http://127.0.0.1:8000/health>; and
- interactive API documentation: <http://127.0.0.1:8000/docs>.

Do not paste the Markdown fence markers (three backticks) into the terminal.
Run the export and server commands separately.

## 3. Inspect the Existing Benchmark

1. Select one of the numbered flows in the left sidebar.
2. Use **Overview** to inspect the ordered screenshots, reviewed requirements,
   labels, evidence steps, uncertainty reasons, and flow metadata.
3. Use **Verification run** to create or inspect model predictions.

The workbench is also an annotation editor. An evaluator who only wants to
inspect the repository should avoid **Accept**, **Edit benchmark item**, and
other save actions. Generating a verification run does not change the reviewed
benchmark; it writes a separate local result under `data/generated/`.

## 4. Published and Local Verification Runs

Reviewed benchmark items and generated predictions are different artifacts:

- the reviewed reference is versioned under
  `data/annotations/verification_gold/`;
- the curated publishable predictions are versioned under `data/published/`;
- new pipeline predictions are created locally under `data/generated/`; and
- model-response caches and API-usage records are local as well.

The repository does not commit generated runs wholesale. The included run sets
were curated to exclude screenshots, source-page text, raw provider responses,
caches, secrets, personal local paths, and email-like task values. This keeps
the public repository compact while allowing evaluators to inspect real
predictions and bounding boxes immediately after exporting the source images.

To create a run, select a flow, open **Verification run**, configure **Run
pipeline**, and choose one of these modes:

### Offline diagnostic

Select **Lexical baseline (limited)** and click **Run lexical baseline**. This
mode requires no API key, but it cannot interpret screenshot pixels
semantically and is expected to abstain frequently.

### Visual verification

Copy the environment template and add a Gemini API key:

```bash
cp .env.example .env
```

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
```

Restart the backend after changing `.env`. In **Verification run**, select:

- **Visual verification (Gemini)**;
- a displayed Gemini screenshot-verifier model;
- **Lexical / OCR overlap** as a simple retriever;
- **verification benchmark** as the requirements source; and
- a positive Gemini API call limit.

Then click **Run visual verification**. The panel shows job status and recent
log lines. When the job completes, it appears under **Verification runs**. The
result view contains label distributions, reviewed-label comparison, claim
evidence, screenshot-step links, diagnostics, and bounding boxes when the run
returned localized regions.

Visual verification sends the selected screenshots and requirement content to
the configured model provider. Do not use private or confidential material
without authorization. The `.env` file, newly generated outputs, raw provider
responses, and caches remain local and must not be committed. Only the
explicitly curated artifacts under `data/published/` belong to the public
repository.

## 5. Verify Your Own Screenshots

Choose **New screenshot verification** or open
<http://127.0.0.1:5173/verify/new>.

1. Enter a project name and optional context.
2. Upload up to 20 PNG, JPEG, or WebP screenshots.
3. Arrange them in the order experienced by the user.
4. Enter one requirement per line, or attach a JSON, TXT, or Markdown file.
5. Select **Create verification workspace**. The page opens and focuses the
   newly created workspace below the form.
6. Configure and run either the offline lexical baseline or visual Gemini
   verification in that workspace.
7. Inspect requirement decisions, claims, evidence steps, and bounding boxes.

Uploaded screenshots are stored under `data/processed/flows/uploads/`.
Normalized uploaded requirements and generated runs stay under
`data/generated/`. Both locations are local working state.

## 6. Dataset and License Boundary

The absence of generated runs is not caused by a Mind2Web license failure. The
[official Mind2Web repository](https://github.com/OSU-NLP-Group/Mind2Web)
states that its dataset is licensed under CC BY 4.0 and separately asks users
not to redistribute unzipped test files online or include the benchmark in
training corpora. This repository therefore exports the selected screenshots on
the evaluator's machine instead of committing them.

The [PURE Zenodo record](https://zenodo.org/records/7118517) marks PURE 2.0 as
CC BY 4.0, so this repository publishes reviewed derived annotations and
aggregate evaluation results with attribution. The record also warns that its
curators did not verify the underlying rights of every collected Web document.
Raw PURE archives are therefore kept as separately attributed third-party data
rather than covered by the repository's MIT license. Install them directly from
Zenodo with:

```bash
python scripts/setup_external_requirement_data.py --dataset pure
```

The command verifies Zenodo checksums and extracts the files into the paths used
by the PURE workflows. It does not construct the thesis's curated PURE
screenshot flows or make PURE verification runs appear in the application. The
versioned aggregate result remains available at
`artifacts/thesis_evaluation/results/pure_exploratory_summary.json`.

See [Dataset Licensing and Release Policy](dataset_licensing_and_release_policy_2026-07-23.md)
and the root [NOTICE](../NOTICE.md) for the complete boundary.

## 7. Troubleshooting

### `pyproject.toml` or `scripts/export_mind2web.py` is missing

The shell is one directory above the clone. Run:

```bash
cd ui-requirement-verification
```

### The shell displays `bquote>`

Markdown backticks were pasted into the terminal. Press `Ctrl+C`, then paste
only the command text.

### The export shows a Pillow traceback after `^C`

The export was interrupted during PNG compression. Rerun the same command and
allow all 13 flows to finish; existing partial files are overwritten.

### The flow list is empty

Complete the Mind2Web export, confirm `Exported flows: 13`, and select
**Refresh flows**.

### Flows exist, but **Verification runs** is empty

Confirm that `data/published/verification_pipeline_runs/` exists in the clone,
restart the backend, and select **Refresh runs**. You can also start an offline
or visual run from the **Run pipeline** section.

### The frontend reports `Failed to fetch`

Confirm that the backend is still running on port 8000 and that
<http://127.0.0.1:8000/health> returns `{"status":"ok"}`. The default frontend
expects that address unless `VITE_API_BASE_URL` is set before `npm run dev`.

### Gemini produces fallbacks or no judgments

Check the verifier diagnostics and recent job logs. Confirm the API key, model,
quota, API-call limit, and retry settings. A fallback result must not be
interpreted as a successful Gemini judgment.
