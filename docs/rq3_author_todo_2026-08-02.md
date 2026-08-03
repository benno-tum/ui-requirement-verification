# RQ3 Author Completion Checklist

Status: automatic preparation complete on 2 August 2026.

No additional paid model run is required. The stored first runs cover all 258
requirements in each of the six prespecified conditions. The automatic pass
created a condition-blinded review queue containing 653 condition-item rows
over 153 distinct requirements.

## Required for the final RQ3 answer

### 1. Complete the author coding workbook

Open `outputs/019fbfa1-94d4-7bb1-9a8a-81dd427302cf/rq3_author_review.xlsx`.
Work in the `Review Queue` sheet and fill the yellow author columns W--AC.

Why this is necessary: the thesis can count label errors, abstentions, unsafe
fulfilled predictions, and evidence overlap automatically, but it cannot call
those observations causes. Distinguishing an evidence-selection miss from an
interpretation error or a label-boundary disagreement requires inspection of
the screenshots and requirement wording by the thesis author.

Practical order:

1. Keep the table sorted by flow, requirement ID, and condition. The six rows
   for one requirement are adjacent, so inspect the complete flow once and
   compare the supplied screenshot sets across conditions.
2. Fill `Author: decisive evidence supplied` with `TRUE` or `FALSE`.
3. Choose exactly one `Author: primary category` from the dropdown.
4. Copy, remove, or extend the suggested requirement and evidence tags. Use
   semicolons when more than one tag applies.
5. Add one sentence that refers only to visible screenshot evidence.
6. Mark `Author: gold review candidate` as `TRUE` only if the reference itself
   may be wrong. Do not change gold during this first pass.
7. Set `Author: review status` to `COMPLETE` only after all preceding fields
   have been filled.

The automatic suggestions are deliberately excluded from reviewed counts.
Accepting all suggestions without inspection would turn a manual error analysis
into an undocumented heuristic classifier.

### 2. Freeze and process possible gold amendments

After every row is reviewed, filter `Author: gold review candidate = TRUE` and
decide those cases together. Record each accepted correction in the item's
metadata with its date, old value, new value, and visible justification.

Why this is necessary: changing reference labels while coding model errors can
bias the analysis toward the observed predictions. A separate amendment pass
preserves the distinction between correcting the benchmark and explaining a
model error. If any amendment is accepted, all aggregate metrics must be
regenerated from unchanged stored predictions.

### 3. Generate the reviewed RQ3 summaries

Return the completed workbook to Codex so its author columns can be synchronized
into the canonical JSON audit form. Then run:

```bash
python scripts/analyze_rq3_error_audit.py
python scripts/analyze_thesis_final_matrix.py
python scripts/analyze_thesis_run_stability.py
python scripts/analyze_chronology_ablation.py
python scripts/audit_thesis_replication_package.py --check-only
```

Why this is necessary: the RQ3 analyzer refuses to emit category percentages
until all 653 rows are complete. The remaining commands ensure that any accepted
gold amendment is reflected consistently in the main matrix, stability,
chronology, and replication artifacts.

### 4. Replace the provisional RQ3 wording in the thesis

Once reviewed counts exist, update Chapter 6 and the RQ3 conclusion with:

- primary category counts and percentages among label errors;
- causes among unsafe `FULFILLED` predictions, using predicted `FULFILLED` as
  the denominator;
- reasons for abstention, using model abstentions as the denominator;
- raw/all versus raw/top-4 and gated/all versus gated/top-4 comparisons;
- label-correct but evidence-incorrect cases as a separate traceability result;
- the number and categories of unstable Qwen rows.

Why this is necessary: the current thesis includes an objective trigger table
but explicitly avoids presenting its overlapping columns as manually coded
causes. The reviewed results are the missing quantitative answer to RQ3.

### 5. Add the final RQ3 visualization

Create one grouped or stacked bar chart showing reviewed primary error
categories by condition. Keep the objective trigger table because it uses
different denominators and measures different events.

Why this is necessary: the figure should visualize the final causal coding,
not merely duplicate the existing accuracy and abstention tables. It will make
the main RQ3 comparison much easier to understand.

## Optional auxiliary reviews

### 6. Decide whether to complete the 81-item UI-evaluability review

The form exists at
`data/annotations/evaluation_audits/single_author_final_20260725/ui_evaluability_disagreement_audit_form.json`.

This is useful for describing recurring boundaries between visible UI behavior
and hidden obligations, but it is not required for the main fulfillment-label
metrics. Because the set contains only disagreements, it cannot estimate
classifier accuracy or annotator agreement. If it is not completed, retain the
current thesis limitation stating that it contributes no resolution counts.

### 7. Decide whether to complete the 60-item region-grounding review

The form exists at
`data/annotations/evaluation_audits/single_author_final_20260725/v7_region_author_audit_form.json`.

This review is required only if the thesis should claim benchmark-wide region
relevance or sufficiency. It is not part of fulfillment-label accuracy or the
core RQ3 taxonomy. If it is not completed, retain the current diagnostic-only
scope and do not report localization-quality rates.

## Already completed by Codex

- Recomputed the controlled matrix after the GameStop correction: 13 flows,
  258 items, and 10,000 flow-cluster bootstrap samples.
- Recomputed run stability and the chronology ablation.
- Verified the replication package: 23 files and zero findings.
- Generated the frozen RQ3 JSON audit, automatic trigger inventory, condition
  key, incomplete-progress guard, and author workbook.
- Added the objective trigger inventory and its denominators to Chapter 6.
- Distinguished the five prespecified cases from later Book Depository,
  Carnival, and corrected GameStop examples.
- Removed unsupported future promises for the incomplete UI-evaluability and
  region-grounding reviews.
