# Thesis citation and source audit — 2026-08-03

## Scope and method

This audit covers every external citation that appears in the generated thesis,
the claim immediately supported by each citation, and the metadata in
`thesis/bibliography.bib`. Claims were checked against primary publication
pages, papers, official model documentation, dataset records, and repository
metadata. The canonical prose remains `docs/thesis_first_draft.md`; generated
chapter files were refreshed with `make all`.

## Result

No cited thesis claim was found to contradict its source. The citations support
the surrounding prose at the level claimed. Several passages are explicitly
author inferences or calculations rather than statements copied from sources:
the context-capacity sentence combines documented model limits with the
thesis's own 1,000-line/20-image stress calculation, and the research-gap
synthesis is the outcome of the stated targeted search rather than a claim made
by one cited paper.

The audit corrected four citation-link failures caused by line-sensitive
author-year normalization. Berry/Gervasi, Field/Welsh (two occurrences), and
Lu et al. had appeared as plain text and were absent from the rendered
bibliography. They now use explicit Pandoc citation keys. Every bibliography
entry is now cited, and no unnormalized author-year citations remain in the
generated chapters.

## Claim-to-source findings

| Citation(s) | Thesis claim supported | Assessment |
|---|---|---|
| Kwa; Jimenez | Time-horizon framing and real GitHub issue resolution as a repository-level benchmark | Directly supported. The thesis retains Kwa et al.'s scope caveat by referring to their studied tasks. |
| Becker | Early-2025 AI tools increased completion time for experienced developers working in familiar open-source repositories | Directly supported by the randomized trial; the thesis does not generalize beyond that setting. |
| Nass | GUI automation faces long-running practical and technical challenges | Directly supported by the systematic review. |
| Kretzer; GUISpector; Massenon | User-story/GUI matching, agent-driven requirement verification, and multimodal mobile bug-fix verification are adjacent tasks | Directly supported; the thesis accurately distinguishes each task from fixed-flow requirement verification. |
| Hendrickx; Wen | Reject-option and LLM-abstention research motivates withholding definite decisions under insufficient information | Directly supported. The thesis clearly presents its own `ABSTAIN` label as a semantic operationalization, not a learned threshold from these sources. |
| Berry; Gervasi | Natural-language requirements can contain ambiguity from vague wording, references, and quantification | Supported by the handbook and ambiguity framework. |
| Cleland-Huang et al. | Traceability links heterogeneous evolving artifacts and remains costly to maintain manually | Supported by the FOSE review. |
| Mind2Web paper | Mind2Web contains real-website tasks and interaction trajectories for generalist web agents | Directly supported by the NeurIPS paper. |
| Mind2Web repository | CC BY 4.0 status plus the requests not to redistribute unzipped test data or include it in training corpora | Directly supported by the maintainers' official repository. |
| SeeClick; UGround | GUI grounding is a specialized capability that maps language to interface locations | Directly supported. |
| Set-of-Mark; SeeAct | Mark overlays enable reference to proposed regions; SeeAct found Set-of-Mark weaker than its HTML-plus-visual grounding strategy | Directly supported. The proposal-coverage upper bound is a transparent methodological inference. |
| OmniParser | OmniParser produces structured UI element proposals from screenshots | Directly supported. |
| Field and Welsh | Resampling complete clusters is an appropriate cluster-bootstrap construction for dependent observations | Supported. The caution caused by having only 13 clusters is the thesis's conservative interpretation. |
| Google model pages; Qwen model card | The evaluated models accept multimodal input and have context limits above the stated stress case | Source metadata supports the model capabilities and limits; fit of the concrete stress case is the thesis's calculation. |
| Baltes et al. | Archiving model/configuration/run information follows current LLM empirical-study reporting guidance | Supported by the reporting guidelines. |
| PURE paper and Zenodo record | PURE is a heterogeneous public-requirements corpus; Version 2.0 metadata, DOI, authors, date, and CC BY 4.0 license | Directly supported. The official Zenodo API reports license ID `cc-by-4.0`; the record separately warns that source-document rights were not verified. |
| Brück artifact | The thesis source code and permitted replication materials are available publicly | Directly supported by the public GitHub repository checked on 2026-08-03. |

## Bibliography corrections

- Added the missing School of Computer Science affiliation and primary PDF URL
  for the Berry technical report.
- Added official volume, page range, and publication URL for Mind2Web.
- Added official publication URLs for UGround, SWE-bench, GUISpector,
  OmniParser, and SeeAct.
- Corrected the rendered titles of UGround and SeeAct to the titles used by
  their official publication pages.
- Removed three uncited entries (Android in the Wild and two generic Gemini
  documentation pages) instead of leaving bibliography metadata that the
  thesis does not use.
- Added bibliography-backed references for the Mind2Web distribution policy
  and the public thesis repository.

## Verification

`make all` succeeds. The generated PDF contains no undefined citations or
references and the build log contains no remaining TeX warnings. A mechanical
comparison of generated citation keys and BibTeX keys reports no uncited or
missing entries.
