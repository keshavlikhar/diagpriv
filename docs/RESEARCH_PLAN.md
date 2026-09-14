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

The benchmark contains Incident Family 001: a timeout followed by a re-arrival
of the same logical operation, with missing or ineffective idempotency causing
two successful effects. Incident Family 002 is an offline construction in which
a reference-shape defect reaches an exact lookup and causes a missing
provisioning effect. All data is fictional and synthetic.

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
6. **HMAC baseline:** `hmac-v1` implemented, invariant-tested, and run on the
   five development seeds, producing 5/5 exact RCA.
7. **Deterministic tokenization:** `tokenization-v1` implemented,
   invariant-tested, and run on the five development seeds, producing 5/5 exact
   RCA.
8. **Format-preserving pseudonymization:** `format-preserving-v1` implemented,
   invariant-tested, and run on the five development seeds, producing 4/5 exact
   RCA. The only error was component localization; the protocol was not changed.
9. **Format-dependent benchmark construction:** Incident Family 002 implemented
   with versioned structural signatures, a canonical development fixture, shape
   ablation, anti-shortcut controls, and transformation expectation audits.
10. **Incident 002 raw qualification:** frozen six-seed development runs for
    GPT-5.6 Luna and GPT-5.6 Sol each produced 4/6 exact RCA. Sol corrected the
    Luna trigger/mechanism errors but showed two component-localization errors.
    These are development observations, not general conclusions.
11. **Matched privacy preparation:** all four existing privacy baselines are
    configured and invariant-audited together for the same Incident 002 seeds
    and GPT-5.6 Sol. No privacy-condition provider observation exists yet.

## Roadmap and decision gates

### 1. Format-dependent incident family

- Review and freeze Incident Family 002 before any provider experiment.
- Validate that its offline evidence requires the predeclared structural
  property and does not reveal the answer through wording or labels.
- Compare redaction, HMAC, tokenization, and format-preserving pseudonymization
  under the same frozen RCA protocol and a documented exposure model.

The current 4/5 format-preserving result is a development observation on an
incident that does not require format. It cannot establish incremental utility
over ordinary relationship-preserving pseudonymization.

### 2. DiagPriv task-aware selection

- Define a transformation policy that selects the minimum structural properties
  required by the troubleshooting task.
- Keep selection logic separate from oracle answers and prevent answer leakage.
- Add policy audit output explaining what was preserved without exposing
  sensitive plaintext or oracle labels to the model.
- Compare with fixed baselines before making superiority claims.

### 3. Harder and broader incident families

- Add multiple mechanisms, outcomes, triggers, subsequent actions, and affected
  components using the fixed taxonomy where it remains conceptually valid.
- Include incidents that require different invariant classes and plausible
  distractors, plus negative controls and ambiguous cases.
- Validate evidence sufficiency and difficulty with humans before large model
  experiments.
- Avoid families whose wording, service names, IDs, or data shape reveal the
  canonical answer.

### 4. Multi-model and repeated-call evaluation

- Preselect models, model/version metadata, reasoning settings, call counts, and
  failure policy.
- Use matched conditions and paired seed analysis.
- Add enough independent families and instances for uncertainty estimates;
  five- and ten-seed pilots are not inferential sample sizes.
- Evaluate response validity, exact RCA, each causal dimension, evidence quality,
  latency/token cost, and defined privacy-exposure metrics.
- Treat component ownership as a potentially model-sensitive dimension and
  measure its stability separately from outcome, trigger, action, and mechanism.

### 5. Protocol freeze and held-out evaluation

- Freeze benchmark generators, transformations, prompts, taxonomy, scorer,
  models, repetitions, analysis code, exclusion rules, and statistical plan.
- Record the freeze commit and artifact hashes.
- Only then authorize generation and provider use of seeds 20000–20999.
- Never use the retired 10000–10999 range.
- Report all attempted held-out calls and do not repair cases post hoc.

### 6. Paper preparation

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
