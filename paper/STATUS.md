# First DiagPriv manuscript draft status

All required narrative sections are drafted: abstract, introduction, threat
model, formulation, transformation framework, methodology, family designs,
results, privacy--utility, evidence support, limitations, related work, and
conclusion. Tables 1--5, an additional family-specific temporal-exposure
table, and Figures 1--3 have source files. Tables and the paired-count figure
are regenerated from frozen development data and the merged exposure artifact.

## Needs review before submission

- **Literature:** references.bib deliberately has no unverified entries.
  Verify and add work on LLM de-identification, pseudonymization/tokenization,
  format-preserving methods, privacy--utility measurement, operational RCA,
  temporal reasoning, and evidence attribution. Revise the related-work
  positioning only after that review.
- **Artifacts:** issue #35 must resolve provenance-safe distribution of
  ignored provider JSONLs before claiming full public observation-level
  reproduction.
- **External validity:** obtain human difficulty/annotation baselines,
  broader incident families and model families, and a preregistered final
  held-out evaluation. Incident 001's raw-only validation is not a matched
  privacy comparison.
- **Threat model:** assess real annotation coverage, auxiliary-data attacks,
  operational key management, known-time anchors, provider terms, and
  real-data governance in separate work.

## Safe preprint-level claims from current evidence

The fixed synthetic development comparisons show task-dependent diagnostic
structure and report descriptive RCA, evidence-support, and representation
exposure separately. The Incident 003 v3 paired-mechanism pattern is
directionally consistent with the preregistered temporal-dependency
expectation. The versioned exposure vector documents visible literal,
linkage, format, cardinality, and temporal properties in selected ModelViews.

## Claims not yet supported

Do not claim statistical significance, raw/relative-time equivalence,
universal transformation superiority, a deployed task-aware selector,
anonymity, zero re-identification risk, legal compliance, differential
privacy, provider-side security, production effectiveness, or full public
artifact reproducibility. The historical Stage-1 evidence-v4 outcome must
not be replaced by its post-hoc v5 rescore.
