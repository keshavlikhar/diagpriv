# Current Status

Last updated: 2026-09-18.

## Handoff point

Incident 002 experimentation is complete for the current development stage.
The frozen Sol raw observation, four matched privacy conditions, two added
trials per seed-condition, and the separately labeled transport-recovery
sensitivity attempt are complete. All observations remain immutable. The final
primary and sensitivity findings, interpretation limits, and complete artifact
ledger are frozen in `docs/INCIDENT_002_FINAL_FINDINGS.md`.

No format-preserving validation or held-out provider observation exists. Do not
rerun the development observation or tune the transformation after its 4/5
result. Incident 002 construction is restricted to development seeds. The
seed-selection scan generated seeds 1000–1017 while applying the frozen
first-occurrence rule; it did not generate or inspect validation or held-out
instances.

Incident 003 v1 raw GPT-5.6 Sol qualification is complete and frozen. Its eight
mechanically selected development seeds were 1000, 1001, 1002, 1003, 1004,
1015, 1017, and 1018 under
`incident-003-first-two-per-temporal-template-v1`. The run produced 8/8 valid
responses but 0/8 exact RCA under the frozen v2 taxonomy because every response
selected `incorrect_concurrency_control` instead of the v1 oracle's
`incorrect_state_transition`. Outcome, trigger, action, and component were each
correct in 8/8. The run has not been retroactively rescored.

Offline adjudication classified the systematic disagreement as **B. Taxonomy
ambiguity**, driven substantially by taxonomy-definition insufficiency. RCA v3
and Incident 003 v2 are implemented. The fresh raw v3 Sol run is frozen at 8/8
valid and 8/8 exact five-label RCA, while `evidence_supported` and
`overall_correct_v3` are 0/8 under the unchanged evidence-support-v3 rubric.
Its ignored JSONL SHA-256 is
`54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915`.

The matched `relative-time-v1` GPT-5.6 Sol development run is complete and
frozen: 8/8 valid responses, 8/8 exact five-label RCA, 1/8
`evidence_supported`, and 1/8 `overall_correct_v3`. All eight raw-correct cases
remained correct after absolute timestamps were replaced by exact
incident-relative millisecond offsets. The ignored result SHA-256 is
`0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb`.
See
`docs/INCIDENT_003_RELATIVE_TIME_V1_FINDINGS.md` for the frozen comparison.

The frozen `temporal-ablation-v1` negative-control run then produced 8/8 exact
RCA on the same seeds even though all temporal relations were unavailable.
Evidence-support-v4 scored only 0.041667 essential coverage, 0/8
evidence-supported, and 0/8 overall correct. Its ignored JSONL SHA-256 is
`aebe64d289c9a0f1d201a8066e6678b0c386bcfaf07026eb73377bc475432922`.
The supported interpretation is that Incident 003 v2 remains solvable from
surviving non-temporal cues on these eight development cases; it does not
isolate temporal reasoning strongly enough for the intended causal claim.

A deterministic 200-instance cue audit found perfect target/control
separability from terminal-state fields, record-type presence, or event-kind
sets alone. The target-only tuple was compensated workflow + successful
execution + active effect + compensation record. Explicit deadline and
compensation vocabulary and near-label orchestrator roles add further
shortcuts. See `docs/INCIDENT_003_TEMPORAL_ABLATION_FINDINGS.md`.

The four remaining destructive configs stay preregistered and frozen, but
their execution is **PAUSED — pending benchmark-cue investigation**. No
validation or held-out Incident 003 observation exists.

