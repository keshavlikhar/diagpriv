# Incident 003 v3 temporal-ablation Stage-3 development observation

Issue #39 authorized one execution of the prospective evidence-support-v5
protocol prepared in issue #38 and merged through PR #40. This is a frozen
**development-only** observation. No answer was retried or replaced; the
benchmark, prompt, taxonomy, scorer, evidence protocol, transformation, and
eight input hashes were not changed after observation. Raw Stage 1 and
relative-time Stage 2 were not rerun.

## Artifact and execution provenance

- Starting clean, synchronized `main`:
  `85a94e5a61f5cb73bbfc96b015503855bccf946e`.
- Frozen config:
  `experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development_v5.toml`,
  file SHA-256
  `4f700ea93821447d5972df317b16e1a1339989e601acb2325196d2a9477268c4`.
- Eight cases, in execution order: `1319:target`, `1319:temporal_twin`,
  `1299:target`, `1299:temporal_twin`, `1387:target`,
  `1387:temporal_twin`, `1222:target`, `1222:temporal_twin`.
- Incident family `incident_003_temporal_compensation_v3`; generator
  `incident-003-generator-v3`; incident protocol
  `incident-003-temporal-protocol-v3`; paired-query protocol
  `incident-003-v3-paired-query-v1`; anchor allocation
  `incident-003-v3-role-neutral-anchor-allocation-v1`.
- Condition `temporal-ablation-v1`, transformation
  `incident-003-temporal-ablation-v1`, temporal semantics
  `temporal-semantics-unavailable-v1`, transformation-configuration SHA-256
  `fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b`.
- Manifest `raw-rca-manifest-v13`; prompt `raw-rca-v3`, template SHA-256
  `a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`;
  taxonomy `rca-taxonomy-v3`; RCA scorer `raw-rca-scorer-v3`;
  evidence protocol `evidence-support-v5`, requirement constructor
  `incident-003-v3-evidence-requirements-v3`, semantic evaluator
  `incident-003-v3-evidence-semantic-evaluator-v3`.
- OpenAI Responses requested `gpt-5.6-sol`, medium reasoning, omitted
  temperature, `max_output_tokens=4096`, one call per case. All eight
  provider-returned model IDs were `gpt-5.6-sol`, all service tiers were
  `default`, and optional model-version metadata was unavailable.
- Before provider initialization, the dry run verified all eight frozen
  model-input hashes, all eight prospective v5 requirement-set hashes, and the
  transformation-config hash. The result path was absent, ignored, and
  untracked. There were no validation or held-out cases scheduled.

The single authorized command was:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development_v5.toml \
  --results results/incident_003_v3_temporal_ablation_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl \
  --execute
