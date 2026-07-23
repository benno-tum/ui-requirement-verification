# Repository Freeze Checklist

Status: pre-run cleanup checklist, 23 July 2026.

## Versioned core

- pipeline, evaluator, usage accounting, and aggregation code;
- Python tests and frontend source;
- `configs/thesis_final_experiments.json`;
- `configs/thesis_remaining_runs.json`;
- run orchestration and stability-analysis scripts;
- reviewed requirement annotations and explicitly retained audit judgments;
- thesis planning, evidence-audit, structure, and supervisor-review documents.

## Local or generated

- `.env` and API keys;
- `data/processed/` screenshots and exported flows;
- `data/generated/` calls, caches, intermediate outputs, and full raw traces;
- `output/` rendered local PDFs;
- the two July 21 generated bounding-box reference bundles containing absolute
  local image paths.

## Pre-run acceptance criteria

- `pytest -q` passes;
- `python -m compileall -q src scripts tests` passes;
- `npm run build` passes in `frontend/`;
- `git diff --check` passes;
- no secrets or absolute personal paths are staged;
- the committed experiment config and artifact source hashes match the intended
  run;
- regenerated preflight manifests report `git_dirty: false`;
- repetition output and cache directories do not exist before execution;
- stability runs are executed sequentially with explicit cost authorization.

## Post-run acceptance criteria

- 13 flow files and exactly 258 predictions per run;
- zero missing predictions, with failures and fallbacks reported separately;
- strict evaluator filter `^[0-9]{2}_` and full-coverage enforcement;
- raw responses, usage, provider, runtime, token, image, and cost metadata
  archived locally;
- three-run descriptive stability and pairwise label agreement generated;
- 3–5 qualitative examples and the RQ3 error taxonomy frozen;
- second-reviewer sample and adjudication recorded;
- release/licensing decision documented before copying selected artifacts into
  `artifacts/thesis_evaluation/`.
