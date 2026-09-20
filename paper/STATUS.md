# First DiagPriv manuscript draft status

All required narrative sections are drafted: abstract, introduction, threat
model, formulation, transformation framework, methodology, family designs,
results, privacy--utility, evidence support, limitations, related work, and
conclusion. Tables 1--5, an additional family-specific temporal-exposure
table, and Figures 1--3 have source files. Tables and the paired-count figure
are regenerated from frozen development data and the merged exposure artifact.

## Needs review before submission

- **Literature:** an initial primary-source-verified pass is complete in
  `references.bib` and `RELATED_WORK_REVIEW.md`; the related-work prose now
  cites clinical de-identification, pre-release prompt transformation,
  task-sensitive anonymization, RCA, grounding, and temporal evaluation.
  Venue-specific coverage and citation polish remain. Adaptive anonymization
  and evidence-grounded RCA are established prior areas, so the manuscript
  makes no priority claim for either. RCAgent's internally deployed model is
  an explicit privacy-aware RCA alternative.
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
The reviewed literature supports positioning this as a joint, scoped
measurement design, not as the first task-aware anonymizer, RCA benchmark,
evidence-grounding metric, or vector privacy analysis.

## Claims not yet supported

Do not claim statistical significance, raw/relative-time equivalence,
universal transformation superiority, a deployed task-aware selector,
anonymity, zero re-identification risk, legal compliance, differential
privacy, provider-side security, production effectiveness, or full public
artifact reproducibility. The historical Stage-1 evidence-v4 outcome must
not be replaced by its post-hoc v5 rescore.