Incident 003 v3 is now an offline, separately versioned causal-isolation
candidate under `incident-003-generator-v3` and
`incident-003-temporal-protocol-v3`. Each queried target has an exact
non-temporal temporal twin: the target has execution/compensation overlap,
while the twin has a serialized state-transition defect. Across development
seeds 1200–1399, all 200 pairs have equal non-temporal projections, all four v2
signature families collide in 200/200 pairs, and no audited single feature or
known 2/3/4-feature conjunction separates target from twin. Raw and
relative-time evidence-v4 obligations are satisfiable; temporal ablation makes
the four causal temporal obligations unavailable. Those statements describe
the offline benchmark-construction phase. The paired provider protocol was
subsequently prepared, and raw Stage 1 is now complete and frozen. The matched
Incident 003 v3 `relative-time-v1` Stage 2 and `temporal-ablation-v1` Stage 3
remain unexecuted. See `docs/INCIDENT_003_V3_CAUSAL_ISOLATION_PROTOCOL.md`.

The final identifier/position audit initially found a blocking fixed raw-log
order: target, temporal twin, then safe control. The approved offline correction
keeps logs globally chronological but allocates each operation's absolute time
window through a dedicated role-neutral deterministic RNG stream. Across 200
constructions, every hidden role now occupies every block position and no
positional separator remains.

V3 also supports paired target and temporal-twin queries over byte-identical
evidence serialization. Their scored RCA labels differ only in mechanism:
`incorrect_concurrency_control` versus `incorrect_state_transition`. Raw and
relative-time evidence obligations are satisfiable for both roles in 200/200;
after temporal ablation the rendered pair is structurally isomorphic and
neither mechanism-specific rubric is satisfied, while the hidden mechanism
oracles conflict. All original and updated offline gates pass. Four
constructions selected by the content-independent hash rule yield eight cases
per condition under raw, `relative-time-v1`, and `temporal-ablation-v1`.
Manifest v11 records case role and evidence-dispatch provenance; all 24
model-input hashes and eight transformation-independent rubric hashes are
frozen. The raw Stage-1 observation is complete and frozen: 8/8 valid, 7/8
exact RCA, and 0/8 evidence-supported under frozen evidence-support-v4. The
sole RCA error is `1222:temporal_twin`. See
`docs/INCIDENT_003_V3_PAIRED_QUALIFICATION_PROTOCOL.md`.

Evidence-support-v5 is now an offline candidate developed post hoc from the
Stage-1 forensic audit. It adds generic structured/log alternatives while
retaining subject binding and strict semantic predicates. The final parity
review aligned three remaining structured/log obligations: active effect before
deadline before compensation start; successful active effect with compensated
workflow; and successful execution completion before compensation start. Across
seeds 1200–1399, complete raw and relative-time structured/log proofs pass
200/200 per query role; temporal ablation, wrong-role evidence, and safe-control-
as-failure proof are rejected 200/200. An explicit secondary rescore recognizes
3/8 Stage-1 responses as evidence-supported. All four target responses lack a
complete four-endpoint positive-overlap citation path;
`1299:temporal_twin` remains unsupported for two serialized-transition
obligations, and `1222:temporal_twin` remains the sole RCA mechanism failure.
The parity correction did not change the 3/8 secondary result. These are
post-hoc development findings, not experimental validation; v4 remains the
frozen Stage-1 primary score, and prospective v5 use requires separate approval.
Relative-time Stage 2 and temporal-ablation Stage 3 remain unexecuted. See
`docs/EVIDENCE_SUPPORT_V5_METHODOLOGY.md` and
`docs/INCIDENT_003_V3_STAGE1_EVIDENCE_V5_ANALYSIS.md`.

## Frozen Incident 003 v1 raw qualification

The development-only raw Sol observation produced:

| Metric | Result |
|---|---:|
| Valid responses | 8/8 |
| Exact RCA under v2 | 0/8 |
| `overall_correct` under v2 | 0/8 |
| Observed outcome | 8/8 |
| Trigger | 8/8 |
| Subsequent action | 8/8 |
| Failure mechanism | 0/8 |
| Affected component | 8/8 |
| Evidence precision | 0.083333 |
| Evidence recall | 0.071429 |
| Evidence F1 | 0.076923 |

