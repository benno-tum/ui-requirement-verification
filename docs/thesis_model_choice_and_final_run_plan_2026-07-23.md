# Model Choice and Final Run Plan

Status: prepared for review on 23 July 2026. No paid calls are triggered by the preparation command.

The frozen research questions for this run plan are:

1. **RQ1:** How accurately can multimodal models apply a provided, application-specific verification label schema to UI-observable textual requirements using ordered screenshot flows?
2. **RQ2:** How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?
3. **RQ3:** Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?

## 1. Applicable guidance

The Chair of Software Engineering describes empirical validation as a central part of its research approach. The more specific reporting standard is the living **LLM Guidelines for SE**, co-authored by Prof. Stefan Wagner:

- Model-version guideline: <https://llm-guidelines.org/guidelines/model-version/>
- Reporting checklist: <https://llm-guidelines.org/checklist/>
- Open-model baseline guideline: <https://llm-guidelines.org/guidelines/open-llm/>
- Peer-reviewed guideline paper: Baltes et al., *Guidelines for Empirical Studies in Software Engineering involving Large Language Models*, accepted in *Empirical Software Engineering*, arXiv:2508.15503.

For this thesis the relevant checklist items are:

1. report the exact model and version;
2. report execution date and every configured parameter, including defaults that affect outputs;
3. explain the model and version choice;
4. archive prompts, outputs, runtime traces, benchmark identifiers, and available checksums;
5. acknowledge the reproducibility limits of commercial APIs;
6. use an open LLM baseline where technically feasible, or justify its omission;
7. include non-LLM baselines, human validation, suitable metrics, and limitations.

The public chair pages do not expose a separate formal pass/fail rule for model selection. The checklist above is therefore treated as the concrete methodological standard because it contains the requested model-choice instructions and Prof. Wagner is a co-author.

## 2. Selected models

### Low-cost comparison: Gemini 2.5 Flash-Lite

`gemini-2.5-flash-lite` is the second model required for the RQ1 plural-model comparison. It is a stable multimodal model, supports image input and structured output, and Google positions it for high-volume classification and extraction. Its standard price is USD 0.10 per million input tokens and USD 0.40 per million output tokens. The run uses an explicit thinking budget of zero because Gemini 2.5 exposes token budgets rather than Gemini 3 thinking levels. It uses the same raw-requirement, all-screenshot configuration as the primary model. To avoid structurally incomplete responses on 20-plus-requirement flows, requests are deterministically chunked to at most eight requirements while every chunk still receives the complete ordered screenshot flow.

This is compliant with the model-choice guideline when presented as a deliberately economical classification baseline rather than as a current frontier model. Choosing a cheaper stable model is permissible; the thesis must state the monetary and methodological rationale and must not imply that it represents the strongest available multimodal capability.

Official model documentation: <https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite>

### Primary model: Gemini 3.1 Flash-Lite

`gemini-3.1-flash-lite` is the primary model for the complete controlled matrix.

Reasons:

- It is a stable generally available model rather than a preview alias.
- Google documents text and image input, structured output, thinking support, and a 1,048,576-token input limit.
- It is explicitly positioned as a low-cost, high-throughput multimodal model.
- The current repository already completed the full 13-flow benchmark with this exact model, prompt family, structured parsing, usage logging, and no fallback.
- Keeping one model fixed across the main matrix prevents model strength from being confounded with claim policy or screenshot selection.
- The measured full runs cost approximately USD 0.48 for all screenshots with provided claims and USD 0.56 for raw requirements with top-4 retrieval under the previous grouping configuration.

Official model documentation: <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>

### Strong-model sensitivity check: Gemini 3.6 Flash

`gemini-3.6-flash` is used only for two anchor configurations: raw whole-flow verification and the proposed gated-decomposition/top-4 pipeline.

Reasons:

- It is the current stable higher-capability Flash model, updated in July 2026.
- Google documents multimodal inputs, structured outputs, thinking, a 1,048,576-token input limit, and particular strength in spatial reasoning.
- Two matched anchor runs test whether the central conclusion depends on the inexpensive primary model without paying for every ablation cell twice.
- It uses the same Gemini API adapter and output schema as the primary model.

Official model documentation: <https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash>

