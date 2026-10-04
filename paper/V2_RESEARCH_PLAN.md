# DiagPriv Version 2 research plan

Version 1 is frozen as the Zenodo preprint published on October 4, 2026
(version DOI: 10.5281/zenodo.23142445). Version 2 is a stronger empirical
extension of the same research question, not a rewrite of the published record.

## Goal

Strengthen the evidence for the central DiagPriv question:

> To what extent can sensitive information be removed or pseudonymized from
> operational troubleshooting data without reducing LLM root-cause-analysis
> accuracy?

Version 2 should directly address the main limitations of Version 1:
small synthetic development sets, three incident families, one model family,
no human baseline, and no matched final held-out evaluation.

The target is an archival/conference-strength empirical paper while preserving
the calibrated claims and threat model of Version 1.

## Frozen Version 1 boundary

Version 1 results, hashes, and published artifacts are immutable evidence.

Version 2 must not:

- overwrite or reinterpret frozen Version 1 provider observations;
- silently rescore Version 1 under changed semantics;
- inspect Version 1 held-out seeds merely to guide benchmark design;
- replace the published Zenodo files in place;
- claim that new Version 2 evidence was available when Version 1 was published.

All Version 2 data, protocols, prompts, scorers, and result manifests must use
new version identifiers.

## Version 2 research questions

### RQ1 — Generalization across diagnostic dependencies

Do the privacy/utility tradeoffs observed in Version 1 persist across a broader
set of operational incident families with different required diagnostic
invariants?

### RQ2 — Generalization across model families

Are the observed transformation effects stable across multiple LLM model
families, or are they model-specific?

### RQ3 — Human difficulty and calibration

How difficult are the same cases for technically competent humans, and which
cases are intrinsically ambiguous versus model-specific failures?

### RQ4 — Held-out confirmation

Do the preregistered Version 2 hypotheses survive a final matched held-out
evaluation after protocol freeze?

### RQ5 — Exposure versus diagnostic utility

How does residual model-visible representation exposure trade off against RCA
utility across incident families and transformation conditions?

## Experimental expansion

### A. Incident-family expansion

Retain the three Version 1 families as historical anchors, but add new
synthetic families only when each isolates a distinct diagnostic dependency.

Candidate dependency classes:

1. **Cross-source linkage**
   - identity equality or stable pseudonymous joins are required.

2. **Reference or schema shape**
   - diagnosis depends on recognizable identifier or payload structure.

3. **Temporal order and overlap**
   - diagnosis depends on sequence, overlap, gap, deadline, or causal timing.

4. **Numeric relation**
   - diagnosis depends on relative magnitudes, thresholds, ratios, counters,
     balances, quotas, or monotonic changes rather than exact sensitive values.

5. **Cardinality / multiplicity**
   - diagnosis depends on one-to-many, duplicate count, fan-out, or missing
     member structure.

6. **State-transition consistency**
   - diagnosis depends on a lifecycle or state-machine relationship without
     requiring concurrency.

Do not add a family merely to increase sample size. Each family must document
its diagnostic invariant, intended privacy transform stressor, confound audit,
oracle, and failure criteria before provider calls.

### B. Transformation set

Keep Version 1 baselines where applicable:

- raw;
- redaction;
- HMAC;
- deterministic tokenization;
- format-preserving pseudonymization;
- relative time;
- temporal ablation.

Add new transformations only if they test a new invariant class. A likely
Version 2 addition is relationship-preserving numeric transformation, but its
semantics must be specified and audited before use.

### C. Model-family expansion

Target at least three independently meaningful model families/configurations
for the final Version 2 comparison.

Requirements:

- freeze exact model identifiers and dates;
- use the same task prompt and scoring protocol where technically possible;
- record transport failures separately from model answers;
- do not silently substitute models after protocol freeze;
- treat model-family comparisons as empirical generalization, not vendor
  ranking.

No provider calls are authorized by this plan alone. Every real provider run
still requires explicit approval.

### D. Human baseline

Run a small blinded human baseline on a stratified subset after the benchmark
and rubric are frozen.

The human task should mirror the model task as closely as practical:

- same visible evidence condition;
- same RCA dimensions;
- same evidence-support requirement;
- no oracle access;
- independent responses before adjudication.

Primary purpose: identify intrinsically hard/ambiguous cases and calibrate the
interpretation of model failures. The human study is not intended as a
competitive "humans vs AI" leaderboard.

