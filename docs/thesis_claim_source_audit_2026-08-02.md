# Thesis Claim-to-Source Audit

Date: 2 August 2026

Audited manuscript: `docs/thesis_first_draft.md`

Audited bibliography: `thesis/bibliography.bib`

## 1. Purpose and decision rule

This audit checks whether sources cited in the thesis are relevant to the
corresponding statements and whether they support the strength and scope of
those statements. It also checks central externally verifiable claims that were
not cited. It is not a systematic literature review and does not establish that
the targeted search found every related paper.

Each citation use receives one of four decisions:

- **Supported:** the source directly supports the statement at its stated
  strength.
- **Supported with qualification:** the source supports the core statement, but
  the thesis must preserve an explicit scope or inference boundary.
- **Partially supported:** the citation is relevant, but the sentence claims
  more than the source establishes.
- **Unsupported or unsuitable:** the source does not establish the claim or is
  not an appropriate source for it.

Official proceedings pages, publisher records, institutional repositories,
arXiv records, and official model cards were preferred. Full text was inspected
when the thesis claim went beyond the abstract. For Massenon et al., the final
article was still under repository embargo; the audit therefore used the final
publisher metadata and the institutional accepted-manuscript record. This is
sufficient for the abstract-level comparison made in the thesis.

## 2. Coverage

- 26 bibliography records inspected.
- 24 sources currently cited in the manuscript.
- 41 individual citation-key uses across 35 citation commands checked.
- Two unused Google documentation records checked for metadata but excluded
  from the claim-support denominator.
- Central uncited claims in the Introduction, Related Work, research design,
  model-capacity discussion, and statistical-method section screened.

## 3. Claim-to-source matrix

