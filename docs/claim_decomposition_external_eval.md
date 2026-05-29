# External Claim Decomposition Evaluation

Use `scripts/evaluate_claim_decomposition_external.py` to evaluate the rule-based claim decomposer on external requirement sources. The script is safe to run on broad directories: malformed files are skipped by default, output JSON is always written for valid directory inputs, and a diagnostics sidecar is written next to the output.

The commands below are written to run from this `docs/` directory, because markdown terminals in this setup open there. They use `../scripts`, `../src`, and `../data` paths.

## External Data Setup

PURE is already present in this repository under `../data/raw/pure`.

PROMISE+ and user-story datasets are not committed. Download public external datasets with:

```bash
python ../scripts/setup_external_requirement_data.py --dataset all
```

This creates:

```text
../data/external/promise_exp/PROMISE_exp.arff
../data/external/user_stories/neodataset_issues.csv
../data/external/source_manifest.json
```

The PROMISE download is `PROMISE_exp`, a public expanded PROMISE ARFF dataset. It is not the missing `Promise+.arff` file.

## PURE

Prefer raw PURE XML files:

```bash
PYTHONPATH=../src python ../scripts/evaluate_claim_decomposition_external.py \
  --input ../data/raw/pure \
  --source-kind pure \
  --out ../data/generated/claim_decomposition_checks/external_pure_decomp.json \
  --limit 300
```

If the raw PURE path is unknown:

```bash
find ../data -iname "*.xml" | grep -i pure
```

## PROMISE / PROMISE_exp

```bash
PYTHONPATH=../src python ../scripts/evaluate_claim_decomposition_external.py \
  --input ../data/external/promise_exp/PROMISE_exp.arff \
  --source-kind promise \
  --out ../data/generated/claim_decomposition_checks/external_promise_exp_decomp.json \
  --limit 500
```

If the file is missing, the script exits clearly with:

```text
Input file does not exist: ../data/external/promise_exp/PROMISE_exp.arff
```

## User Stories

```bash
PYTHONPATH=../src python ../scripts/evaluate_claim_decomposition_external.py \
  --input ../data/external/user_stories \
  --source-kind user_stories \
  --out ../data/generated/claim_decomposition_checks/external_user_stories_decomp.json \
  --limit 500
```

## Broad Scan

Use broad scans for diagnostics, not final benchmark numbers:

```bash
PYTHONPATH=../src python ../scripts/evaluate_claim_decomposition_external.py \
  --input ../data \
  --out ../data/generated/claim_decomposition_checks/broad_scan_decomp.json \
  --limit 300
```

You can narrow or expand scanning:

```bash
PYTHONPATH=../src python ../scripts/evaluate_claim_decomposition_external.py \
  --input ../data \
  --include-glob "../data/raw/pure/**/*.xml" \
  --include-glob "../data/external/**/*.arff" \
  --include-glob "../data/external/**/*.csv" \
  --exclude-glob "../data/generated/**" \
  --out ../data/generated/claim_decomposition_checks/external_decomp.json
```

For an output path like:

```text
../data/generated/claim_decomposition_checks/external_pure_decomp.json
```

the diagnostics file is:

```text
../data/generated/claim_decomposition_checks/external_pure_decomp.diagnostics.json
```

Diagnostics include candidate files, parsed files, skipped files with exception types, extraction counts by source file, item counts before and after deduplication, and flag counts.
