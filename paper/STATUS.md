# DiagPriv preprint status

Publication title: *DiagPriv: Preserving Diagnostic Structure While Reducing Sensitive Data Exposure in LLM Root-Cause Analysis*.

All required narrative sections are drafted: abstract, introduction, threat
model, formulation, transformation framework, methodology, family designs,
results, privacy--utility, evidence support, limitations, related work, and
conclusion. Tables 1--5, an additional family-specific temporal-exposure
table, and Figures 1--3 have source files. Tables and the paired-count figure
are regenerated from frozen development data and the merged exposure artifact.

## Preprint publication

The development-stage preprint was published on Zenodo on October 4, 2026:

- Record: https://zenodo.org/records/23142445
- Version DOI: 10.5281/zenodo.23142445
- All-versions DOI: 10.5281/zenodo.23142444
- Version: v1
- License: CC BY 4.0

The internal adversarial scientific review (#49) and team-executed clean-room
reproducibility review (#50) were completed before publication. Neither is
represented as an independent external collaborator review.

## Follow-up work and release boundaries

- **Literature:** an initial primary-source-verified pass is complete in
  `references.bib` and `RELATED_WORK_REVIEW.md`; the related-work prose now
  cites clinical de-identification, pre-release prompt transformation,
  task-sensitive anonymization, RCA, grounding, and temporal evaluation.
  Venue-specific coverage and citation polish remain. Adaptive anonymization
  and evidence-grounded RCA are established prior areas, so the manuscript
  makes no priority claim for either. RCAgent's internally deployed model is
  an explicit privacy-aware RCA alternative.
- **Artifacts:** the tracked repository provides Level-1 reproducibility.
  `docs/FROZEN_ARTIFACT_ARCHIVE_RFC.md`, the manifest, and provider-free
  verifier design Level-2 exact-byte verification, but no private archive is
  provisioned and no JSONL has been distributed. Level 3 public
  observation-level reproduction is not available.
- **External validity:** human difficulty/annotation baselines, broader
  incident/model families, and a preregistered final held-out evaluation are
  strengthening work for a later archival/conference version rather than
  prerequisites for an honestly scoped development-stage preprint. Incident
  001's raw-only validation is not a matched privacy comparison.
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