All eight responses recovered the deadline, compensation, overlap, late-success,
inconsistent-state, and orchestrator-ownership chain. The disagreement was the
mechanism label. Seven responses cited valid alternative lifecycle logs rather
than the single frozen structured-row evidence path. Citation coverage was
incomplete, but the exact-ID rubric also omitted semantically equivalent paths.
No cited ID was nonexistent.

The local ignored artifact has SHA-256
`4f24b8a5bb593fb491307544796bc6d75b85c32b761e5ee09d79bdb802e8f66b`.
The raw run remains 0/8 exact under v2 and must not be regenerated, relabelled,
or presented as a successful exact qualification.

The implemented v3 mapping changes only Incident 003's mechanism to
`incorrect_concurrency_control`. Its fresh development
set is 1019, 1020, 1021, 1022, 1023, 1025, 1026, and 1028 under
`incident-003-v2-first-two-per-temporal-template-unobserved-v1`. Those seeds
were used once for the frozen raw v3 qualification. The protocol identifiers are
`raw-rca-v3`, `rca-taxonomy-v3`, `raw-rca-scorer-v3`,
`evidence-support-v3`, and `raw-rca-manifest-v9`; the prompt-template SHA-256 is
`a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`.

Incident 003 v2 is a versioned wrapper over the frozen v1 construction. For a
given seed its ModelView, invariants, and temporal ablation are unchanged. It
keeps the historical v2 oracle intact and adds a separate v3 oracle whose
mechanism is `incorrect_concurrency_control`. This prevents the v1 result from
being relabelled or rescored in place.

The final offline hardening separates the family-neutral evidence evaluator
from the Incident 003 v2 rubric builder, preregisters canonical per-seed rubric
hashes alongside model-input hashes, enforces subject bindings, and applies a
conservative wrong-subject veto for the flat citation list. Manifest v9 now
requires generator version, protocol version, and evidence requirement-set
SHA-256. The completed fresh raw qualification, matched relative-time
observation, and temporal-ablation negative control remain immutable.

## Frozen Incident 003 v2 matched temporal result and prepared negative controls

Raw and `relative-time-v1` both achieved 8/8 exact RCA on the same eight
development seeds. Every transformed response selected `inconsistent_state`,
`timeout_or_deadline`, `compensation_or_rollback`,
`incorrect_concurrency_control`, and `workflow_orchestrator`; none selected
`incorrect_state_transition`.

Citation completeness remains substantially weaker than label accuracy. Raw
essential coverage was 19/48 and relative-time coverage was 23/48; raw had
0/8 evidence-supported diagnoses and relative time had 1/8. Relative-time
useful citation precision was 34/40, with zero invalid, wrong-subject, or
redundant citations. These differences are descriptive development findings,
not statistically significant evidence.

The supported statement is limited to: on these eight fresh matched Incident
003 development cases with GPT-5.6 Sol, replacing absolute timestamps with
exact incident-relative millisecond offsets preserved all five RCA dimensions.
It does not establish validation or held-out performance, other-model
behavior, anonymity, or superiority over destructive transformations.

The preregistered directional hypothesis was
`Raw approximately equals Relative-time-v1 > Temporal-ablation-v1`, with
redaction, HMAC, tokenization, and format-preserving pseudonymization as
supporting destructive baselines. Temporal ablation instead remained 8/8 exact,
while evidence support fell to 0/8. The remaining four runs are paused rather
than interpreted without first addressing the demonstrated shortcut cues.

## Frozen Incident 002 development seeds

Starting at 1000, seeds were inspected in ascending order and selected only
when they introduced a previously unseen hidden generator-side defect class.
The scan stopped as soon as all six classes were represented. The procedure is
versioned as `incident-002-first-defect-class-occurrence-v1`.

