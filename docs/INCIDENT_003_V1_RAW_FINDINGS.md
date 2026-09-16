# Incident 003 v1 Raw Sol Findings

## Frozen status

This document records an immutable development observation. It does not revise
the benchmark, oracle, prompt, taxonomy, scorer, or expected evidence. The run
must not be regenerated, retried, or retroactively rescored.

Incident 003 v1 used:

- family: `incident_003_temporal_compensation`;
- protocol: `incident-003-temporal-protocol-v1`;
- condition: `raw`;
- model: requested and returned `gpt-5.6-sol`;
- reasoning: `medium`;
- temperature: omitted;
- calls per seed: one;
- prompt: `raw-rca-v2`;
- taxonomy: `rca-taxonomy-v2`;
- scorer: `raw-rca-scorer-v2`;
- manifest: `raw-rca-manifest-v6`; and
- prompt-template SHA-256:
  `744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d`.

The mechanically selected development seeds were:

```text
1000, 1001, 1002, 1003, 1004, 1015, 1017, 1018
```

Selection used `incident-003-first-two-per-temporal-template-v1`, retaining the
first two ascending occurrences of each temporal template. Validation and
held-out seeds were empty.

The ignored local result is
`results/incident_003_raw_sol_development_gpt_5_6_sol_medium.jsonl`, with
SHA-256:

```text
4f24b8a5bb593fb491307544796bc6d75b85c32b761e5ee09d79bdb802e8f66b
```

## Frozen aggregate result

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
| Provider/parser/rate-limit/refusal/transport failures | 0 |
| Input tokens | 79,410 |
| Output tokens | 3,247 |
| Reasoning tokens | 1,666 |
| Total tokens | 82,657 |
| Estimated cost under the frozen pricing snapshot | $0.461966 |

Every observation predicted:

```text
observed_outcome = inconsistent_state
trigger = timeout_or_deadline
subsequent_action = compensation_or_rollback
failure_mechanism = incorrect_concurrency_control
affected_component = workflow_orchestrator
```

The frozen v1 oracle differed only on:

```text
failure_mechanism = incorrect_state_transition
```

The run remains historically scored as 0/8 exact RCA. It must not be presented
as successful exact qualification under v2.

## Temporal reasoning finding

The model did not fail to recover the intended temporal sequence. Across all
eight observations, its labels and explanations recognized:

- deadline before original completion;
- compensation following the deadline;
- compensation/execution overlap;
- late original success;
- active effect coexisting with compensated workflow state;
- timeout/deadline as trigger;
- compensation/rollback as subsequent action; and
- workflow-orchestrator ownership.

The systematic disagreement concerned failure-mechanism classification.

The precise finding is:

> Incident 003 v1 demonstrated that the temporal causal signal was visible to
> GPT-5.6 Sol, but exact RCA qualification failed under the frozen v2 taxonomy
> because the mechanism category was systematically interpreted as
> `incorrect_concurrency_control` rather than the v1 oracle's
> `incorrect_state_transition`. Subsequent offline adjudication found the v2
> distinction underspecified.

## Offline taxonomy adjudication

The accepted classification is **B. Taxonomy ambiguity**, driven substantially
by taxonomy-definition insufficiency.

RCA taxonomy v2 defined the general failure-mechanism dimension and listed both
mechanism labels, but defined neither label individually. It did not make them
mutually exclusive or specify precedence when an invalid transition occurs
during overlapping operations.

Incident 003 v1 mechanically contains both:

- a transition into compensation while original execution remains nonterminal;
- overlapping original execution and compensation;
- no effective fencing or cancellation preventing both paths from taking
  effect;
- late original success and an active downstream effect;
- completed compensation; and
- a compensated final workflow state.

The v1 oracle is therefore defensible but not uniquely determined under v2.
This development finding motivates a future versioned taxonomy and incident
protocol; it does not authorize changing v1.

## Frozen evidence audit

Seven responses cited valid target lifecycle-log IDs instead of IDs from the
single frozen structured-row expected set. No cited evidence ID was nonexistent
or outside the visible evidence.

The log evidence supported substantial parts of the causal sequence, but model
citation coverage was genuinely incomplete: controls were omitted, and most
responses did not cite every row needed to prove the full overlap relation.
Nevertheless, the exact-ID rubric substantially understated grounding because
it did not preregister semantically equivalent structured, log, or mixed paths.

The historical precision, recall, F1, and `evidence_supported` results remain
unchanged. Any semantic evidence protocol must be independently versioned and
cannot be applied retroactively as the experimental score.

## Limitations and use

- This is one model with one call on eight synthetic development instances.
- All observations share one generator family and do not establish generality.
- Exact qualification failed under the protocol actually used.
- Agreement across eight responses is not agreement across eight independent
  models.
- The mechanism disagreement may reflect taxonomy semantics rather than loss of
  temporal information.
- The exact-ID evidence rubric and semantic evidence support answer different
  questions.
- No privacy condition has been executed for Incident 003.
- At this v1 result freeze, no `relative-time-v1` transformation existed; it
  was implemented later under a separate offline protocol and does not alter
  this historical observation.
- No Incident 003 validation or held-out observation exists.

See `docs/RCA_V3_METHODOLOGY.md` for the approved but unimplemented methodology
decision and fresh-seed policy.
