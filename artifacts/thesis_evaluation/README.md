# Thesis Evaluation Replication Package

Status: aggregate replication package prepared after the final stability runs;
classified as supervisor-only pending dataset permission and a repository code
license decision.

This directory is the intended versioned, curated replication package for the
Bachelor's thesis evaluation. `data/generated/` remains local working state and
must not be committed wholesale.

## Included contents

- exact experiment configurations under `configs/`;
- sanitized clean-commit launch manifests under `manifests/`; their
  `execution_requested` status records the state at launch, while
  `results/stability_execution_summary.json` records verified completion;
- aggregate metrics, the paired flow-cluster bootstrap, and the three-run
  stability summary under `results/`;
- `artifact_manifest.json` with file sizes, SHA-256 hashes, and a passed path
  and secret scan.

The executed source code, prompt templates, and evaluators correspond to commit
`cf243be2dd641e4b90e844eccbbe97bd0325f3c6`. Review and packaging tooling was
added afterward without changing those stored run outputs. Full per-item
predictions and raw provider responses remain local until redistribution is
approved.

## Excluded contents

- API keys, `.env`, authorization headers, billing identifiers, or account data;
- screenshots or other Mind2Web-derived media unless redistribution is
  explicitly permitted;
- absolute local home-directory paths containing a user name;
- unreviewed local bounding-box reference bundles;
- caches, virtual environments, frontend build output, and temporary PDFs.

## Release gate

Before publishing this package:

1. follow `DATASET_NOTICE.md` and `release_classification.json`;
2. obtain written permission before releasing per-item Mind2Web test
   derivatives or PURE text/figure derivatives;
3. replace absolute repository paths with repository-relative paths;
4. scan JSON and text files for secrets and personal data;
5. state the exact model identifier, provider, execution date, parameters,
   prompt version, benchmark hash, item coverage, failures, tokens, and cost;
6. verify every reported metric against the frozen 258-item Mind2Web gold set;
7. build a separate public artifact from an explicit allowlist instead of
   publishing this supervisor package wholesale.

Run the automated path and secret gate before committing:

```bash
python scripts/audit_thesis_replication_package.py --check-only
```

After the package is final, omit `--check-only` to write
`artifact_manifest.json` with file sizes and SHA-256 hashes.

Bounding boxes remain an exploratory implementation unless an independent
relevance and sufficiency review is completed. They must not be presented as a
validated thesis contribution merely because coordinates were generated.