### Historical reference only: Gemini 3.1 Pro Preview

The existing `gemini-3.1-pro-preview` run remains preliminary evidence, not part of the final controlled matrix. It is a preview model, and its existing configuration differs from the later Flash-Lite runs in more than model identity. Repeating the complete matrix with it would add cost without resolving the central pipeline-factor questions.

### Open-weight baseline: hosted run completed

The LLM Guidelines recommend an open model when commercial models are central. A local `HuggingFaceTB/SmolVLM2-2.2B-Instruct` adapter and a hosted `Qwen/Qwen3-VL-8B-Instruct` adapter are implemented. The hosted Qwen run completed on the full benchmark on 23 July 2026.

The local pilot used the M1 Pro GPU, FP16 weights without quantization, four shared screenshots resized through the model processor to a 768-pixel longest edge, greedy decoding, and a capped 128-token response. One group required 323 seconds and the truncated output did not contain a complete parseable decision for its eight claims. Extrapolating to the output length required for 39 groups makes a local full run impractical on this machine. The failed timing output is not benchmark evidence.

The selected hosted model is `Qwen/Qwen3-VL-8B-Instruct`, released under Apache 2.0. It supports multi-image input, OCR, GUI understanding, and structured multimodal reasoning. The OpenRouter run:

- reuses the frozen Gemini raw/top-4 group and screenshot selection but never reads Gemini predictions into the prompt;
- resizes local screenshots to a documented maximum edge before base64 transport;
- requests the same conservative label semantics, step evidence, and UI-evaluability judgment;
- disables provider fallbacks and providers that cannot honor the requested parameters;
- archives raw responses, returned provider, token usage, cost, preprocessing, prompt version, and source hashes;
- intentionally omits bounding-box generation.

The run produced all 258 predictions in 39 first-attempt calls with no fallback or parsing failure. OpenRouter returned Alibaba as the provider. Hosted open-weight inference is more reproducible than a closed-weight-only comparison but weaker than self-hosting because the provider's serving stack and quantization are not exposed. This limitation must remain explicit.

## 3. Frozen controlled matrix

All main LLM cells use temperature 0, preferred-original screenshots, lexical retrieval, top-k 4, the same supplied four-label schema, model-predicted UI evaluability, no candidate-mark grounding, no LLM decomposition fallback, and the same deterministic label aggregation. Gemini 3 models use thinking level `low`; Gemini 2.5 uses the explicitly recorded thinking budget `0`. Missing outputs are coverage failures and are never reinterpreted as `ABSTAIN`.

| ID | Tier | Model | Claims | Screenshots | Purpose |
|---|---|---|---|---|---|
| `det_raw` | core | deterministic | raw | lexical top-4 | Non-LLM baseline |
| `det_gated` | core | deterministic | gated automatic | lexical top-4 | Zero-cost decomposition baseline |
| `fl_raw_all` | core | 3.1 Flash-Lite | raw | all | Whole-flow baseline |
| `fl_gated_all` | core | 3.1 Flash-Lite | gated automatic | all | Decomposition effect with fixed evidence |
| `fl_raw_top4` | core | 3.1 Flash-Lite | raw | lexical top-4 | Retrieval effect without decomposition |
| `fl_gated_top4` | core | 3.1 Flash-Lite | gated automatic | lexical top-4 | Proposed evidence-first configuration |
| `g25_raw_all` | core | 2.5 Flash-Lite | raw | all | Low-cost second model for RQ1 |
| `fl_oracle_all` | extended | 3.1 Flash-Lite | reviewed/oracle | all | Claim-quality upper bound |
| `fl_oracle_top4` | extended | 3.1 Flash-Lite | reviewed/oracle | lexical top-4 | Claim upper bound under restricted evidence |
| `g36_raw_all` | extended | 3.6 Flash | raw | all | Strong-model whole-flow anchor |
| `g36_gated_top4` | extended | 3.6 Flash | gated automatic | lexical top-4 | Strong-model pipeline anchor |

The gated policy currently yields 281 claims from 258 requirements and decomposes 31 requirements; the provided-claim condition contains 541 reviewed claims. Provided claims must be described as an oracle condition, not automatic decomposition.

## 4. Token and cost estimate

Prices checked on 23 July 2026:

