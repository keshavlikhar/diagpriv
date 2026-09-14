# Current Status

Last updated: 2026-09-13.

## Handoff point

PR #6 has merged the Luna raw-development preparation checkpoint into `main`.
The frozen Sol raw-qualification preparation is commit `71af881`, and its six
completed observations are preserved locally. The stacked branch
`experiment/incident-002-privacy-development` prepares all four matched privacy
conditions together without making a privacy-condition provider call.

No format-preserving validation or held-out provider observation exists. Do not
rerun the development observation or tune the transformation after its 4/5
result. Incident 002 construction is restricted to development seeds. The
seed-selection scan generated seeds 1000–1017 while applying the frozen
first-occurrence rule; it did not generate or inspect validation or held-out
instances.

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

## Prepared Incident 002 privacy comparison

Four separate GPT-5.6 Sol development configurations now preregister
`redaction-v1`, `hmac-v1`, `tokenization-v1`, and `format-preserving-v1` on the
same six seeds. All use medium reasoning, omitted temperature, the frozen v2
prompt/taxonomy/scorer, schema v6, and one call per seed. Exact transformed
`model_input_sha256` values are frozen and verified before provider setup.
HMAC additionally verifies the established non-secret key fingerprint. See
`docs/INCIDENT_002_PRIVACY_COMPARISON.md` for the invariant matrix, provenance,
hypothesis, and proposed artifacts. No privacy-condition result exists.

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

Incident Family 002 now makes visible external-reference structure explicitly
necessary for its intended RCA by combining one shape anomaly with healthy
controls and non-unique lookup-miss/latency/dependency distractors. It is an
offline construction under review, not evidence that format preservation
improves model utility. Its initial defect set is limited to transformations
already represented by `format-preserving-v1`; semantic and check-digit defects
remain out of scope.

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

- Incident 002 has only six raw observations per model and no privacy-condition
  provider observations. Current scores cannot establish generality or the
  utility of format preservation.
- Development and validation samples are small and generated by one family.
- No human difficulty or evidence-sufficiency study has been completed.
- Provider determinism is not guaranteed even with fixed input and one call.
- Component ownership may be more interpretation-sensitive than other RCA
  dimensions.
- Result artifacts are local/ignored; a collaboration-safe distribution policy
  remains to be chosen.
- The evaluation registry currently supports only Incident Families 001 and
  002; adding another family requires explicit routing and seed-policy review.
