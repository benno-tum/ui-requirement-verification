# Targeted Literature Search Log

Date: 30 July 2026

Database: Google Scholar

Sort order and limits: Scholar relevance order, no date restriction. The first
20 results of the baseline query were screened. Result counts and rankings are
volatile and may vary by date, location, and Scholar index state.

Purpose: Identify literature adjacent to automated verification of textual
software requirements against GUI artifacts and document the search in a
reproducible form. This is a targeted related-work search rather than a
systematic literature review.

## Baseline query

```text
("software requirements" OR "user stories" OR "bug fixes")
("graphical user interface" OR GUI OR prototype OR screenshot)
(verification OR traceability OR consistency OR conformance)
("large language model" OR LLM OR multimodal OR "vision-language model")
```

Google Scholar treats whitespace between the parenthesized concept groups as
`AND`. Truncation wildcards were omitted because Scholar does not implement
database-style wildcard semantics consistently.

The query was constructed from four concepts:

1. textual software-engineering artifact;
2. GUI or screenshot artifact;
3. relation or decision between the artifacts; and
4. model family.

The relation block deliberately uses several terms because relevant work frames
the connection between textual and visual artifacts in different ways:

- `verification` directly expresses the decision studied in this thesis;
- `traceability` covers links from a requirement to the artifact used to
  justify or assess it;
- `consistency` covers cross-artifact agreement, including comparisons that do
  not use verification terminology; and
- `conformance` covers whether observed implementation states accord with the
  textual contract.

These terms are complementary rather than paper-specific: each denotes a
recognized relationship that may be used when requirements, prototypes,
screenshots, tests, or implementation evidence are compared.

## Screening rule

At title-and-snippet screening, a result was marked:

- **retain** when it directly connects a textual software-engineering artifact
  to a GUI or screenshot artifact and performs a verification-like decision;
- **candidate** when it may meet that rule but needs full-text review;
- **context only** when it is useful for orientation or snowballing but does
  not provide task-specific primary evidence; or
- **exclude** when it concerns GUI generation, generic requirements work,
  code-only verification, or a non-software visual task.

No candidate was added to the thesis on title-and-snippet evidence alone.

## Query sensitivity check

| ID | Change from baseline | Approx. results | Central comparison papers in top 10 | Observation |
| --- | --- | ---: | --- | --- |
| Q1 | Baseline | 3,920 | 3/3 at ranks 1, 2, and 3 | Best coverage and ranking of the central comparison set; precision declines after the first results |
| Q2 | Remove bare `GUI`, generic `prototype`, `traceability`, and `consistency`; restrict relation to verification/conformance/fulfillment | 931 | 2/3 at ranks 1 and 3 | More focused result set, but Massenon et al. drops out of the first page |
| Q3 | Add `natural language specification` and use `user interface`; keep the narrower relation block | 2,250 | 2/3 at ranks 1 and 4 | Retrieves specification-driven GUI testing, but still loses Massenon et al. |
| Q4 | Restore broad GUI/model synonyms but keep the narrower relation block | 2,950 | 3/3 at ranks 1, 2, and 5 | Recovers all three central comparison papers, but adds several broad surveys and does not improve the first page over Q1 |

The exact alternatives were:

```text
Q2:
("software requirements" OR "user stories" OR "bug fixes")
("GUI prototype" OR "graphical user interface" OR screenshot)
(verification OR conformance OR fulfillment)
("large language model" OR multimodal)

Q3:
("software requirements" OR "user stories" OR
 "natural language specification" OR "bug fixes")
("GUI prototype" OR "user interface" OR screenshot)
(verification OR fulfillment OR conformance)
("large language model" OR multimodal)

Q4:
("software requirements" OR "user stories" OR "bug fixes")
(GUI OR "graphical user interface" OR prototype OR screenshot)
(verification OR conformance OR fulfillment)
("large language model" OR LLM OR multimodal OR "vision-language model")
```

Q1 provides the strongest coverage of the central comparison set among the
tested formulations. Q2 is more focused but omits the
bug-fix-verification comparison from the first page.

## Complete screening of the first 20 baseline results

