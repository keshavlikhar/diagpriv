# DiagPriv preprint-readiness checklist

Issue #51. Working branch: `paper/preprint-release`.

Baseline before the integrated revision:
`6ae3d0a136dab38700e32927eaced9f50c6527ef`.

## Review provenance

Two prerequisite reviews are complete:

- #49 is an **internal adversarial scientific red-team review** performed by
  the project team/assistant. It is not an independent external review.
- #50 is a **team-executed clean-room reproducibility review** whose value
  comes from a genuinely fresh hosted environment. It is not an independent
  collaborator review.

Any later feedback from external collaborators should be recorded separately.

## Authorship

Confirmed author order:

1. Keshav Likhar — Independent Researcher, Boise, Idaho, USA
2. Harsh Mandalgi — Independent Researcher, Bengaluru, India
3. Mohit Chaturvedi — Independent Researcher, Buffalo, New York, USA

Keshav Likhar is the primary project lead and corresponding author. All three
authors are credited as equal contributors.

Confirmed ORCIDs:

- Keshav Likhar: 0009-0000-1473-8274
- Harsh Mandalgi: 0009-0000-9956-3636
- Mohit Chaturvedi: 0009-0001-7496-1504

The public corresponding-author contact is confirmed as `keshavlikhar007@gmail.com`. The manuscript exposes only the corresponding-author email; coauthor emails are not required for the preprint source.

## Review triage

| Finding | Source | Severity | Decision | Action |
| --- | --- | --- | --- | --- |
| Replace stale issue-#35 artifact wording with actual Level-1/2/3 state | #49 / #50 | Must fix | Accepted | Implemented in Methodology, Limitations, README, paper README, STATUS |
| Make Incident 003 asymmetry explicit: target 4/4 throughout, twin 3/4 -> 2/4 -> 0/4 | #49 | Must fix | Accepted | Implemented in Results, Limitations, Conclusion |
| Avoid treating Incident 002 as a shape-only causal intervention | #49 | Must fix | Accepted | Reframed as shape-sensitive and explicitly associational |
| Make Incident 002 primary coverage visible beside recovered sensitivity utility | #49 | Must fix | Accepted | Utility table now includes Primary valid coverage |
| Rename Identity-dependent Incident 001 | #49 | Should fix | Accepted | Renamed Linkage-dependent |
| State that cross-family accuracy levels are not directly comparable | #49 | Should fix | Accepted | Added to Results |
| Surface Incident 003 adaptive benchmark-development history earlier | #49 | Should fix | Accepted | Added to family design |
| Keep Incident 002 interpretation centered on trigger/mechanism, not exact RCA alone | #49 | Should fix | Accepted | Existing dimension-level interpretation retained and clarified |
| Explain why evidence-v5 is a representation repair rather than score optimization | #49 | Should fix | Accepted | Added explicit rationale and surviving failures |
| Tie first-page privacy wording to representation exposure rather than formal privacy | #49 | Should fix | Accepted | Introduction/abstract wording calibrated |
| Refresh stale root README Incident 003 status | #50 | Must fix | Accepted | Implemented |
| Document concrete TeX build prerequisites | #50 | Should fix | Accepted | Implemented in paper README |
| Surface paper and artifact-verifier commands in root README | #50 | Should fix | Accepted | Implemented |
| Distinguish current clean-room review from historical fresh-clone audit | #50 | Should fix | Accepted | Implemented |

Optional suggestions from #49, including a per-pair Incident-003 table and
additional future human/model studies, are deferred unless final visual review
shows they materially improve the preprint.

## Scientific claim status

The publication title is finalized as:

> DiagPriv: Preserving Diagnostic Structure While Reducing Sensitive Data Exposure in LLM Root-Cause Analysis

The final preprint should continue to support only the following scoped
interpretation:

> DiagPriv studies pre-release transformation of operational troubleshooting
> evidence while preserving task-specific diagnostic invariants, and evaluates
> the resulting RCA utility, evidence support, and residual model-visible
> representation exposure.

Current evidence is synthetic and development-stage. The paper does not claim:

- statistical significance or raw/relative-time equivalence;
- a universal transformation ranking;
- formal anonymity, differential privacy, or legal de-identification;
- zero re-identification risk;
- production effectiveness;
- a deployed automatic task-aware selector;
- public reproduction of exact historical provider observations.

## Reproducibility state