### E. Final held-out evaluation

Create a new Version 2 seed policy with separate:

- development;
- qualification/validation;
- final held-out.

The final held-out split must remain unseen until:

1. family generators are frozen;
2. transformations are frozen;
3. prompt/taxonomy/scorer are frozen;
4. hypotheses and primary comparisons are written;
5. model configurations are frozen;
6. exclusion and transport-recovery rules are frozen;
7. the statistical analysis plan is frozen.

No tuning after held-out inspection. Any post-hoc analysis must be labeled as
such and kept separate from the primary result.

## Statistical plan

Version 2 should move beyond descriptive counts while respecting the paired
design.

Primary analysis should emphasize:

- paired case-level comparisons between raw and transformed conditions;
- confidence intervals for exact RCA and dimension-level accuracy;
- paired uncertainty estimates for matched target/twin or analogous contrasts;
- effect sizes by incident family and transformation;
- model-family heterogeneity;
- predeclared handling of missing/transport-failed responses.

Avoid pretending that repeated calls on the same synthetic construction are
independent benchmark examples.

The exact inferential method should be frozen before final held-out access.
A hierarchical or clustered analysis may be appropriate because observations
are nested within incident construction, family, transformation, and model.

## Evidence support and exposure

Keep RCA correctness, evidence support, and representation exposure as
separate outcomes.

Version 2 should preserve the Version 1 exposure-vector philosophy:

- no single "privacy score";
- no anonymity claim;
- no differential-privacy claim;
- no legal de-identification claim;
- no zero-reidentification claim.

If attack-based re-identification evaluation is added, report it as a separate
empirical outcome rather than folding it into the exposure vector.

## Version 2 claim target

A successful Version 2 may support a statement of the form:

> Across multiple diagnostic dependency classes and model families, privacy
> transformations that preserve the task-relevant diagnostic relationships
> retain more RCA utility than transformations that remove those relationships,
> with the strength and failure mode depending on the incident family and
> model.

This claim is conditional on the final preregistered evidence. It must not be
written as a conclusion before the final analysis.

## Explicitly out of scope for Version 2

To keep the paper scientifically coherent, Version 2 should not also become the
automatic transformation-planner paper.

Defer to separate follow-on work:

- automatic task-aware transform selection;
- a production gateway/MCP service;
- enterprise deployment architecture evaluation;
- adversarial prompt injection;
- malicious agents;
- formal privacy guarantees;
- comprehensive re-identification attack benchmarking.

Those are separate research questions and can become later papers.

## Proposed execution phases

### Phase 0 — Freeze and protocol design
- preserve Version 1 artifacts unchanged;
- define Version 2 seed ranges and artifact namespaces;
- finalize Version 2 research questions;
- draft the statistical analysis plan;
- define stop/go criteria for candidate incident families.

### Phase 1 — New-family construction
- implement one family at a time;
- audit for unintended diagnostic shortcuts;
- verify the intended invariant offline;
- reject weak or confounded families before provider calls.

### Phase 2 — Development qualification
- run only explicitly approved development experiments;
- qualify prompts/scorers/model configurations;
- perform evidence-semantic audits;
- freeze primary Version 2 protocol.

### Phase 3 — Cross-model development replication
- run the frozen development matrix across selected model families;
- inspect model heterogeneity;
- make only protocol-level corrections that are documented before held-out.

### Phase 4 — Human baseline
- execute the blinded human subset;
- adjudicate rubric ambiguity;
- freeze any interpretation rules before final held-out.

### Phase 5 — Preregistered final held-out
- lock repository state and analysis plan;
- run the final held-out matrix once;
- preserve raw observations append-only;
- produce the primary tables from frozen manifests.

### Phase 6 — Version 2 manuscript
- update the paper around the preregistered evidence;
- retain Version 1 as historical provenance;
- rebuild reproducibility artifacts;
- publish a new Zenodo version only after full review.

## Immediate next milestone

Before any new model call, complete a Version 2 protocol package containing:

1. Version 2 seed/split policy.
2. Candidate Family 004 specification.
3. Version 2 statistical analysis plan.
4. Model-family selection criteria.
5. Human-baseline protocol update.
6. Frozen-artifact namespace and provenance rules.

The first implementation target should be **Family 004: numeric-relation
dependency**, because it adds a genuinely new invariant class not directly
tested by the three Version 1 families.