| Seed | Defect class | Structural template | Observable delta |
|---:|---|---|---|
| 1000 | `extra_separator` | `hyphenated_mixed_b` | `extra_separator` |
| 1001 | `missing_separator` | `hyphenated_mixed_b` | `missing_separator` |
| 1003 | `case_class_mismatch` | `underscored_mixed` | `case_class_mismatch` |
| 1004 | `truncation` | `slashed_mixed` | `truncation` |
| 1005 | `leading_zero_loss` | `slashed_mixed` | `numeric_run_leading_position_deletion` |
| 1017 | `fixed_width_mismatch` | `slashed_mixed` | `fixed_width_mismatch` |

This set is frozen for all future matched Incident 002 development conditions.
It was not selected using model or transformation behavior and must not change
in response to future results.

The prepared raw pilot uses `raw-rca-v2`, `rca-taxonomy-v2`,
`raw-rca-scorer-v2`, GPT-5.6 Luna, medium reasoning, omitted temperature, and
one call for each of these seeds. It uses manifest schema v6, whose new
`model_input_sha256` field hashes the exact rendered model-visible prompt. The
historical `prompt_sha256` template-hash meaning remains unchanged.

## Frozen Incident 002 Luna raw observation

The development-only Luna run is a diagnostic observation, not a general
conclusion. It produced 6/6 valid responses, 4/6 exact RCA, and 4/6
`overall_correct`. Outcome and subsequent action were correct in 6/6, trigger
and failure mechanism in 4/6, and affected component in 5/6. Average evidence
precision was 0.6750, recall 0.3125, and F1 approximately 0.423271. There were
no provider, parser, rate-limit, or refusal failures.

Seeds 1001 (`missing_separator`) and 1017 (`fixed_width_mismatch`) favored a
dependency/retry explanation rather than the format/input-handling oracle. This
result must not be rerun or used to revise the benchmark or protocol.

The local append-only result has SHA-256
`43004a011443fd2b2ca1789e4ce57198484b8cad01e50f80b240679148d6b425`.
It remains ignored and untracked.

## Frozen Incident 002 Sol raw qualification

The matched GPT-5.6 Sol run produced 6/6 valid responses, 4/6 exact RCA, and
4/6 `overall_correct`. Outcome, trigger, subsequent action, and failure
mechanism were correct in 6/6; affected component was correct in 4/6. Evidence
precision was 0.8056, recall 0.2500, and F1 0.3768. Seeds 1000 and 1017 selected
`request_ingress` rather than oracle `operation_executor`; no other RCA
dimension was incorrect. No provider, parser, rate-limit, or refusal failure
occurred.

The local append-only result has SHA-256
`b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f`.
It remains ignored and untracked. This development observation must not be
rerun or used to revise the benchmark or protocol.

## Frozen Incident 002 privacy comparison: trial 1

The first complete Sol comparison is an immutable single-trial development
observation:

| Condition | Trigger | Failure mechanism | Exact RCA |
|---|---:|---:|---:|
| Raw | 6/6 | 6/6 | 4/6 |
| Redaction v1 | 2/6 | 2/6 | 0/6 |
| HMAC v1 | 0/6 | 0/6 | 0/6 |
| Tokenization v1 | 1/6 | 1/6 | 0/6 |
| Format-preserving v1 | 4/6 | 4/6 | 2/6 |

The assessment is **mixed, with directional support for the preregistered
hypothesis**. It is not confirmation or a statistically significant result.
See `docs/INCIDENT_002_REPEATED_TRIALS.md` for the frozen artifact hashes and
the preregistered two-call extension to three total trials per seed-condition.

## Frozen Incident 002 repeated-trial and recovery results

The primary as-executed result has 80 valid responses across 90 planned
observations, including trial 1. Ten transport failures remain missing RCA
observations; none was retried or replaced. The assessment is **mixed / unstable**.

| Condition | Valid /18 | Trigger correct | Mechanism correct | Exact RCA | Overall correct |
|---|---:|---:|---:|---:|---:|
| Raw | 18 | 15 | 15 | 9 | 9 |
| Redaction v1 | 9 | 2 | 2 | 0 | 0 |
| HMAC v1 | 18 | 1 | 1 | 1 | 1 |
| Tokenization v1 | 17 | 2 | 2 | 0 | 0 |
| Format-preserving v1 | 18 | 10 | 10 | 4 | 4 |

