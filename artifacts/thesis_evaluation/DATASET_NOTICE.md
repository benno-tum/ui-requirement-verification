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
- <https://creativecommons.org/licenses/by/4.0/>
- <https://doi.org/10.1109/RE.2017.29>

Zenodo's metadata assigns PURE 2.0 CC BY 4.0. Changes made for this thesis
include selecting Split/Merge and Mashboot, contextualizing requirements,
assigning UI-evaluability and verification labels, linking visual evidence, and
calculating exploratory results. The PURE curators do not endorse this work.

The PURE record also states that the curators did not verify the underlying
license agreements or intellectual-property rights for every third-party Web
document and provides a takedown contact. This package retains that provenance
caveat. The original source archives are installed directly from Zenodo rather
than duplicated here.

## Package boundary

This package contains author-created configurations, aggregate metrics,
statistical summaries, sanitized manifests, and documentation. Its PURE summary
is derived from the versioned reviewed annotations and is distributed with the
CC BY 4.0 attribution above. The repository also contains reviewed derived
annotations and one explicitly sanitized Mind2Web prediction set under
`data/published/`; raw prompts, raw responses, and reviewer working materials
remain local.

The repository's MIT license covers original software only. No file in this
package should be interpreted as relicensing third-party dataset content.