| Rank | Result | Screening decision | Reason or possible use |
| ---: | --- | --- | --- |
| 1 | Kretzer et al. (2025), *Closing the Loop between User Stories and GUI Prototypes* | Retain; already cited | Closest work on user-story representation in GUI prototypes |
| 2 | Massenon, Gambo, and Khan, *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes* | Retain; already cited | Adjacent textual/visual bug-fix verification |
| 3 | Kolthoff et al. (2025), *GUISpector* | Retain; cited after full-text review | Closest comparison: agent-executed requirement verification over interactive GUIs |
| 4 | *Fixpad++: Automated Bug Fix Verification Using LLM Agents* | Candidate | Potentially relevant GUI-based bug-fix verification; requires venue and full-text review |
| 5 | *AI-Assisted Requirements Engineering Using Multimodal Language Models* | Exclude pending credibility check | Scholar metadata reports 2019 despite terminology and content that appear substantially newer; venue quality also requires verification |
| 6 | *Context-Aware Visual Prompting: Automating Geospatial Web Dashboards...* | Exclude | Geospatial dashboard automation, not software-requirement verification |
| 7 | *Formalising Software Requirements with Large Language Models* | Exclude | Requirements formalization and code/model checking, not GUI evidence |
| 8 | *A Process-Centric Review of Large Language Models in Graphical User Interface Testing* | Context only | Potential orientation and citation snowballing; not task-specific primary evidence |
| 9 | *Effective GUI Generation: Leveraging Large Language Models for Automated GUI Prototyping* | Exclude | GUI generation rather than verification |
| 10 | *Zero-Shot Prompting Approaches for LLM-Based Graphical User Interface Generation* | Exclude | GUI generation rather than verification |
| 11 | *A Design Science Research Approach to LLM-Based Agents for Requirements Specification...* | Exclude | Requirements specification in low-code development, not verification against recorded GUI evidence |
| 12 | *Large Language Model Assisted Software Engineering: Prospects, Challenges, and a Case Study* | Exclude | General LLM-assisted software engineering |
| 13 | *Enhancing Requirements Engineering with Large Language Models...* | Exclude | General requirements-engineering thesis |
| 14 | *Large Language Models in High-Level Software Testing* | Context only | Broad testing background; not a direct task match from title/snippet |
| 15 | *On the Provenance of Software Systems: Automating Software Traceability...* | Exclude for core task | General traceability dissertation, not GUI verification |
| 16 | *Guiding Human Validation of LLM-Generated Code via Verifiable Literate Programming* | Exclude | Code validation rather than GUI evidence |
| 17 | *Reliable Execution of Natural Language Test Cases for GUI Applications Using LLM Agents* | Candidate | Close GUI-testing neighbor; requires full-text comparison of execution, oracle, and evidence contracts |
| 18 | *A LLM-Based Approach for End-to-End Web GUI Test Script Generation and Execution* | Candidate | Adjacent GUI test generation/execution; requires full-text review |
| 19 | *Improvement of Code Generation Quality ... Leveraging Product Documentation* | Exclude | Code generation and documentation, not GUI verification |
| 20 | *From Requirement Text to Diagrams: Using Generative AI for UML Modeling...* | Exclude | UML generation rather than GUI verification |

The first page contains four direct or potentially direct primary studies
(ranks 1--4) plus one contextual review (rank 8). The second page contains no
additional already cited task-nearest paper; ranks 17 and 18 are the only
clearly adjacent candidates from title-and-snippet screening. This means the
excellent top-three ranking should not be reported as high precision over the
entire result set.

## Coverage of sources used in Section 1.3

The baseline query retrieves Kretzer et al., Massenon et al., and GUISpector in
the first three ranks. It does not retrieve Mind2Web or SeeClick in the first 20
results, and it is not designed to retrieve the abstention sources. This is an
expected consequence of their different roles:

- Kretzer et al., Massenon et al., and GUISpector define the central
  requirements/verification neighborhood;
- Mind2Web and SeeClick establish the UI-agent and GUI-grounding context; and
- traceability and abstention justify specific design concepts.

Therefore, the query has strong coverage of the central comparison set but weak
coverage of the complete set of sources used to construct the research gap.

## Thesis reporting

The thesis records the database, date, exact query, relevance sort, first-20
screening depth, and the conceptual rationale for the relation terms. A concise
formulation is:

> A targeted Google Scholar search was conducted on 30 July 2026 using the
> query reported at the beginning of Chapter 2. The first 20 relevance-ranked results were
> screened against predefined artifact, task, and model criteria. The search
> retrieved the three closest comparison papers used in this thesis (Kretzer
> et al., 2025; Massenon, Gambo, and Khan, 2026; Kolthoff et al., 2025).
> Because the research gap also draws on distinct literatures on UI-agent
> trajectories, GUI grounding, traceability, and abstention, those strands
> were covered through concept-specific searches and citation chaining.
