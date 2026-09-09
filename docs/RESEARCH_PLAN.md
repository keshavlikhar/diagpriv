# DiagPriv Research Plan

## Research objective

DiagPriv asks whether sensitive identity can be removed from operational
troubleshooting evidence without removing the structural information needed for
LLM root-cause analysis. The working hypothesis is that explicitly preserving
task-relevant diagnostic invariants will retain more RCA utility than generic
privacy transformations at comparable privacy exposure.

This is an empirical hypothesis. Software tests establish implementation
properties; pilot model results establish observations on specific synthetic
instances. Neither establishes production realism, general model capability, or
a privacy guarantee.

## Experimental unit and outcomes

The current experimental unit is one deterministic instance of a DiagBench
incident family under one evidence condition, prompt, model configuration, and
call index. Primary and secondary outcomes are defined in
`docs/EXPERIMENT_PROTOCOL.md`.

The current benchmark contains Incident Family 001: a timeout followed by a
re-arrival of the same logical operation, with missing or ineffective
idempotency causing two successful effects. All data is fictional and synthetic.

## Design principles

- Keep complete oracle data separate from the model-visible `ModelView`.
- Version prompts, taxonomies, scorers, transformations, pricing snapshots, and
  seed policy.
- Use paired seeds when comparing evidence conditions.
- Treat provider and parser failures as recorded infrastructure outcomes, not as
  silently missing observations.
- Preserve every completed observation append-only and publish its digest.
- Never tune against held-out evaluation instances.
- Separate software correctness, diagnostic utility, and privacy exposure.
- Do not infer research validity from a passing test suite.

## Completed milestones

1. **DiagBench v0.2 foundation:** versioned schemas, one deterministic incident
   family, model/oracle separation, diagnostic invariants, privacy annotations,
   nuisance variation, and protected seed ranges.
2. **Raw RCA harness:** provider-neutral invocation, fake and OpenAI adapters,
   structured parsing, deterministic scoring, append-only manifests, inspection,
   token accounting, and separate pricing estimates.
3. **RCA protocol v2:** fixed five-dimensional taxonomy and `raw-rca-v2` prompt,
   created after a development v1 response exposed an underspecified free-label
   taxonomy.
4. **Raw pilots:** development and validation observations completed and frozen.
5. **Naive redaction:** `redaction-v1` implemented, invariant-audited, and run on
   development seeds only.
6. **HMAC baseline:** `hmac-v1` implemented and invariant-tested offline. Its
   provider experiment has not been run.

## Roadmap and decision gates

### 1. HMAC development pilot

- Human-review the offline transform, namespace policy, threat model, key
  procedure, and exact development configuration.
- Provision one external experimental key without committing it.
- Execute seeds 1000–1004 once only after explicit approval.
- Freeze the JSONL and digest before interpreting or changing later methods.
- Decide whether results justify a separately approved validation comparison.

### 2. Deterministic tokenization baseline

- Define a versioned token vocabulary and collision/namespace behavior.
- Specify whether a lookup service or local mapping is part of the threat model.
- Measure equality, inequality, cardinality, and cross-source preservation.
- Complete offline tests and review before any provider call.

### 3. Format-preserving methods

- Add incident families where format is truly diagnostic before claiming a need
  for format preservation.
- Define exactly which syntactic properties survive and what additional
  attribute leakage they create.
- Compare against redaction, HMAC, and deterministic tokenization under a
  documented exposure model.

### 4. DiagPriv task-aware selection

- Define a transformation policy that selects the minimum structural properties
  required by the troubleshooting task.
- Keep selection logic separate from oracle answers and prevent answer leakage.
- Add policy audit output explaining what was preserved without exposing
  sensitive plaintext or oracle labels to the model.
- Compare with fixed baselines before making superiority claims.

### 5. Harder and broader incident families

- Add multiple mechanisms, outcomes, triggers, subsequent actions, and affected
  components using the fixed taxonomy where it remains conceptually valid.
- Include incidents that require different invariant classes and plausible
  distractors, plus negative controls and ambiguous cases.
- Validate evidence sufficiency and difficulty with humans before large model
  experiments.
- Avoid families whose wording, service names, IDs, or data shape reveal the
  canonical answer.

### 6. Multi-model and repeated-call evaluation

- Preselect models, model/version metadata, reasoning settings, call counts, and
  failure policy.
- Use matched conditions and paired seed analysis.
- Add enough independent families and instances for uncertainty estimates;
  five- and ten-seed pilots are not inferential sample sizes.
- Evaluate response validity, exact RCA, each causal dimension, evidence quality,
  latency/token cost, and defined privacy-exposure metrics.

### 7. Protocol freeze and held-out evaluation

- Freeze benchmark generators, transformations, prompts, taxonomy, scorer,
  models, repetitions, analysis code, exclusion rules, and statistical plan.
- Record the freeze commit and artifact hashes.
- Only then authorize generation and provider use of seeds 20000–20999.
- Never use the retired 10000–10999 range.
- Report all attempted held-out calls and do not repair cases post hoc.

### 8. Paper preparation

- Produce a reproducible artifact manifest and data dictionary.
- Report negative results, failure records, deviations, and confidence intervals.
- Separate claims about synthetic diagnostic utility from claims about privacy or
  production generalization.
- Document model/provider versions, dates, costs, and known non-determinism.
- Complete ethical, privacy, and release review before publishing artifacts.

## Decisions still required

- Formal privacy-exposure metrics and acceptable comparison levels.
- Whether HMAC linkability is evaluated within an incident, across sources,
  across incidents, or all three.
- Independent-instance generation and sample-size targets per family.
- Human baseline and inter-rater protocol.
- Multi-model selection, repetitions, and provider-failure handling.
- Statistical tests, paired effect sizes, intervals, and multiplicity treatment.
- Artifact distribution for ignored local JSONL files.
- Criteria for graduating a development condition to validation.
- Final held-out authorization and preregistration procedure.
