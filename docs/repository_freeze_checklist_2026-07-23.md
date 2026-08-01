# Repository Freeze Checklist

Status: stability runs completed; single-author audits and release decisions
remain. The evaluation was rescoped on 25 July 2026 without an independent
second reviewer.

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

- [x] 13 flow files and exactly 258 predictions per stability run;
- [x] zero missing predictions, with failures and fallbacks reported separately;
- [x] strict evaluator filter `^[0-9]{2}_` and full-coverage enforcement;
- [x] raw responses, usage, provider, runtime, token, image, and cost metadata
  archived locally;
- [x] three-run descriptive stability and pairwise label agreement generated;
- [x] five qualitative examples and the RQ3 error taxonomy frozen;
- [x] blinded, stratified second-review form prepared;
- [x] second-review form retained as unused provenance; no independent-review
  or inter-rater-agreement claim will be made;
- [x] all 81 UI-evaluability reference-versus-classifier disagreements reviewed
  as a targeted qualitative audit; no accuracy or agreement estimate derived
  from the selected cases;
- [x] author-conducted V7 region-grounding quality audit completed;
- [x] conservative Mind2Web/PURE release boundary and dataset notice documented;
- [ ] written permission obtained for any per-item derived-data release;
- [ ] repository code license selected before calling the code open source.