| Source | Main thesis use | Decision | Audit note |
| --- | --- | --- | --- |
| Kwa et al. (2025) | Defines the 50% task-completion time horizon and reports approximately exponential historical growth on the studied tasks | Supported | The paper defines the metric relative to human task time and reports an approximate seven-month doubling since 2019, with external-validity caveats. |
| Jimenez et al. (2024) | Positions SWE-bench as repository-level resolution of real GitHub issues rather than isolated code completion | Supported | The task requires editing a repository to resolve issues drawn from real GitHub repositories. |
| Becker et al. (2025) | Reports that early-2025 AI tools increased completion time for experienced developers on familiar open-source repositories | Supported | The randomized trial reports a 19% slowdown for 16 developers completing 246 tasks in projects with substantial prior experience. |
| Nass, Alégroth, and Feldt (2021) | Motivates persistent GUI-test-automation challenges arising from GUI complexity and variability | Supported | The SLR distinguishes inherent and removable challenges and identifies long-lived technical problems. |
| Kretzer et al. (2025) | Connects user stories to GUI prototypes and detects whether stories are implemented | Supported | The assistant detects user-story implementation, identifies relevant components, and supports GUI-prototype work. |
| Kolthoff et al. (2025) | GUISpector operationalizes requirements, explores interactive GUIs, records trajectories, and returns met/partial/unmet decisions with evidence | Supported | The full paper explicitly describes autonomous verification trajectories, evidence, acceptance-criterion decisions, and the three requirement classes. |
| Massenon, Gambo, and Khan (2026) | Cross-modal mobile bug-fix verification using textual and visual evidence | Supported | BUGFixChecker combines bug reports, developer claims, changelogs/user feedback, and before/after UI screenshots. The thesis correctly treats it as bug-fix rather than requirement verification. |
| Deng et al. (2023) | Mind2Web supplies real-web tasks and ordered action trajectories for generalist web-agent evaluation | Supported | The official NeurIPS record reports more than 2,000 tasks from 137 real websites and crowdsourced action sequences. |
| Rawles et al. (2023) | Android in the Wild is a related mobile-device-control trajectory dataset | Supported | The dataset contains screens, actions, language instructions, and multi-step device-control demonstrations. |
| Cheng et al. (2024) | SeeClick specializes visual GUI grounding and connects grounding quality to downstream agents | Supported | The ACL paper defines GUI grounding as locating screen elements from instructions and evaluates GUI-specific grounding pretraining. |
| Gou et al. (2025) | UGround treats GUI grounding as a dedicated trained capability | Supported | The ICLR paper trains a specialized visual grounding model on GUI elements and referring expressions. |
| Yang et al. (2023) | Set-of-Mark overlays candidate regions with marks for reference by a multimodal model | Supported | The paper uses segmentation proposals with alphanumeric marks, masks, or boxes. The thesis correctly states that its OCR/UI proposal pipeline is inspired by, not identical to, this method. |
| Zheng et al. (2024) | SeeAct finds Set-of-Mark ineffective for its web-agent setting and performs best with combined visual and HTML grounding | Supported | The ICML abstract and full text state both points directly. |
| Berry, Kamsties, and Krieger (2003) | Linguistic ambiguity sources including vague expressions, references, and quantifiers | Supported | The handbook discusses these categories and specifically treats terms such as “all,” “each,” and “every.” |
| Gervasi et al. (2019) | Ambiguity depends on language, interpretation, context, and actors rather than being one uniform textual defect | Supported with qualification | The framework supports the distinction. The thesis appropriately presents the three-part summary as a synthesis, not a verbatim taxonomy. |
| Cleland-Huang et al. (2014) | Traceability spans heterogeneous artifacts, evolves over time, and remains costly to create and maintain | Supported | The paper explicitly discusses heterogeneous artifact repositories, link evolution, manual effort, and trace maintenance. |
| Hendrickx et al. (2024) | General reject-option principle and error/rejection trade-off | Supported | The survey covers abstaining when a prediction is likely wrong and formalizes rejection costs and evaluation. |
| Wen et al. (2025) | LLM-specific abstention under uncertainty or unanswerability | Supported | The TACL survey defines abstention as refusing to answer and reviews query-, knowledge-, and value-related settings. The thesis correctly distinguishes this literature from its semantic `ABSTAIN` label. |
| Ferrari, Spagnolo, and Gnesi (2017) | PURE is a heterogeneous collection of public requirements documents | Supported | The paper reports 79 documents gathered from the web across formats, domains, structures, and abstraction levels. Claims about context dependence are now explicitly limited to the selected documents examined in this thesis. |
| Baltes et al. (2026) | Reporting model versions, configurations, prompts/traces, validation, baselines, and limitations in empirical LLM studies | Supported | These items correspond to the paper's eight guidelines. Whether the repository fully complies is an internal reproducibility question, not something established by the citation. |
| Field and Welsh (2007) | Resampling complete clusters rather than correlated observations within clusters | Supported | The paper is directly about bootstrapping clustered data and establishes consistency results for cluster bootstrap procedures. The thesis uses the intervals cautiously because only 13 clusters are available. |
| Google Gemini 2.5 Flash-Lite model card | Multimodal input, structured output, thinking, and 1,048,576-token input limit | Supported | Verified against the official model page as accessed on 2 August 2026. |
| Google Gemini 3.1 Flash-Lite model card | Multimodal input, structured output, thinking, and 1,048,576-token input limit | Supported | Verified against the official model page as accessed on 2 August 2026. |
| Qwen3-VL-8B-Instruct model card | Open weights under Apache-2.0, multimodal input, and a native 256K context | Supported | Verified against the official Qwen model card. The thesis only uses these documented properties for a conservative capacity check. |

## 4. Corrections made from the audit

### Claim-strength corrections

1. The Introduction previously inferred that benchmark progress had already
   reduced implementation effort. Kwa et al. and SWE-bench demonstrate broader
   task capability, not reduced end-to-end human effort. The sentence now says
   that the developments expand the scope of work that can be delegated. Becker
   et al. remains the explicit counterweight on measured productivity.
2. The research-gap statement previously said that no line of work evaluates
   the full contract. Because the documented search is targeted rather than
   systematic, the statement now refers to the work identified by that search.