- Gemini 2.5 Flash-Lite standard: USD 0.10 per million input tokens and USD 0.40 per million output tokens, including thinking tokens.
- Gemini 3.1 Flash-Lite standard: USD 0.25 per million input tokens and USD 1.50 per million output tokens, including thinking tokens.
- Gemini 3.6 Flash standard: USD 1.50 per million input tokens and USD 7.50 per million output tokens, including thinking tokens.

Official pricing: <https://ai.google.dev/gemini-api/docs/pricing>

The estimates are ranges extrapolated from the repository's completed 258-item runs. Exact image-token accounting is model-dependent, and top-4 batching repeats screenshots across calls.

| Run set | Estimated total tokens | Estimated cost |
|---|---:|---:|
| RQ-sufficient core tier | 6.9M–9.9M | USD 2.13–3.09 |
| Optional oracle and Gemini 3.6 extensions | 8.7M–12.3M additional | USD 7.78–11.21 additional |
| Deterministic baseline | 0 hosted tokens | USD 0 |
| Complete prepared package | 15.5M–22.2M | USD 9.92–14.30 |

For the core tier, a 30% planning reserve is approximately **USD 4.02**. The corresponding reserve for every optional run is approximately **USD 18.60**. These are planning reserves, not guaranteed hard billing ceilings. Provider-side image tokenization, billable failed attempts, retry behavior, and model changes can still move actual billing outside the estimate. Runs should therefore be executed sequentially, usage should be checked after every flow, and the next flow should not start once the approved budget is approached.

The estimates use standard synchronous API prices. Google's Batch API is cheaper, but the current runner uses synchronous calls and therefore must not claim Batch pricing.

## 5. How to prepare and execute

Preparation only, no API calls:

```bash
python scripts/run_thesis_final_experiments.py
```

Primary matrix only:

```bash
python scripts/run_thesis_final_experiments.py --groups primary
```

RQ-sufficient core tier only:

```bash
python scripts/run_thesis_final_experiments.py --tiers core
```

Execute one experiment after reviewing its manifest:

```bash
python scripts/run_thesis_final_experiments.py \
  --experiments fl_raw_all \
  --execute \
  --workers 1 \
  --cost-ceiling-usd 0.60
```

The generated preflight manifest contains the three RQs, the supplied label schema, 13 gold-file hashes, hashes of prompt and pipeline source files, exact commands, selected configurations, expected counts, environment versions, and cost bands. Paid execution is rejected unless `--execute` and a sufficient `--cost-ceiling-usd` are both supplied. This argument is currently an authorization guard against accidentally starting a larger selection; it must not be described as a provider-side billing cap.

## 6. Research-question coverage and remaining preparation

- **RQ1:** the matched Gemini 2.5 Flash-Lite and Gemini 3.1 Flash-Lite raw/all configurations supply the completed two-model comparison. Report per-label precision/recall/F1, confusion matrices, false fulfillment, inter-model agreement, and confidence intervals. Both are commercial Google models, so this sensitivity check does not replace the recommended open-model baseline. The experiment assesses one supplied schema; it must not be generalized to arbitrary unseen label schemas.
- **RQ2:** the raw/gated-claim by all/top-4 Flash-Lite cells form the primary controlled 2x2 comparison. The provided-claim cells are oracle upper bounds and must not be presented as automatic decomposition.
- **RQ3:** use a predefined taxonomy, frozen cases, category counts, abstention reasons, and unsafe-`FULFILLED` analysis. No forced-decision experiment is required, because the question is diagnostic rather than causal.

An additional **offline abstention-policy ablation** is nevertheless prepared because it strengthens RQ3. It applies the native aggregation and a forced closed-world evidence policy to the same frozen claim outputs from `fl_raw_all` and `fl_gated_top4`. This adds no model calls or tokens. The forced policy maps supported evidence to `FULFILLED`, partial visible support to `PARTIALLY_FULFILLED`, contradictions to `NOT_FULFILLED`, and otherwise treats missing support as `NOT_FULFILLED`. It must be described as an aggregation-policy counterfactual, not as a separate LLM prediction. Report the resulting coverage/error trade-off and the types of native abstentions converted into incorrect negative or positive decisions.