Counts are observed correct answers across the 18 planned slots per condition;
missing provider responses are not incorrect model diagnoses. Nine failures
were redaction transport failures; one was a tokenization timeout. There were
no parser, rate-limit, or refusal failures. All 60 model-input hashes matched
trial 1. The original repeated-trial artifact hashes are frozen in the recovery
protocol and its configuration.

The separately preregistered recovery attempted each of those ten cells once
and produced 10/10 valid responses. Recovery achieved 0/10 correct trigger,
0/10 correct failure mechanism, 0/10 exact RCA, and 7/10 correct component,
with no recovery failure and no second attempt. The sensitivity view therefore
contains 18 valid observations per condition:

| Condition | Valid | Trigger | Failure mechanism | Exact RCA | Component |
|---|---:|---:|---:|---:|---:|
| Raw | 18/18 | 15/18 | 15/18 | 9/18 | 12/18 |
| Redaction-v1 | 18/18 | 2/18 | 2/18 | 0/18 | 10/18 |
| HMAC-v1 | 18/18 | 1/18 | 1/18 | 1/18 | 13/18 |
| Tokenization-v1 | 18/18 | 2/18 | 2/18 | 0/18 | 13/18 |
| Format-preserving-v1 | 18/18 | 10/18 | 10/18 | 4/18 | 10/18 |

The recovery records are sensitivity-analysis substitutions only. They do not
revise the primary table above or replace the original failure records. See
`docs/INCIDENT_002_FINAL_FINDINGS.md` for evidence metrics, scientific
interpretation, and artifact hashes.

## Frozen Incident 001 protocol

- Benchmark: DiagBench `0.2`, Incident Family 001.
- Prompt: `raw-rca-v2`.
- Prompt-template SHA-256:
  `744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d`.
- Taxonomy: `rca-taxonomy-v2`.
- Scorer: `raw-rca-scorer-v2`.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `medium`.
- Temperature: originally intended as zero, but omitted because the provider
  rejected the parameter for this model/configuration.
- Calls per seed: one.

The historical field `prompt_sha256` records the frozen prompt-template bytes,
not the rendered prompt containing a particular ModelView. See
`docs/EXPERIMENT_PROTOCOL.md` for the compatibility and future-provenance note.

Exact RCA v2 requires all five canonical dimensions to be correct:
`observed_outcome`, `trigger`, `subsequent_action`, `failure_mechanism`, and
`affected_component`. `overall_correct` additionally requires supported
evidence under the frozen deterministic evidence scorer.

## Frozen observations

These are small development/validation observations, not general research
conclusions.

| Condition | Seeds | Valid | Exact RCA | Status |
|---|---:|---:|---:|---|
| Raw v2 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Raw v2 validation | 2000–2009 | 10/10 | 10/10 | Frozen; 9/10 overall |
| Redaction v1 development | 1000–1004 | 5/5 | 4/5 | Frozen |
| HMAC v1 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Tokenization v1 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Format-preserving v1 development | 1000–1004 | 5/5 | 4/5 | Frozen |

For `format-preserving-v1`, outcome, trigger, subsequent action, and failure
mechanism were each correct in 5/5 cases. Seed 1000 was the only exact-RCA miss:
the response selected `request_ingress` rather than the oracle
`operation_executor`. Evidence precision was 1.0000, recall was approximately
0.742857, and F1 was approximately 0.848018. Total usage was 23,918 tokens and
estimated cost under the configured pricing snapshot was $0.00840885. No
provider, parser, rate-limit, or refusal failure occurred.

The component disagreement is retained as an observation. It does not justify
changing the oracle or any post-observation protocol element.

## Component-ownership interpretation

