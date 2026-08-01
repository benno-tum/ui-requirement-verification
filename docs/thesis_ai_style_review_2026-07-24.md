# Thesis AI-Style Review

Date: 24 July 2026

Reviewed file: `docs/thesis_first_draft.md`

Reference checklist:
<https://de.wikipedia.org/wiki/Wikipedia:Anzeichen_f%C3%BCr_KI-generierte_Inhalte>

## Interpretation of the Checklist

The referenced page is a community checklist for German Wikipedia, not a
validated authorship detector or an academic-writing standard. It states that
the softer indicators are ambiguous and that automated AI detectors have high
error rates. Several listed features, including a conclusion, structured
headings, tables, lists, Markdown, and section summaries, are normal or required
in a technical thesis. They were therefore assessed in context rather than
removed mechanically.

The review cannot establish whether a text was written with AI assistance. Its
purpose is narrower: identify formulaic, repetitive, unsupported, or
editorial-sounding prose and improve the manuscript. Any required disclosure of
AI-assisted drafting remains necessary regardless of style.

## Findings and Revisions

### Strong indicators

No dialogue fragments, greetings, chatbot offers, knowledge-cutoff disclaimers,
broken Wikipedia templates, category links, or rendered search placeholders
were present.

Four HTML comments mark results that have not yet been produced. They are
intentional drafting notes and are invisible in the rendered manuscript. They
must be replaced with final results or removed before submission.

No obviously fictitious citation was found in the manuscript. The references
use identifiable DOI, proceedings, arXiv, or dataset records already maintained
in the bibliography audit. Final author lists, page ranges, publication years,
and publisher metadata still require the planned source-by-source bibliography
check before submission.

### Formulaic transitions and editorial comments

The original draft repeatedly used paragraph openings such as “This
distinction,” “This separation,” “This result,” and “At the same time.” It also
contained comments such as “This distinction is important” that described how
the reader should value a point. These passages were rewritten to state the
technical relationship directly.

Examples of the revision include:

- the evidence-metric explanation now states the difference between hit@k and
  complete multi-step recall directly;
- the UI-evaluability section explains the two failure modes without a
  “First ... Second ...” construction;
- the discussion describes the measured interaction between decomposition and
  screenshot selection without announcing that “the result is mixed.”

### Negative parallelism

The draft overused constructions of the form “not X, but Y,” “not merely,” and
“not only ... but also.” These were most visible in the motivation, research
gap, evidence discussion, contribution statement, and scope limitations.

The revised prose uses direct claims. For example, the motivation now separates
benchmark capability from observed delivery speed, and the grounding section
states that bounding boxes are evaluated for geometric validity, relevance, and
sufficiency. It no longer introduces this point through a contrast with label
accuracy.

Necessary logical negations remain where the evidence policy depends on them,
such as “missing evidence is not `NOT_FULFILLED`” and statements that
screenshots cannot establish hidden backend behavior.

### Tricolon and repeated rhetorical cadence

The pipeline description previously followed a conspicuous “First ... Second
... Third ... Fourth ... Finally” sequence. It was replaced with a compact
description of the data flow. The conclusion also introduced five contributions
through five nearly identical paragraphs. These are now grouped into two
substantive paragraphs.

Technical enumerations remain where the exact categories matter, including
label definitions, error taxonomies, metrics, and the experiment matrix.

### Section summaries and conclusion

Some sections ended by restating their opening sentence. Redundant summaries in
the related-work, retrieval, region-grounding, and discussion prose were
shortened or replaced with a concrete implication.

The thesis conclusion and direct RQ answers were retained. A conclusion is a
normal component of an empirical bachelor thesis even though the Wikipedia
checklist identifies formulaic “Fazit” sections as unusual for encyclopedia
articles.

### Formatting

Bold emphasis was removed from the five contribution bullets, table captions,
and qualitative error-category paragraphs. It remains for the three research
questions and their labels in the final RQ answers, where it supports
navigation.

Lists, tables, mathematical notation, and Markdown headings remain because the
file is the Markdown source of a technical thesis. They encode schemas,
experimental conditions, and quantitative results rather than presentation
flourishes. No emojis or decorative separators are used.

### Promotional language and vague authority

No promotional or celebratory language was found. Claims about related work are
attributed to named publications instead of vague groups such as “experts” or
“researchers.” Speculative generalizations were narrowed to the 13-flow
benchmark where necessary.

## Remaining Author Review

Before submission:

1. replace or remove the four hidden pending-result comments;
2. verify every bibliography entry against the publisher or official
   proceedings record;
3. read the manuscript aloud once to identify phrasing that does not match the
   author's normal academic voice;
4. add project-specific interpretation where the author has direct experimental
   knowledge, especially in the qualitative examples;
5. include the AI-use disclosure agreed with the supervisor.

These steps improve authorship transparency and scientific quality. They do not
attempt to optimize the text against an AI detector.
