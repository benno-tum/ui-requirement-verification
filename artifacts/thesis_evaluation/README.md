# Thesis Evaluation Replication Package

Status: public aggregate replication package prepared after the final stability
runs. The repository uses an MIT license for original software and follows the
Mind2Web attribution and source-file redistribution boundary in
`DATASET_NOTICE.md`.

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
predictions and raw provider responses remain local. Three separate sanitized
per-item run sets are published under `data/published/`.

## Excluded contents

- API keys, `.env`, authorization headers, billing identifiers, or account data;
- screenshots or other Mind2Web-derived media unless redistribution is
  explicitly permitted;
- absolute local home-directory paths containing a user name;
- unreviewed local bounding-box reference bundles;
- original PURE archives and extracted document figures;
- caches, virtual environments, frontend build output, and temporary PDFs.

## Release controls

When updating this package:

1. follow `DATASET_NOTICE.md` and `release_classification.json`;
2. do not add Mind2Web source files; retain CC BY 4.0 attribution, change
   identification, and the curator provenance caveat for PURE-derived material;
3. replace absolute repository paths with repository-relative paths;
4. scan JSON and text files for secrets and personal data;
5. state the exact model identifier, provider, execution date, parameters,
   prompt version, benchmark hash, item coverage, failures, tokens, and cost;
6. verify every reported metric against the frozen 258-item Mind2Web gold set;
7. verify PURE summaries against the two versioned reviewed gold files;
8. continue using an explicit allowlist instead of copying local generated
   directories wholesale.

Run the automated path and secret gate before committing:

```bash
python scripts/audit_thesis_replication_package.py --check-only
```

After the package is final, omit `--check-only` to write
`artifact_manifest.json` with file sizes and SHA-256 hashes.

Bounding boxes remain an exploratory implementation unless an independent
relevance and sufficiency review is completed. They must not be presented as a
validated thesis contribution merely because coordinates were generated.