3. The PURE paragraph previously generalized context dependence to the whole
   corpus. It now attributes the observation to the selected documents examined
   in this thesis.
4. The generic claim that multimodal models can describe screenshots now refers
   specifically to the reviewed multimodal systems and their ability to process
   screenshots.

### Missing methodological support

5. The cluster-bootstrap method was described without a statistical-method
   citation. Field and Welsh (2007) has been added in both the research strategy
   and statistical comparison sections.

### Bibliographic corrections

6. Corrected the authors and full title of Massenon, Gambo, and Khan (2026).
7. Corrected the containing volume title for Gervasi et al. (2019).
8. Corrected the full publication title of the UGround paper.
9. Added missing page/article metadata for SeeClick, Cleland-Huang et al., PURE,
   Kretzer et al., Nass et al., and SeeAct.
10. Replaced all `and others` placeholders with complete author lists for the
    cited records.

## 5. Remaining limitations and examiner risk

No citation problem found in this audit undermines a central empirical result.
The remaining limitations are low risk if stated transparently:

- The literature search is targeted, not systematic. It supports a scoped gap
  statement, not a proof that no related work exists.
- GUISpector is currently an arXiv paper rather than a peer-reviewed venue
  publication. It remains the closest task comparison and should be identified
  as a preprint in the bibliography.
- The Massenon et al. comparison was checked at the abstract and institutional
  record level because the accepted manuscript is embargoed. The thesis makes
  no detailed method or performance claim that would require inaccessible
  full-text evidence.
- Official model documentation can change. The bibliography records the access
  date, and the thesis should retain exact executed model identifiers and dates
  in its experiment artifacts.
- Field and Welsh provide the methodological basis for clustered bootstrap
  resampling, but 13 clusters still yield imprecise descriptive intervals. The
  thesis already states this limitation and avoids population-level guarantees.

## 6. Primary records used

- Kwa et al.: <https://arxiv.org/abs/2503.14499>
- Becker et al.: <https://arxiv.org/abs/2507.09089>
- Berry, Kamsties, and Krieger: <https://se.uwaterloo.ca/~dberry/handbook/ambiguityHandbook.pdf>
- SWE-bench: <https://openreview.net/forum?id=VTF8yNQM66>
- Nass et al.: <https://doi.org/10.1016/j.infsof.2021.106625>
- Kretzer et al.: <https://doi.org/10.1145/3706598.3713932>
- GUISpector: <https://arxiv.org/abs/2510.04791>
- Massenon et al.: <https://doi.org/10.1016/j.infsof.2025.107996>
- Mind2Web: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/5950bf290a1570ea401bf98882128160-Abstract-Datasets_and_Benchmarks.html>
- Android in the Wild: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/bbbb6308b402fe909c39dd29950c32e0-Abstract-Datasets_and_Benchmarks.html>
- SeeClick: <https://aclanthology.org/2024.acl-long.505/>
- UGround: <https://openreview.net/forum?id=kxnoqaisCT>
- Set-of-Mark: <https://arxiv.org/abs/2310.11441>
- SeeAct: <https://proceedings.mlr.press/v235/zheng24e.html>
- Gervasi et al.: <https://doi.org/10.1007/978-3-030-30985-5_12>
- Cleland-Huang et al.: <https://doi.org/10.1145/2593882.2593891>
- Hendrickx et al.: <https://doi.org/10.1007/s10994-024-06534-x>
- Wen et al.: <https://aclanthology.org/2025.tacl-1.26/>
- PURE: <https://doi.org/10.1109/RE.2017.29>
- Baltes et al.: <https://arxiv.org/abs/2508.15503>
- Field and Welsh: <https://doi.org/10.1111/j.1467-9868.2007.00593.x>
- Gemini 2.5 Flash-Lite: <https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite>
- Gemini 3.1 Flash-Lite: <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>
- Qwen3-VL-8B-Instruct: <https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct>
