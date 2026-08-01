# Bachelor’s thesis LaTeX workspace

This directory contains the LaTeX version of the thesis. The prose remains in
[`../docs/thesis_first_draft.md`](../docs/thesis_first_draft.md); the files in
`chapters/` are generated from it and must not be edited by hand.

## Edit and build

1. Edit `docs/thesis_first_draft.md`.
2. Run `make sync` in this directory to regenerate the eight chapter files.
3. Run `make pdf` to compile `build/main.pdf`, or `make all` to synchronize and
   compile in one command.

Synchronization requires `pandoc`. Compilation uses `latexmk` with
`pdflatex`/`bibtex` when available and otherwise falls back to `tectonic`. In a
graphical LaTeX editor, select `main.tex` as the root document and use
`pdflatex` with `bibtex`. The complete `thesis/` folder can also be uploaded to
Overleaf or [TUM ShareLaTeX](https://sharelatex.tum.de/ldap/login).

Markdown comments such as `<!-- TODO -->` are intentionally omitted from the
PDF and collected in `notes/pending_from_markdown.md` during synchronization.

## Formal basis and checks before submission

The Chair of Software Engineering does not currently publish a chair-specific
writing template on its thesis page. This workspace therefore adapts the
[TUM-Dev thesis template](https://github.com/TUM-Dev/tum-thesis-latex) to the
current [TUM CIT Informatics thesis requirements](https://www.cit.tum.de/en/cit/studies/students/thesis-completing-your-studies/informatics/).

The current setup follows the published requirements by:

- identifying TUM, the School of Computation, Information and Technology,
  Informatics, the degree, document type, title, and author on the cover;
- repeating that information and adding English and German titles, examiner,
  supervisor, and submission date on the first title page;
- omitting the matriculation number, private contact details, and company logos.

Before final submission, confirm these items with the supervisor:

- the exact registered English and German thesis titles;
- examiner, supervisor, submission place, and submission date;
- the required declaration of originality and wording for generative-AI use;
- whether the chair requests any additional formatting or archival material.

Submission itself is through the CIT portal; the generated PDF is a working
draft, not a guarantee that the thesis is formally ready for submission.

## Template attribution

The layout is derived from
[TUM-Dev/tum-thesis-latex](https://github.com/TUM-Dev/tum-thesis-latex) under
CC BY-SA 4.0. The exact imported revision and local modifications are recorded
in [`TEMPLATE_ATTRIBUTION.md`](TEMPLATE_ATTRIBUTION.md). The template license
applies to the template, not to the thesis content or resulting PDF.
