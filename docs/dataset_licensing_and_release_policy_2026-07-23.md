# Dataset Licensing and Release Policy

Status: release decision based on official source information, 23 July 2026,
updated 3 August 2026 after supervisor confirmation of the Mind2Web approach
and verification of PURE's Zenodo license metadata. This is a research-artifact
policy, not legal advice.

## Decision

- the repository may publish source code, experiment configurations, aggregate
  metrics, statistical summaries, and documentation created by the thesis
  author;
- the aggregate thesis replication package and the explicitly curated
  Mind2Web-derived run set may be published with attribution;
- Mind2Web screenshots, HTML, MHTML, HAR files, videos, traces, `task.json`,
  `steps.json`, complete test records, raw per-item prompts, and raw provider
  responses are not published;
- PURE-derived requirements, annotations, and evaluation results may be
  published under the dataset record's CC BY 4.0 terms with attribution and an
  indication of changes;
- PURE source archives may be downloaded and used through the documented setup
  command; they remain outside the repository's MIT license and are not
  duplicated in Git by default;
- curated per-item predictions must exclude source-page text and must not
  enable reconstruction of screenshots or complete test records;
- no release is described as training data, and Mind2Web test-derived material
  must not be placed in a training corpus.

## 1. Mind2Web

### Official information

The official Mind2Web repository states:

- the dataset is licensed under Creative Commons Attribution 4.0 International;
- repository code is MIT-licensed;
- the test splits are distributed separately to reduce benchmark
  contamination;
- users should not redistribute the unzipped test files online;
- benchmark data should not appear in training corpora.

Sources:

- <https://github.com/OSU-NLP-Group/Mind2Web>
- <https://creativecommons.org/licenses/by/4.0/>

CC BY 4.0 normally permits sharing and adaptation with attribution, a license
link, and an indication of changes. It does not guarantee that every embedded
third-party element is free of other rights, including privacy, publicity, or
trademark restrictions. The separate test-split redistribution instruction also
creates a practical benchmark-governance constraint even if a broad reading of
CC BY might permit more.

### Repository-specific finding

All 13 thesis flows record `"split": "test_task"` in their local `task.json`
metadata. They are not training-set examples.

The public GitHub repository contains author-created requirement and
verification annotation files keyed by selected test annotation identifiers.
It does not contain local screenshots, raw test records, or processed flow
files. Following supervisor confirmation of the Mind2Web licensing approach,
these derived annotations and explicitly sanitized prediction artifacts are
published with attribution under the boundary described here. This does not
authorize redistribution of the source test files.

### Required attribution

> This work uses and adapts the Mind2Web dataset by Deng et al., licensed under
> CC BY 4.0. Changes include selection of 13 `test_task` trajectories,
> author-created UI requirements, verification labels, claim annotations, and
> aggregate evaluation artifacts. The Mind2Web authors do not endorse this
> derivative work. Original dataset:
> <https://github.com/OSU-NLP-Group/Mind2Web>. License:
> <https://creativecommons.org/licenses/by/4.0/>.

The thesis must also cite:

> Xiang Deng, Yu Gu, Boyuan Zheng, Shijie Chen, Samuel Stevens, Boshi Wang,
> Huan Sun, and Yu Su. “Mind2Web: Towards a Generalist Agent for the Web.”
> NeurIPS 2023.

## 2. PURE

### Official information

The current Zenodo record for PURE describes 79 public requirements documents
collected from the Web. Its API metadata assigns the deposited dataset
`CC-BY-4.0`. That license permits sharing and adaptation for any purpose when
appropriate credit, a license link, and an indication of changes are supplied.

The same record states that the curators are not aware of the license agreements
or intellectual-property rights governing the original Web requirements and
provides a takedown contact for possible claims. This is a material provenance
and warranty caveat. It should be preserved in downstream notices, but the
repository should not misstate the deposited dataset as unlicensed.

Sources:

- <https://zenodo.org/records/7118517>
- License metadata: <https://zenodo.org/api/records/7118517>
- <https://creativecommons.org/licenses/by/4.0/>
- DOI: <https://doi.org/10.5281/zenodo.7118517>
- Paper DOI: <https://doi.org/10.1109/RE.2017.29>

The release policy therefore relies on the explicit CC BY 4.0 metadata for
research reuse while retaining the curator's warning. It does not relicense
PURE content under the repository's MIT license or imply that the curators or
original document authors endorse this thesis.

### Repository-specific finding

The repository uses full PURE source text and figures from at least:

- `2010 - split merge`;
- `2010 - mashboot`.

The local source PDFs and extracted images remain ignored by Git to avoid
duplicating the source corpus. The tracked candidate and verification
annotations are adaptations of the CC BY 4.0 dataset and may be public when the
required attribution and change notice accompany them.

