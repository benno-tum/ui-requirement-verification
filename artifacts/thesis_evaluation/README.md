# Thesis Evaluation Replication Package

Status: structure prepared; final stability runs and release review are pending.

This directory is the intended versioned, curated replication package for the
Bachelor's thesis evaluation. `data/generated/` remains local working state and
must not be committed wholesale.

## Intended contents

- exact experiment configurations and preflight manifests;
- benchmark and source-file checksums;
- aggregate metrics, confidence intervals, and stability summaries;
- prompt templates and evaluation scripts;
- selected sanitized per-item predictions and raw responses where licensing
  and provider terms permit redistribution;
- a machine-readable artifact manifest with SHA-256 hashes.

## Excluded contents

- API keys, `.env`, authorization headers, billing identifiers, or account data;
- screenshots or other Mind2Web-derived media unless redistribution is
  explicitly permitted;
- absolute local home-directory paths containing a user name;
- unreviewed local bounding-box reference bundles;
- caches, virtual environments, frontend build output, and temporary PDFs.

## Release gate

Before any artifact is added here:

1. confirm the Mind2Web and PURE redistribution boundary with the supervisor;
2. replace absolute repository paths with repository-relative paths;
3. scan JSON and text files for secrets and personal data;
4. state the exact model identifier, provider, execution date, parameters,
   prompt version, benchmark hash, item coverage, failures, tokens, and cost;
5. verify every reported metric against the frozen 258-item Mind2Web gold set;
6. record whether an artifact is public, supervisor-only, or local-only.

Run the automated path and secret gate before committing:

```bash
python scripts/audit_thesis_replication_package.py --check-only
```

After the package is final, omit `--check-only` to write
`artifact_manifest.json` with file sizes and SHA-256 hashes.

Bounding boxes remain an exploratory implementation unless an independent
relevance and sufficiency review is completed. They must not be presented as a
validated thesis contribution merely because coordinates were generated.