The v2 prompt defines `affected_component` as the architectural role that owns
the failure mechanism, not a component that merely reports a symptom. Incident
001 shows the ingress/edge handler accepting arrivals and reporting the
caller-facing deadline. The operation executor/payment worker then persists two
distinct successful effects for the same logical request. Missing or ineffective
idempotency is therefore assigned to `operation_executor`: that is the role that
must prevent a repeated arrival from producing the second durable effect.

`request_ingress` is nevertheless a plausible model-sensitive localization
because it observes the timeout and accepts the re-arrival. Component ownership
should be evaluated across models and repeated trials after the protocol is
extended; it may be less stable than outcome, trigger, subsequent action, or
mechanism. This is a research caution, not an oracle revision.

## Frozen local artifact ledger

Experiment JSONLs are ignored by Git and remain local append-only research
records. Their contents must not be edited or regenerated under the same
experiment IDs.

| Artifact | SHA-256 |
|---|---|
| `results/raw_pilot_v2_gpt_5_6_luna_medium.jsonl` | `dbf72a9a3d3e33e510622e3eab9df11d4e5c138d35fb89c6ed04e1ccdde4ab2b` |
| `results/raw_pilot_v2_validation_gpt_5_6_luna_medium.jsonl` | `c9d4cfa93c3176590ad820484266843c464e8a58f92994beebf7d10548c6028e` |
| `results/redaction_v1_development_gpt_5_6_luna_medium.jsonl` | `b3a885a65e9369a26e9cdb69b7fcc1244739cee0812d6313040a3f03203b1559` |
| `results/hmac_v1_development_gpt_5_6_luna_medium.jsonl` | `063137ee4c29d5f2ef0c6688754a485822b45d4434b4c16cdb0f2476a36508e3` |
| `results/tokenization_v1_development_gpt_5_6_luna_medium.jsonl` | `acb9d5fb53b8177c6b5dac954569fda6c0b74f25b7e479f6b393cc0ce33b6695` |
| `results/format_preserving_v1_development_gpt_5_6_luna_medium.jsonl` | `3b32fff6fc7604afec2e467f18f850ffafa89c63633e0155b8cfc397fa9e1fa9` |
| `results/incident_002_raw_development_gpt_5_6_luna_medium.jsonl` | `43004a011443fd2b2ca1789e4ce57198484b8cad01e50f80b240679148d6b425` |
| `results/incident_002_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f` |
| `results/incident_002_redaction_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `aaaad02bc5bdaa6dd07cbe5785d92d6a38e9475b34bf13c4191a52072e611f33` |
| `results/incident_002_hmac_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `20f91837846ed9bac0d50d09671aee4166033e58d51622aed6905a628edb71ad` |
| `results/incident_002_tokenization_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `f6d0f56f65d44140692a6d5a3eebff6a662897356346d8872b4a804e55d694d3` |
| `results/incident_002_format_preserving_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `03cce974a6ac2ad9f5d7d393ab6b139fcbb6072d44ccb8a080e1a73056661fa0` |
| `results/incident_002_raw_sol_repeated_trials_2_3.jsonl` | `ad8d8e059efdea20c7a25f325c1bf3f3ae5e65b7c2eb7eef6953f0039528026a` |
| `results/incident_002_redaction_v1_sol_repeated_trials_2_3.jsonl` | `56f43a72ce4bdf8160cade695bfc83995ef29846ebbe0b10d887b6b87040ee15` |
| `results/incident_002_hmac_v1_sol_repeated_trials_2_3.jsonl` | `b2fda91b0c958dcc11e405c30c4431a982735070f1667b86b155415f407f1b31` |
| `results/incident_002_tokenization_v1_sol_repeated_trials_2_3.jsonl` | `441a603bb1e31f373ac4920eaf31e0882d3538f833b683e1c159f2ec7cde11df` |
| `results/incident_002_format_preserving_v1_sol_repeated_trials_2_3.jsonl` | `cb1b17e8ad57ce4788ddb3d37e5249fde27263d912f16f03664dc506956df318` |
| `results/incident_002_sol_transport_recovery.jsonl` | `87902fa3217aaca020cb2cd2df14effc19c8c97a6f823031ed171a6f0ef4747e` |
| `results/incident_003_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `4f24b8a5bb593fb491307544796bc6d75b85c32b761e5ee09d79bdb802e8f66b` |
| `results/incident_003_v2_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915` |
| `results/incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb` |
| `results/incident_003_v2_temporal_ablation_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `aebe64d289c9a0f1d201a8066e6678b0c386bcfaf07026eb73377bc475432922` |