```

The completed, ignored and untracked JSONL has **8 lines** and exact-byte
SHA-256
`40d48f58f95b9bf837fa75a6a13209f6d00c6bbedca8c24d90ddb0927e1bb55a`.
It is not part of Git or the documentation PR. The historical Stage-1 and
Stage-2 JSONLs were available locally and still matched their frozen SHA-256
values, respectively
`b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`
and `f020511aeb497eab8c4ca5da4487ed87e20c6fe5e8b37a56613eb521297536e4`.

## Coverage and RCA

All 8/8 planned slots were attempted; none remained unattempted. All eight
responses were valid. Provider failures, parser failures, refusals, and rate
limits were each zero.

| Measure | Stage-3 result |
|---|---:|
| Exact five-dimensional RCA | 4/8 valid |
| Observed outcome | 8/8 |
| Trigger | 8/8 |
| Subsequent action | 8/8 |
| Failure mechanism | 4/8 |
| Affected component | 8/8 |
| Target exact / mechanism | 4/4 / 4/4 observed |
| Temporal-twin exact / mechanism | 0/4 / 0/4 observed |
| Paired exact / mechanism | 0/4 / 0/4 complete pairs |
| Complete-pair coverage | 4/4 planned |

The target oracle mechanism is `incorrect_concurrency_control`; the twin
oracle mechanism is `incorrect_state_transition`. Every response predicted
`incorrect_concurrency_control`:

| Construction | Target mechanism | Twin mechanism | Frozen pair pattern |
|---|---|---|---|
| 1319 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |
| 1299 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |
| 1387 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |
| 1222 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |

There were no unavailable pairs. The model's behavior is an observation, not
an input to the frozen scorer or a reason to edit the benchmark.

## Prospective evidence-support-v5

Evidence-supported: **0/8 valid**. Mean essential requirement coverage:
`0.3`; contrast coverage: `0.0`; supportive coverage:
`0.20833333333333331`; useful citation precision: `0.5750000000000001`.
Invalid citations: 0; wrong-subject citations: 0.

The following path-set abbreviations preserve the exact per-case selected
paths without repeating long strings in the table:

- **A:** `queried_subject_identity:logs-compensation_completed`,
  `inconsistent_terminal_workflow_effect_state:logs`,
  `queried_terminal_outcome_support:logs`.
- **B:** `queried_subject_identity:logs-deadline_reached`,
  `inconsistent_terminal_workflow_effect_state:structured`,
  `queried_cross_source_linkage:structured`.
- **C:** `queried_subject_identity:logs-deadline_reached` only.

The missing-essential sets are:

- **T4:** `deadline_before_original_completion`,
  `compensation_after_deadline`, `execution_compensation_overlap`,
  `late_successful_original_effect`.
- **T5:** T4 plus `inconsistent_terminal_workflow_effect_state`.
- **W3:** `successful_execution_and_active_effect_before_deadline`,
  `compensation_after_committed_success`,
  `serialized_execution_before_compensation`.
- **W4:** W3 plus `inconsistent_terminal_workflow_effect_state`.

| Case | Exact RCA | Mechanism correct | Evidence-supported | Essential coverage | Selected paths | Missing essentials |
|---|---|---|---|---:|---|---|
| `1319:target` | yes | yes | no | 2/6 | A | T4 |
| `1319:temporal_twin` | no | no | no | 2/5 | B | W3 |
| `1299:target` | yes | yes | no | 1/6 | C | T5 |
| `1299:temporal_twin` | no | no | no | 2/5 | B | W3 |
| `1387:target` | yes | yes | no | 1/6 | C | T5 |
| `1387:temporal_twin` | no | no | no | 1/5 | C | W4 |
| `1222:target` | yes | yes | no | 2/6 | B | T4 |
| `1222:temporal_twin` | no | no | no | 2/5 | B | W3 |

The temporal essentials remain unsatisfied under the frozen unavailable-time
semantics. Correct RCA labels on targets and evidence support are separate
outcomes; no evidence requirement was relaxed after seeing the responses.

## Usage and descriptive three-stage comparison

Stage 3 consumed 46,020 input tokens, 2,973 output tokens (including 1,397
reasoning tokens), and 48,993 total tokens. Estimated API cost is
**$0.289536** using pricing snapshot `openai-gpt-5.6-sol-2026-09-10`.
The estimate is not part of scoring.

| Development stage | Valid | Exact RCA | Target mechanism | Twin mechanism | Paired mechanism | Paired exact | Evidence support |
|---|---:|---:|---:|---:|---:|---:|---|
| Raw Stage 1 | 8/8 | 7/8 | 4/4 | 3/4 | 3/4 | 3/4 | 0/8 primary v4; 3/8 post-hoc v5 |
| Relative-time Stage 2 | 8/8 | 6/8 | 4/4 | 2/4 | 2/4 | 2/4 | 4/8 prospective v5 |
| Temporal-ablation Stage 3 | 8/8 | 4/8 | 4/4 | 0/4 | 0/4 | 0/4 | 0/8 prospective v5 |

The observed paired-mechanism ordering (3/4, 2/4, 0/4) is directionally
consistent with the preregistered descriptive expectation that raw and
relative-time evidence outperform temporal ablation. It does **not** establish
equivalence between raw and relative time. Stage 2 versus Stage 3 is the clean
prospective-v5 evidence-protocol comparison; Stage-1 v5 is post-hoc and
secondary, while v4 remains Stage 1's primary evidence score. Four paired
constructions and one call per case do not support statistical significance,
a universal privacy-method ranking, or a causal claim from provider
variability alone. The offline matched-pair construction and observed
descriptive pattern should be assessed together, without changing the
benchmark after observation.

No provider call beyond the eight authorized Stage-3 slots occurred. No raw
or relative-time observation was rerun, and no validation or held-out
instance was generated or inspected.
