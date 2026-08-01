# Script Entry Points

The repository retains historical experiment runners because they are part of
the provenance of earlier thesis results. New experiments should use the
frozen entry points below rather than copying an older wrapper.

## Current thesis entry points

- `run_verification_pipeline.py`: execute one configured flow.
- `run_thesis_final_experiments.py`: preflight and orchestrate the controlled
  Gemini matrix, stability repetitions, and optional oracle runs.
- `run_openrouter_qwen_baseline.py`: hosted Qwen open-weight baseline.
- `run_smolvlm_open_baseline.py`: local open-weight feasibility runner.
- `evaluate_verification_metrics.py`: strict label, evidence, and claim metrics.
- `analyze_thesis_final_matrix.py`: flow-cluster bootstrap and controlled
  contrasts.
- `analyze_thesis_run_stability.py`: descriptive three-run stability analysis.
- `analyze_chronology_ablation.py`: paired ordered-versus-order-unavailable
  analysis with deterministic per-flow permutations and flow-cluster
  bootstrap intervals.
- `run_abstention_policy_ablation.py`: zero-call aggregation counterfactual.
- `audit_thesis_replication_package.py`: release gate for secrets, personal
  paths, and artifact hashes.
- `prepare_single_author_thesis_audits.py`: prepare the complete
  reference-versus-deterministic-classifier UI-disagreement audit and the
  frozen 60-item V7 region quality audit. These are targeted qualitative and
  quality checks, not accuracy estimates or independent validation.
- `build_verification_second_review_sample.py`: deterministic blinded,
  label-stratified 44-item independent-review form. Retained as unused
  provenance after the evaluation was scoped to one annotator.
- `evaluate_verification_second_review.py`: completeness gate, agreement,
  Cohen's kappa, confusion matrix, and adjudication queue for the completed
  second review. Not part of the current single-author plan.

## Historical or specialized runners

- `run_joint_gemini31flashlite_allflows.py`: historical all-flow wrapper,
  superseded by the final experiment orchestrator.
- `run_realistic_topk4_no_claims_allflows.py`: historical raw/top-k wrapper,
  retained to reproduce the July 21 contextual run.
- `run_gemini25_omnimark_grounding.py` and related OmniParser scripts:
  exploratory region-grounding experiments, not final label-evaluation entry
  points.

Do not silently change a historical runner and reuse its old run identifier.
Create a new experiment ID, output directory, cache directory, and preflight
manifest whenever behavior or parameters change.

## Chronology-destroying order ablation

The matched order-unavailable experiment is configured as
`fl_raw_all_chronology_destroyed` in `configs/thesis_final_experiments.json`.
It uses the same model, requirements, screenshot set, chunking, prompt contract,
and aggregation as `fl_raw_all`. A fixed per-flow permutation replaces original
step identities with local apparent IDs, and the prompt explicitly states that
chronology is unavailable. Returned evidence IDs are mapped back to the original
flow steps before evaluation.

Prepare or execute it with:

```bash
python scripts/run_thesis_final_experiments.py \
  --experiments fl_raw_all_chronology_destroyed

python scripts/run_thesis_final_experiments.py \
  --experiments fl_raw_all_chronology_destroyed \
  --execute \
  --workers 1 \
  --cost-ceiling-usd 0.70
```

Analyze the paired result with:

```bash
python scripts/analyze_chronology_ablation.py
```

The analysis reports the full benchmark, multi-screen, multi-step-evidence,
lexically sequence-sensitive, and single-screen negative-control subsets. Its
flow-cluster bootstrap is descriptive because only 13 flows are available.
