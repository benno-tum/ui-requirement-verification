# Dataset Licensing and Release Policy

Status: conservative release decision based on official source information,
23 July 2026, updated 3 August 2026 after supervisor confirmation of the
Mind2Web licensing approach. This is a research-artifact policy, not legal
advice.

## Decision

Until written permission or an institutional legal review says otherwise:

- the repository may publish source code, experiment configurations, aggregate
  metrics, statistical summaries, and documentation created by the thesis
  author;
- the aggregate thesis replication package and the explicitly curated
  Mind2Web-derived run set may be published with attribution;
- Mind2Web screenshots, HTML, MHTML, HAR files, videos, traces, `task.json`,
  `steps.json`, complete test records, raw per-item prompts, and raw provider
  responses are not published;
- PURE source PDFs, XML files, extracted figures, embedded screenshots,
  substantial text extracts, and annotations reproducing full requirement text
  are not published;
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

### Required attribution if permission is granted

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
collected from the Web. Crucially, the curator states that the dataset creators
are not aware of license agreements or intellectual-property rights governing
the source requirements and provide a takedown contact for possible copyright
claims.

Sources:

- <https://zenodo.org/records/7118517>
- DOI: <https://doi.org/10.5281/zenodo.7118517>
- Paper DOI: <https://doi.org/10.1109/RE.2017.29>

The fact that a record is openly downloadable from Zenodo is not sufficient
evidence that every underlying third-party requirements document can be
relicensed or redistributed in a new public package. Zenodo itself states that
reuse is subject to the license of the deposited object, while the PURE record
expressly identifies uncertainty over rights in the collected documents.

### Repository-specific finding

The repository uses full PURE source text and figures from at least:

- `2010 - split merge`;
- `2010 - mashboot`.

The local source PDFs and extracted images are correctly ignored by Git. Some
tracked verification annotations reproduce complete requirement passages.
Those files must remain supervisor-only unless the PURE curator or original
document rightsholder confirms redistribution permission.

### Permitted conservative public form

Without additional permission, a public artifact may contain:

- PURE dataset and document identifiers;
- source page and section references;
- cryptographic hashes;
- author-created labels and category counts that do not reproduce the source
  wording;
- aggregate metrics;
- extraction and evaluation code;
- a script requiring the user to obtain PURE independently from Zenodo.

It must exclude:

- the original PDFs or XML documents;
- extracted figures or screenshots;
- full or substantial requirement passages;
- per-item model prompts or outputs containing those passages;
- a newly assigned open license over third-party PURE text.

### Thesis use

The thesis may cite PURE and discuss aggregate results. Any requirement excerpt
or figure included in the thesis should be limited to what is necessary for the
academic argument, attributed to its source, and confirmed with the supervisor
or TUM publication guidance before a publicly accessible thesis copy is
released. Thesis quotation practice and dataset redistribution are separate
questions.

## 3. Release classes

### Public candidate under the repository's MIT code license

- `src/`, `scripts/`, `tests/`, and frontend source;
- experiment configuration files;
- aggregate metric JSON files;
- aggregate bootstrap and stability summaries;
- curated Mind2Web-derived prediction and bounding-box outputs that exclude
  screenshots, source-page text, raw provider responses, caches, secrets, and
  absolute local paths;
- methodology and thesis documentation;
- hashes and counts that do not expose source content.

The repository has a root MIT `LICENSE` covering the author's original
software. `NOTICE.md` excludes the thesis, datasets, derived annotations,
screenshots, and other third-party material from that license. Publishing code
under MIT does not grant redistribution rights for those excluded materials.

### Supervisor-only

- unpublished PURE per-item annotations containing source requirement text;
- the 44-item second-review form;
- uncurated per-item predictions and raw responses;
- uncurated source-derived evidence descriptions and absolute screenshot paths;
- reviewer working material not included in the public allowlist.

### Never redistribute without explicit permission

- Mind2Web test archives and their unzipped contents;
- Mind2Web screenshots, HTML/MHTML, HAR, trace, video, and session data;
- PURE source PDFs/XML;
- PURE embedded or extracted figures;
- secrets, API keys, account data, or billing identifiers.

## 4. Final release gate

A public thesis artifact is allowed only when all of the following are true:

1. the supervisor approves the curated Mind2Web-derived release boundary;
2. a root code license is selected;
3. `DATASET_NOTICE.md` and dataset citations are included;
4. public files contain no source screenshots, documents, substantial source
   text, test records, per-item raw responses, or personal data;
5. the path/secret audit passes;
6. the public package is built from an explicit allowlist rather than by
   publishing the complete working repository;
7. any release of Mind2Web source files or PURE source-derived content is
   supported by separate explicit permission.

## 5. Thesis disclosure text

> The evaluation uses 13 trajectories from the Mind2Web `test_task` split.
> Mind2Web is distributed under CC BY 4.0, while its maintainers additionally
> request that unzipped test files not be redistributed online and that
> benchmark data not enter training corpora. Consequently, the released
> replication material contains code, configurations, hashes, aggregate
> results, reviewed derived annotations, and explicitly sanitized prediction
> artifacts, but no original screenshots, HTML, trajectories, or complete test
> records. PURE contains requirements documents collected from third-party Web
> sources whose individual licensing status is not guaranteed by the dataset
> curators. PURE source documents, figures, substantial text extracts, and
> per-item model outputs are therefore excluded from the public artifact. Full
> internal artifacts are retained only for examination and reproducibility
> review under controlled access.