Earlier raw-v1 HTTP failures and the seed-1000 taxonomy diagnostic remain local
infrastructure/development history. The HTTP 400 attempts are not RCA
observations. The v1 taxonomy finding motivated a separately versioned v2
protocol; v1 was not overwritten.

## Methodological interpretation

Incident 001 requires equality, inequality, cross-source identity, ordering,
success state, amount equality, and row cardinality. It does not require
sensitive-value format for diagnosis. Consequently, the current result cannot
establish whether format preservation adds utility beyond ordinary
relationship-preserving pseudonymization.

Incident Family 002 makes visible external-reference structure explicitly
necessary for its intended RCA by combining one shape anomaly with healthy
controls and non-unique lookup-miss/latency/dependency distractors. Repeated
development observations provide directional support for the diagnostic-
invariant hypothesis, but do not establish causality, statistical significance,
general model behavior, Raw ≈ Format-preserving, or a universal method ranking.
Its initial defect set is limited to transformations already represented by
`format-preserving-v1`; semantic and check-digit defects remain out of scope.

Incident 003's matched development result shows complete five-label RCA
preservation for exact relative millisecond offsets on eight GPT-5.6 Sol cases.
The temporal-ablation negative control also remained 8/8 exact despite removing
temporal semantics, demonstrating that v2 can be solved through non-temporal
shortcut cues. This blocks the intended causal interpretation. The four
supporting destructive baselines remain paused pending a separately versioned
benchmark repair; their configs are retained unchanged.

## Immediate prohibitions

- Do not rerun or edit any frozen development/validation observation.
- Do not run privacy baselines on validation seeds without separate approval.
- Do not generate or inspect held-out seeds 20000–20999.
- Never use retired seeds 10000–10999.
- Do not modify frozen prompts, taxonomies, scorers, generator behavior, oracle,
  evidence definitions, model configuration, or completed JSONLs in place.
- Do not infer research validity from passing tests or five-instance results.
- Do not implement DiagPriv as a silent extension of a baseline protocol.

## Known limitations

- Incident 002 has three logical trials on six development seeds per condition.
  The primary analysis retains ten transport failures; later valid recovery
  responses appear only in a separate sensitivity analysis. Neither view can
  establish generality, statistical significance, or causality.
- Evidence-overlap metrics did not track causal correctness, and component
  ownership remained model-sensitive.
- Format-preserving seed 1005 missed the causal explanation in all three trials
  despite all applicable declared structural invariants being preserved.
  Invariant preservation is not demonstrated to be sufficient for reliable
  model use.
- Development and validation samples are small and generated by one family.
- No human difficulty or evidence-sufficiency study has been completed.
- Provider determinism is not guaranteed even with fixed input and one call.
- Component ownership may be more interpretation-sensitive than other RCA
  dimensions.
- Result artifacts are local/ignored; a collaboration-safe distribution policy
  remains to be chosen.
- Incident 003 v1 raw qualification failed exact RCA under the frozen v2
  taxonomy despite recovering the temporal chain. The accepted ambiguity and
  prospective v3 methodology are development findings, not a retroactive score
  correction or empirical v3 qualification.
- Incident 003 v2 raw, relative time, and temporal ablation each achieved 8/8
  exact RCA. Temporal ablation nevertheless had 0/8 evidence-supported
  responses and exposed perfect non-temporal target/control separability in an
  offline 200-instance audit. The result is a benchmark-cue finding, not
  evidence that temporal reasoning is unnecessary.