```bash
python scripts/run_abstention_policy_ablation.py \
  --source-dir data/generated/thesis_final_experiments/fl_raw_all \
  --output-dir data/generated/thesis_final_experiments/fl_raw_all_forced_decision
```

The following preparation remains:

1. freeze and commit the code, benchmark hashes, completed outputs, metrics, and bootstrap artifact;
2. freeze the completed hosted open-weight outputs, provider metadata, metrics, and agreement analysis;
3. execute the prepared `r2` and `r3` repetitions of the two central Flash-Lite anchor configurations and the inexpensive Qwen baseline after the repository is frozen, because temperature 0 does not guarantee determinism;
4. freeze the RQ3 error taxonomy before coding and counting final-run errors;
5. add the statistical-method citation and report the limitation of having only 13 flow clusters.

Ordered-versus-shuffled screenshots and abstention-versus-forced-decision are no longer required by the final RQs. They should only be added as optional robustness experiments, and no causal claim about ordering or abstention should be made without them.

## 7. Reporting-rule compliance

Implemented in the run package:

- exact API model identifiers and model roles;
- execution date, configured generation parameters, prompt-reuse policy, and zero-shot status;
- prompt/pipeline artifact hashes, config hash, gold hashes, Git commit and dirty status, Python and SDK versions;
- archived structured outputs, raw model responses, usage metadata, errors, and coverage;
- fixed label contract and explicit separation of `ABSTAIN` from missing predictions;
- model-choice rationale, deterministic non-LLM baseline, two-model sensitivity comparison, and commercial-API reproducibility limitation.

Not yet fully satisfied:

- independent human validation or second-reviewer agreement on a representative benchmark sample;
- a clean committed repository state for the final executions;
- repeated-run stability, a statistical-method citation, and the frozen RQ3 coding protocol.

## 8. Completed controlled Gemini 3.1 Flash-Lite matrix

The primary 2x2 RQ2 matrix completed on 23 July 2026 over the same 13 flows and 258 accepted Mind2Web verification items. Every cell used `gemini-3.1-flash-lite`, temperature 0, thinking level `low`, the same prompt version and aggregation policy, full prediction coverage, and at most eight claims per call. The cells differ only in claim policy (`raw` or gated automatic decomposition) and screenshot policy (complete flow or lexical top-4). Across all four cells, 160 API calls completed without a recorded fallback or failure.

| Configuration | Items | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR | Recall@1 | Recall@3 | Calls | Tokens | Est. cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Raw requirements, all screenshots | 258 | 79.5% | 0.514 | 10.6% | 19.0% | 0.716 | 0.401 | 0.475 | 39 | 612,429 | $0.2817 |
| Gated automatic decomposition, all screenshots | 258 | 79.1% | 0.536 | 12.4% | 17.1% | 0.734 | 0.414 | 0.493 | 41 | 653,388 | $0.3002 |
| Raw requirements, lexical top-4 | 258 | 71.3% | 0.387 | 11.0% | 27.9% | 0.621 | 0.334 | 0.378 | 39 | 433,519 | $0.2778 |
| Gated automatic decomposition, lexical top-4 | 258 | 73.6% | 0.518 | 10.4% | 26.0% | 0.607 | 0.317 | 0.375 | 41 | 421,723 | $0.2394 |

The controlled result does not support a simple claim that either automatic decomposition or top-4 selection is uniformly better. A paired 10,000-sample percentile bootstrap that resamples the 13 complete flows gives the following 95% intervals. With all screenshots fixed, gated decomposition changes accuracy by -0.4 percentage points (95% CI -3.7 to +2.2) and macro-F1 by +0.022 (-0.075 to +0.109); neither interval excludes zero. Its false-fulfillment difference is +1.9 percentage points (+0.4 to +3.3). With raw requirements fixed, top-4 selection reduces accuracy by 8.1 percentage points (-12.0 to -3.8), macro-F1 by 0.127 (-0.244 to -0.043), and evidence MRR by 0.095 (-0.148 to -0.031) while saving only about $0.004. Under top-4 evidence, gated decomposition improves accuracy by 2.3 percentage points (0.0 to +4.9) and macro-F1 by 0.131 (+0.021 to +0.193), although its MRR difference of -0.015 has an interval spanning zero. With only 13 clusters, these intervals still warrant cautious interpretation.

