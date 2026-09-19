# Incident 003 v3 relative-time Stage-2 development observation

Issue #34 authorized one execution of the prospective protocol prepared in
issue #33 and merged through PR #36. This is a frozen **development-only**
observation, not a validation or held-out result. No response was retried or
replaced, and no protocol, scorer, evidence rule, input, or transformation was
changed after observing it. Temporal-ablation Stage 3 remains unexecuted.

## Artifact and protocol

- Starting `main`: `66d40c5bc5d594ce987ae03f340fa7006d867a7a`.
- Condition: `relative-time-v1`; cases in order: `1319:target`,
  `1319:temporal_twin`, `1299:target`, `1299:temporal_twin`, `1387:target`,
  `1387:temporal_twin`, `1222:target`, `1222:temporal_twin`.
- All eight frozen model-input hashes and v5 requirement-set hashes matched the
  checked-in config before provider initialization; transformation-config
  SHA-256 matched
  `cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660`.
- Frozen prompt `raw-rca-v3`, taxonomy `rca-taxonomy-v3`, RCA scorer
  `raw-rca-scorer-v3`, evidence protocol `evidence-support-v5`, manifest
  `raw-rca-manifest-v12`; GPT-5.6 Sol, medium reasoning, temperature omitted,
  `max_output_tokens=4096`, one call per case.
- Ignored, untracked local result:
  `results/incident_003_v3_relative_time_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl`.
  Exact-byte SHA-256:
  `f020511aeb497eab8c4ca5da4487ed87e20c6fe5e8b37a56613eb521297536e4`.
  The JSONL is intentionally not part of Git or this documentation PR.
- Execution was the checked-in `run-pilot` command with the v5 config and that
  result path, explicitly passing `--execute`. The path was absent beforehand.

## Coverage and RCA

All 8/8 planned calls were attempted and produced valid responses; 0 were
unattempted. There were no provider, parser, refusal, or rate-limit failures.
Each provider-returned model ID was `gpt-5.6-sol` (service tier `default`);
optional model-version metadata was unavailable.

| Measure | Stage-2 result |
|---|---:|
| Exact five-dimension RCA | 6/8 |
| Observed outcome | 8/8 |
| Trigger | 8/8 |
| Subsequent action | 8/8 |
| Failure mechanism | 6/8 |
| Affected component | 8/8 |
| Target exact / mechanism | 4/4 / 4/4 |
| Temporal-twin exact / mechanism | 2/4 / 2/4 |
| Paired exact / mechanism | 2/4 / 2/4 complete pairs |
| Complete-pair coverage | 4/4 |

Both queried roles have the same oracle labels except mechanism: target
`incorrect_concurrency_control`; temporal twin `incorrect_state_transition`.
The observed pair patterns are:

| Construction | Target mechanism | Twin mechanism | Frozen pattern |
|---|---|---|---|
| 1319 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |
| 1299 | `incorrect_concurrency_control` | `incorrect_state_transition` | `correct_mechanism_flip` |
| 1387 | `incorrect_concurrency_control` | `incorrect_state_transition` | `correct_mechanism_flip` |
| 1222 | `incorrect_concurrency_control` | `incorrect_concurrency_control` | `both_concurrency` |

## Prospective evidence-support-v5

Evidence-supported: 4/8. Mean essential requirement coverage:
`0.9166666666666667`; contrast requirement coverage: `0.0`; supportive
requirement coverage: `0.6666666666666666`; useful citation precision: `1.0`.
Invalid citations: 0; wrong-subject citations: 0.

The selected-path set `T` (all four targets) was:
`queried_subject_identity:logs-compensation_started`,
`deadline_before_original_completion:logs`,
`compensation_after_deadline:logs`, `late_successful_original_effect:logs`,
`inconsistent_terminal_workflow_effect_state:logs`,
`queried_deadline_action_support:logs`, and
`queried_terminal_outcome_support:logs`.

The selected-path set `W` (all four temporal twins) was:
`queried_subject_identity:logs-compensation_started`,
`successful_execution_and_active_effect_before_deadline:logs`,
`compensation_after_committed_success:logs`,
`serialized_execution_before_compensation:logs`,
`inconsistent_terminal_workflow_effect_state:logs`,
`queried_deadline_action_support:logs`, and
`queried_terminal_outcome_support:logs`.

| Case | Exact RCA | Mechanism correct | Evidence-supported | Essential coverage | Selected paths | Missing essential |
|---|---|---|---|---:|---|---|
| `1319:target` | yes | yes | no | 5/6 | T | `execution_compensation_overlap` |
| `1319:temporal_twin` | no | no | yes | 6/6 | W | none |
| `1299:target` | yes | yes | no | 5/6 | T | `execution_compensation_overlap` |
| `1299:temporal_twin` | yes | yes | yes | 6/6 | W | none |
| `1387:target` | yes | yes | no | 5/6 | T | `execution_compensation_overlap` |
| `1387:temporal_twin` | yes | yes | yes | 6/6 | W | none |
| `1222:target` | yes | yes | no | 5/6 | T | `execution_compensation_overlap` |
| `1222:temporal_twin` | no | no | yes | 6/6 | W | none |

Thus evidence support and RCA correctness are separate outcomes. The targets
were RCA-correct but did not cite a complete proof of positive execution/
compensation overlap; the two incorrect twins met the frozen citation
requirements despite choosing the wrong mechanism label. The frozen rubric
was not relaxed.

## Usage and descriptive comparison

Across the eight calls: 42,524 input tokens, 3,804 output tokens (including
2,225 reasoning tokens), and 46,328 total tokens. Estimated API cost:
**$0.288676**, using pricing snapshot
`openai-gpt-5.6-sol-2026-09-10`. Pricing is an estimate, not a scoring input.

| Development condition | Valid | Exact RCA | Target mechanism | Twin mechanism | Paired mechanism | Paired exact | Evidence support |
|---|---:|---:|---:|---:|---:|---:|---:|
| Raw Stage 1 | 8/8 | 7/8 | 4/4 | 3/4 | 3/4 | 3/4 | 0/8 primary v4; 3/8 post-hoc v5 |
| Relative-time Stage 2 | 8/8 | 6/8 | 4/4 | 2/4 | 2/4 | 2/4 | 4/8 prospective v5 |

Stage-1 primary v4 evidence support and Stage-2 prospective v5 evidence
support are **different protocols**. The Stage-1 v5 figure is secondary and
post hoc; it is not a second prospective condition. With only four paired
constructions, these descriptive differences establish neither statistical
superiority nor equivalence. Stage 1 was not rerun. Validation, held-out, and
Stage 3 were untouched.
