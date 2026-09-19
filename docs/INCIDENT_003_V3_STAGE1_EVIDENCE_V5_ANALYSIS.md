# Incident 003 v3 Stage-1 Evidence v5 Secondary Analysis

This is a post-hoc, provider-free secondary analysis. The frozen v4 observation
remains primary and unchanged.

Source artifact:
`results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl`

Verified source SHA-256:
`b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`

Protocol: `incident-003-v3-stage1-evidence-v5-secondary-analysis-v1` using
`evidence-support-v5`.

## Summary

| Metric | Frozen v4 | Candidate v5 |
|---|---:|---:|
| Cases | 8 | 8 |
| Evidence-supported | 0/8 | 7/8 |
| Frozen exact RCA | 7/8 | unchanged, 7/8 |
| Invalid citations | 0 | 0 |
| Wrong-subject citations | 0 | 0 |

V5 recognizes complete log-based semantic paths in seven cases. It does not
infer uncited facts for `1299:temporal_twin`, which omits the
`compensation_started` event needed for both compensation-after-success and
affirmative completion-before-compensation proof.

## Case comparison

| Case | Frozen RCA exact | v4 support / essential coverage | v5 support / essential coverage | v5 useful precision | V5 missing essentials |
|---|---:|---:|---:|---:|---|
| `1319:target` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1319:temporal_twin` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1299:target` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1299:temporal_twin` | yes | no / 0.000 | no / 0.600 | 1.000 | `compensation_after_committed_success`; `serialized_execution_before_compensation` |
| `1387:target` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1387:temporal_twin` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1222:target` | yes | no / 0.000 | yes / 1.000 | 1.000 | none |
| `1222:temporal_twin` | **no** | no / 0.000 | yes / 1.000 | 1.000 | none |

The selected v5 paths in supported cases are log paths for queried identity,
the role-specific temporal requirements, terminal-state inconsistency, and any
cited supportive subrequirements. No contrast path was required to gate support.

`1222:temporal_twin` remains the sole RCA mechanism failure. Its evidence can
be independently supported under v5, but the submitted mechanism remains
`incorrect_concurrency_control` rather than the frozen twin oracle
`incorrect_state_transition`; exact RCA and overall correctness remain false.

The result must be described as a broader representation-invariant model
developed post hoc. It does not retroactively invalidate or overwrite v4.