The four cells cost approximately $1.0991 in total based on recorded successful-call token usage. Together with the valid Gemini 2.5 baseline below, the completed paid package cost approximately $1.1701. Provider billing for earlier invalid smoke attempts is not contained in these successful-run totals.

The offline forced-decision counterfactual was also applied to two prespecified Gemini 3.1 outputs. Replacing all 49 native abstentions in `fl_raw_all` with `NOT_FULFILLED` reduced accuracy from 79.5% to 70.2% and macro-F1 from 0.514 to 0.331. Replacing all 67 abstentions in `fl_gated_top4` reduced accuracy from 73.6% to 64.3% and macro-F1 from 0.518 to 0.305. False fulfillment stayed at 10.6% and 10.4%, respectively, because this counterfactual never creates a positive prediction. It therefore shows that blanket closed-world replacement is harmful; it does not establish causal safety benefits or calibration of every native abstention.

## 9. Completed low-cost model baseline

The final chunked `gemini-2.5-flash-lite` whole-flow baseline completed on 23 July 2026 with 13/13 flows, 258/258 predictions, 39 successful API calls, zero fallbacks, and zero recorded failures. Every call used temperature 0, thinking budget 0, at most eight requirements, and the complete ordered screenshot flow. Recorded successful-call usage was 253,958 input tokens, 114,135 output tokens, 45 thinking tokens, and 368,138 total tokens, for approximately USD 0.0711. Earlier structurally incomplete attempts are not part of the result and their provider billing is not included in this recorded successful-call total.

| Items | Accuracy | Macro-F1 | False fulfillment | Abstain rate | Evidence MRR |
|---:|---:|---:|---:|---:|---:|
| 258 | 73.3% | 0.412 | 13.7% | 22.1% | 0.595 |

Against the matched Gemini 3.1 Flash-Lite raw/all cell, Gemini 2.5 is 6.2 percentage points lower in accuracy (paired flow-cluster bootstrap 95% CI 1.6 to 10.8), 0.102 lower in macro-F1 (0.006 to 0.218), and 0.121 lower in evidence MRR (0.010 to 0.241). The two models agree on 83.3% of item labels (95% CI 78.5% to 88.1%); Cohen's kappa is 0.616 (0.469 to 0.735). This supplies a low-cost model-sensitivity result for RQ1, while remaining limited to two commercial models from one provider.

The offline forced-decision counterfactual converted all 57 native abstentions to `NOT_FULFILLED`. Accuracy fell to 66.7% and macro-F1 to 0.332; false fulfillment remained 13.7%. This shows that a blanket closed-world replacement of abstention with negative decisions is harmful, but it does not by itself establish that every individual abstention is well calibrated.

## 10. Completed hosted open-weight baseline

The `qwen/qwen3-vl-8b-instruct` baseline completed through OpenRouter on 23 July 2026. OpenRouter returned Alibaba as the provider for every call. The run reused the frozen raw/shared-top-4 groups, resized screenshots to a 1,600-pixel longest edge, used temperature 0 and JSON mode, disabled provider fallbacks, and did not request bounding boxes. It produced all 258 predictions in 39 first-attempt calls with no recorded failure or fallback. Usage was 255,185 prompt tokens and 24,981 completion tokens; recorded inference cost was USD 0.041223.

| Items | Accuracy | Macro-F1 | False fulfillment | Abstain rate | Evidence MRR |
|---:|---:|---:|---:|---:|---:|
| 258 | 71.3% | 0.356 | 18.5% | 23.3% | 0.622 |

The matched Gemini 3.1 Flash-Lite raw/shared-top-4 condition also reaches 71.3% accuracy. The paired flow-cluster bootstrap estimates an accuracy difference of 0.0 percentage points (95% CI -3.4 to +3.4) and an evidence-MRR difference of +0.001 (-0.038 to +0.038). Qwen's macro-F1 is 0.030 lower (-0.068 to +0.007), while its false-fulfillment rate is 7.4 percentage points higher (+2.5 to +12.6). The models agree on 81.0% of labels (75.7% to 86.7%); Cohen's kappa is 0.559 (0.444 to 0.683).