### Public form and attribution

The public repository may contain:

- PURE dataset and document identifiers;
- source page and section references;
- cryptographic hashes;
- selected or contextualized requirement text with source attribution;
- author-created labels, claims, evidence references, and category counts;
- aggregate and per-item evaluation results;
- extraction and evaluation code;
- an automated setup script that downloads the original archives from Zenodo.

Every public PURE-derived package must:

- credit Ferrari, Spagnolo, and Gnesi and link the Zenodo record;
- identify the source dataset as CC BY 4.0 and link the license;
- state that this thesis selected, contextualized, annotated, or evaluated the
  material;
- retain the curator's underlying-rights and takedown caveat;
- avoid implying endorsement or applying the repository's MIT license to the
  PURE-derived content.

Raw provider responses, credentials, personal paths, and caches remain excluded
for privacy and repository-hygiene reasons, not because PURE results are barred
from publication.

Suggested attribution:

> This work uses and adapts PURE 2.0 by Alessio Ferrari, Giorgio Oronzo
> Spagnolo, and Stefania Gnesi, distributed through Zenodo under CC BY 4.0.
> Changes include selecting two documents, contextualizing requirements,
> assigning UI-evaluability and verification labels, linking visual evidence,
> and evaluating model outputs. The PURE curators do not endorse this work.
> Dataset: <https://doi.org/10.5281/zenodo.7118517>. License:
> <https://creativecommons.org/licenses/by/4.0/>. The PURE record notes that
> the curators did not verify the underlying rights of every collected Web
> document and provides a contact for takedown requests.

### Thesis use

The thesis may cite PURE and publish its selected examples and results with the
same attribution and provenance notice. Figures should identify the PURE source
document and any author-added annotations.

## 3. Release classes

### Public repository content

- `src/`, `scripts/`, `tests/`, and frontend source;
- experiment configuration files;
- aggregate metric JSON files;
- aggregate bootstrap and stability summaries;
- reviewed PURE-derived candidate and verification annotations under CC BY 4.0
  attribution;
- PURE aggregate and sanitized per-item evaluation results;
- curated Mind2Web-derived prediction and bounding-box outputs that exclude
  screenshots, source-page text, raw provider responses, caches, secrets, and
  absolute local paths;
- methodology and thesis documentation;
- hashes and counts that do not expose source content.

The repository has a root MIT `LICENSE` covering the author's original
software. PURE-derived content instead retains the CC BY 4.0 attribution in
`data/annotations/PURE_ATTRIBUTION.md`. `NOTICE.md` excludes the thesis,
datasets, derived annotations, screenshots, and other third-party material from
the MIT license.

### Supervisor-only

- the 44-item second-review form;
- uncurated per-item predictions and raw responses;
- uncurated source-derived evidence descriptions and absolute screenshot paths;
- reviewer working material not included in the public allowlist.

### Excluded from this repository's default public package

- Mind2Web test archives and their unzipped contents;
- Mind2Web screenshots, HTML/MHTML, HAR, trace, video, and session data;
- PURE source archives and extracted figures, which are installed directly from
  Zenodo by the setup script instead of duplicated in Git;
- secrets, API keys, account data, or billing identifiers.

## 4. Final release gate

A public thesis artifact is allowed only when all of the following are true:

1. the supervisor approves the curated Mind2Web-derived release boundary;
2. a root code license is selected;
3. `DATASET_NOTICE.md` and dataset citations are included;
4. public files contain no Mind2Web source screenshots or test records, no
   duplicated PURE source archives, and no raw provider responses, secrets, or
   personal data;
5. the path/secret audit passes;
6. the public package is built from an explicit allowlist rather than by
   publishing the complete working repository;
7. PURE-derived releases carry CC BY 4.0 attribution, change identification,
   and the curator's provenance caveat.

## 5. Thesis disclosure text

> The evaluation uses 13 trajectories from the Mind2Web `test_task` split.
> Mind2Web is distributed under CC BY 4.0, while its maintainers additionally
> request that unzipped test files not be redistributed online and that
> benchmark data not enter training corpora. Consequently, the released
> replication material contains code, configurations, hashes, aggregate
> results, reviewed derived annotations, and explicitly sanitized prediction
> artifacts, but no original screenshots, HTML, trajectories, or complete test
> records. PURE 2.0 is distributed through Zenodo under CC BY 4.0. The released
> replication material includes selected and contextualized requirements,
> reviewed annotations, and aggregate results with attribution and an
> indication of changes. The PURE record notes that the curators did not verify
> the underlying rights of every collected Web document; this provenance and
> takedown caveat is retained. Original PURE archives are installed directly
> from Zenodo rather than duplicated in the repository.
