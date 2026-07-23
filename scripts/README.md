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
- `run_abstention_policy_ablation.py`: zero-call aggregation counterfactual.
- `audit_thesis_replication_package.py`: release gate for secrets, personal
  paths, and artifact hashes.

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