This satisfies the practical open-weight comparison recommendation but not the stronger ideal of independent local reproducibility. The Qwen weights are Apache-2.0, while the hosted provider's quantization and serving stack remain opaque. The local SmolVLM timing artifact remains excluded from benchmark results.

### Prepared stability and oracle package

`configs/thesis_remaining_runs.json` defines six core stability runs and two optional oracle diagnostics. Every repetition uses a distinct output and verifier-cache directory. The package intentionally excludes Gemini 3.6, shuffled-order, bounding-box, and new abstention calls.

Preflight only, with no API calls:

```bash
python scripts/run_thesis_final_experiments.py \
  --config configs/thesis_remaining_runs.json \
  --tiers core \
  --manifest-out data/generated/thesis_final_experiments/stability_preflight_manifest.json
```

The conservative preflight estimate for all six stability runs is USD 0.98–1.48. Split estimates are USD 0.90–1.38 for four Gemini repetitions and USD 0.07–0.10 for two Qwen repetitions. Based on recorded prior runs, actual cost is expected to be lower, but only the conservative bounds should authorize execution.

After committing and confirming that the regenerated manifest records `git_dirty: false`, execute sequentially:

```bash
python scripts/run_thesis_final_experiments.py \
  --config configs/thesis_remaining_runs.json \
  --groups stability_gemini \
  --workers 1 \
  --execute \
  --cost-ceiling-usd 1.80

python scripts/run_thesis_final_experiments.py \
  --config configs/thesis_remaining_runs.json \
  --groups stability_open_weight \
  --workers 1 \
  --execute \
  --cost-ceiling-usd 0.14
```

The cost-ceiling argument is an authorization check, not a provider-side hard cap. Do not add `--force` to completed repetition directories: a replacement could reuse their local cache and would no longer be a clean independent execution. Use a new repetition ID instead.

After all six repetitions pass strict 258-item coverage, generate the descriptive stability artifact:

```bash
python scripts/analyze_thesis_run_stability.py
```

This reports every run separately, the mean, sample standard deviation and range of each metric, and all pairwise label agreements. It explicitly does not treat three executions over the same benchmark as independent benchmark samples.

The optional reviewed-claim oracle pair is prepared separately:

```bash
python scripts/run_thesis_final_experiments.py \
  --config configs/thesis_remaining_runs.json \
  --groups oracle_optional \
  --manifest-out data/generated/thesis_final_experiments/oracle_preflight_manifest.json
```

Its conservative estimate is USD 1.67–2.44 before retry reserve. It should be executed only after the stability runs and only if the remaining budget and thesis schedule justify the additional upper-bound analysis.

## 11. Completed deterministic sanity checks

The deterministic configurations are technical and non-LLM sanity checks. They are not the primary model baseline requested by the reporting guidance and should not receive headline emphasis in the thesis.

The two deterministic 258-item baselines were executed on 23 July 2026 with full prediction coverage and an explicit Mind2Web-only evaluator filter. They are preliminary until the dirty worktree is committed and the manifest is regenerated.

| Configuration | Items | Accuracy | Macro-F1 | False fulfillment | Abstain rate | Evidence MRR |
|---|---:|---:|---:|---:|---:|---:|
| Deterministic raw requirements, lexical top-4 | 258 | 44.6% | 0.293 | 33.3% | 10.1% | 0.467 |
| Deterministic gated decomposition, lexical top-4 | 258 | 45.3% | 0.301 | 32.8% | 9.7% | 0.464 |

Gated decomposition therefore changes this baseline only marginally: +0.8 percentage points accuracy, +0.008 macro-F1, and -0.5 percentage points false fulfillment. Neither deterministic configuration predicts any of the eight `NOT_FULFILLED` items correctly.

The forced-decision smoke test converted all 26 raw-baseline abstentions and all 25 gated-baseline abstentions to `NOT_FULFILLED`. Accuracy fell from 44.6% to 41.1% for raw requirements and from 45.3% to 41.9% for gated decomposition; macro-F1 fell to 0.229 and 0.237. False fulfillment stayed unchanged because this forced policy never converts an abstention into `FULFILLED`. This validates the offline ablation mechanics. The corresponding LLM counterfactuals are reported in Section 8 and lead to the same qualitative conclusion: forcing every uncertain case to a negative label harms label quality and does not change false fulfillment under this particular policy.