Verified by #50 from a fresh GitHub-hosted Ubuntu runner:

- `uv sync --extra dev`: PASS
- tracked secret scan: PASS
- full suite: 861 passed, 2 skipped
- 7 generated paper assets verified
- 7 generated paper assets reproduced byte-for-byte
- frozen-artifact verifier: expected MISSING / exit 2 with no provider rerun

Current level:

- **Level 1 available** — source, configs, deterministic generators and
  analyses, tracked aggregates, exposure artifact, paper assets, hashes,
  offline verifier.
- **Level 2 unavailable** — private exact-byte archive is designed but not
  provisioned/materialized.
- **Level 3 unavailable** — no public provider-observation release.

## Release metadata

- [x] Final author order
- [x] Independent Researcher affiliations
- [x] ORCIDs
- [x] Equal-contribution statement
- [x] Corresponding author identified
- [x] `CITATION.cff` drafted without invented DOI/arXiv identifiers
- [x] Preferred public corresponding-author email confirmed
- [x] Apache-2.0 selected and added for repository software code; manuscript/text licensing remains separate
- [x] Level 2 private archive explicitly deferred for the initial preprint
- [ ] Add arXiv identifier/DOI only after one actually exists

## Final build and visual inspection

Completed final verification:

- [x] `uv run python paper/render_tables.py --check` — PASS in clean hosted audit
- [x] full `uv run pytest` — PASS, 861 passed / 2 skipped
- [x] `git diff --check` — PASS
- [x] tracked-file high-confidence secret scan — PASS
- [x] clean TeX-capable `latexmk` build — PASS on Ubuntu 24.04
- [x] citations and references resolved — no undefined citation/reference warnings
- [x] final page count recorded — 16 pages
- [x] substantive LaTeX warnings checked — none observed
- [x] every page visually inspected
- [x] Figures 1--3 visually inspected
- [x] Tables 1--5 and the temporal-exposure display visually inspected
- [x] first-page author/ORCID/corresponding-author rendering verified
- [x] abstract, limitations, conclusion, author-contribution section, and bibliography visually verified
- [x] arXiv-style source bundle built successfully from the packaged source without ignored/local files

## Frozen-data boundary

This revision must not:

- rerun provider experiments;
- inspect new validation or held-out cases;
- modify frozen provider observations;
- rewrite frozen hashes;
- change generator/scorer/transformation semantics used by reported results.

All numeric changes in generated paper assets must come from tracked frozen
paper data through `paper/render_tables.py`, never manual editing.

## Current decision

**PREPRINT READY**

No scientific blocker was found by #49 or #50. Release metadata decisions are resolved, current CI is green, deterministic paper assets verify, the manuscript and arXiv-style source bundle both compile cleanly, and all 16 rendered pages were visually inspected. No provider calls, validation access, held-out access, or frozen-observation changes were required.

## Release decisions confirmed after review

- Public corresponding author: Keshav Likhar, `keshavlikhar007@gmail.com`.
- Software code license: Apache License 2.0.
- Manuscript/preprint licensing is intentionally separate from the software license and will follow the selected preprint host/submission choice.
- Level-2 private exact-observation archive: **deferred for the initial preprint**. The paper will continue to state that exact provider observations are not distributed.


## Final verification record

- Clean software CI: GitHub Actions run 35802912441 — PASS.
- Clean preprint build audit: GitHub Actions run 35802912385 — PASS.
- Manuscript output: 16 pages, US Letter, PDF 1.5.
- Exact generated-paper-asset check: PASS.
- arXiv-style source-only bundle build: PASS.
- Visual inspection: all 16 pages, Figures 1--3, Tables 1--5, temporal-exposure display, title/author block, abstract, limitations, conclusion, author contributions, and bibliography.
- Substantive LaTeX warnings: none observed.


## Zenodo-first publication decision

Because arXiv endorsement is not currently available, the initial public
preprint will be deposited on Zenodo. This does not change the scientific
content or frozen experimental record. The paper may later be mirrored on
arXiv once endorsement is available, with the two records cross-linked.

The public-facing title was revised before first publication to make the
paper's contribution immediately understandable while retaining the DiagPriv
project name:

> DiagPriv: Preserving Diagnostic Structure While Reducing Sensitive Data Exposure in LLM Root-Cause Analysis

"DiagPriv" remains the project/benchmark name; the subtitle carries the
plain-language meaning for readers who do not already know the name.
