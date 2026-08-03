# Dataset Notice

Release status: **public aggregate replication package**.

This package contains aggregate research artifacts derived from Mind2Web and
PURE. It is not a redistribution of either source dataset.

## Mind2Web

Mind2Web is provided by the OSU NLP Group under CC BY 4.0:

- <https://github.com/OSU-NLP-Group/Mind2Web>
- <https://creativecommons.org/licenses/by/4.0/>

Changes made for this thesis include selecting 13 `test_task` trajectories and
creating UI requirements, verification labels, claim annotations, evaluation
configurations, and aggregate metrics. The Mind2Web authors do not endorse this
work.

The original repository asks users not to redistribute unzipped test files
online and not to place benchmark data in training corpora. The public artifact
therefore excludes screenshots, HTML/MHTML, HAR files, traces, videos, task
records, processed trajectories, per-item prompts, and raw responses.

## PURE

PURE is described at:

- <https://zenodo.org/records/7118517>
- <https://doi.org/10.1109/RE.2017.29>

The PURE record states that the curators are not aware of license agreements or
intellectual-property rights for the third-party requirements documents
collected from the Web. The public artifact therefore excludes PURE source PDFs,
XML files, extracted figures, embedded images, substantial source text, and
per-item prompts or outputs reproducing that text.

## Package boundary

This package is limited to author-created configurations, aggregate metrics,
statistical summaries, sanitized manifests, and documentation that does not
reproduce source screenshots or substantial source text. The repository also
contains reviewed derived annotations and one explicitly sanitized prediction
set under `data/published/`; raw prompts, raw responses, and reviewer working
materials remain local.

The repository's MIT license covers original software only. No file in this
package should be interpreted as relicensing third-party dataset content.
