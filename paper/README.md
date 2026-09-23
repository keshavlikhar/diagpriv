# DiagPriv manuscript source

Working title: *DiagPriv: Diagnostic-Invariant Privacy Transformations for
LLM-Based Root Cause Analysis*. This is a development-stage research draft,
not a submission-ready or held-out evaluation claim.

## Reproduce tables and build

From the repository root:

~~~bash
uv run python paper/render_tables.py --check
uv run python paper/render_tables.py --write
uv run pytest tests/test_paper_tables.py
~~~

The renderer reads paper/data/frozen_development_results_v1.json and the
merged, development-only docs/data/privacy_exposure_development_v1.json
directly. It verifies the latter's SHA-256,
beffb1fe1d53250670921ef2817c5a111bf2bf41e3bff7ba474940cd58d0ebc2,
before writing seven deterministic LaTeX table/figure assets under
paper/generated/. The check mode is read-only and fails on any byte
difference. The paper data file records exact source-document paths and
frozen result hashes for the utility tables. It contains no provider
output, sensitive identifiers, or credentials.

From `paper/`, compile with `latexmk` and a TeX distribution that provides
the packages imported by `main.tex` (including geometry, lmodern, amsmath,
amssymb, booktabs, graphicx, float, xcolor, TikZ, hyperref, and microtype):

~~~bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
~~~

The PDF and auxiliary files are in the ignored `paper/build/` directory and
should not be committed. The source
uses the generic article class, not a premature venue template. BibTeX
references are compiled by `latexmk`; primary-source verification and
conservative novelty comparisons are in `paper/RELATED_WORK_REVIEW.md`.

## Frozen result provenance

- Incident 001 development and raw-only validation counts:
  docs/CURRENT_STATUS.md, including the exact JSONL hash ledger. The
  paper does not treat raw validation as transformed-condition validation.
- Incident 002 primary three-trial and later transport-recovered sensitivity
  counts: docs/INCIDENT_002_FINAL_FINDINGS.md. The data file records all
  trial and recovery artifact hashes; recovery does not replace the primary
  ten missing responses.
- Incident 003 v3: docs/INCIDENT_003_V3_STAGE1_EVIDENCE_V5_ANALYSIS.md,
  docs/INCIDENT_003_V3_STAGE2_RELATIVE_RESULTS.md, and
  docs/INCIDENT_003_V3_STAGE3_ABLATION_RESULTS.md. Exact Stage-1/2/3
  result hashes are also typeset in the evaluation section.
- Exposure definitions and caveats:
  docs/PRIVACY_EXPOSURE_ANALYSIS.md; compact cross-check:
  docs/PAPER_RESULTS_TABLES.md.

All provider-result JSONLs remain ignored local files and are not packaged in
the repository. `docs/FROZEN_ARTIFACT_ARCHIVE_RFC.md`, the tracked manifest,
and the offline verifier define a provenance-safe private-archive design, but
no archive has been provisioned or uploaded. The tracked repository therefore
provides Level-1 reproducibility only; exact private observation distribution
(Level 2) and public observation-level release (Level 3) are unavailable. No
provider call, RCA rescore, validation access, or held-out generation is needed
to regenerate the manuscript tables.

## Review boundary

The data and generated LaTeX are development observations. They do not
establish anonymity, statistical equivalence, broad model capability, or
production effectiveness. See paper/STATUS.md for unresolved venue-specific literature,
artifact, validation, and human-baseline work.
