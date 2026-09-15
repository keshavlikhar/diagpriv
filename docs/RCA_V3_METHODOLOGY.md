# RCA v3 Methodology Decision

## Status

This document records an approved design decision. None of the versions below
is implemented yet:

- `rca-taxonomy-v3`
- `raw-rca-v3`
- `raw-rca-scorer-v3`
- `evidence-support-v3`

The frozen v2 taxonomy, prompt, scorer, manifests, incident oracles, and
historical observations remain unchanged. In particular, the Incident 003 v1
raw result remains 0/8 exact RCA under its original v2 oracle and scorer.

## Motivation

RCA taxonomy v2 defines `failure_mechanism` generally as the system defect or
missing control that allowed a trigger and later action to produce an outcome.
It lists both `incorrect_state_transition` and
`incorrect_concurrency_control`, but gives neither label an individual
benchmark-wide definition. It also provides no mutual-exclusion or precedence
rule for an incident containing an invalid transition and overlapping actors.

Incident 003 v1 exposed that ambiguity during development. Its construction
contains a transition into compensation while original execution remains
nonterminal, overlapping execution and compensation, late original success,
an active downstream effect, completed compensation, and a compensated final
workflow state. All eight frozen Sol responses recovered this temporal chain
but selected `incorrect_concurrency_control` instead of the v1 oracle's
`incorrect_state_transition`.

Offline adjudication classified the result as **B. Taxonomy ambiguity, driven
substantially by taxonomy-definition insufficiency**. The v1 oracle is
defensible, but not uniquely determined by v2.

## Taxonomy decision rules

The proposed v3 protocol will:

- evaluate each RCA dimension independently;
- choose the most specific category supported by model-visible evidence;
- define the trigger as the event directly initiating the causal sequence;
- define the subsequent action as the first post-trigger action necessary to
  propagate the failure;
- define the failure mechanism as the most proximal defective or missing
  system control;
- assign the affected component to the architectural owner of that control,
  not a normal participant or symptom reporter; and
- use category-specific counterfactual and precedence rules to resolve
  superficially overlapping labels.

The complete researcher-facing taxonomy may include definitions, inclusion and
exclusion criteria, nearest confusables, precedence, positive examples, and
contrastive examples. Those examples are methodology documentation and test
fixtures; they are not automatically model-visible.

## State-transition and concurrency-control boundary

### `incorrect_concurrency_control`

The failure requires overlapping actors or operations that can both proceed or
commit because synchronization, serialization, fencing, conditional updates,
locking, version checks, or cancellation enforcement is absent or ineffective.

### `incorrect_state_transition`

A lifecycle or state-machine transition is permitted from an invalid source
state or without a required state precondition, and that transition remains
invalid under serialized execution.

The accepted precedence is:

1. If the failure requires overlap and correct concurrency control would
   prevent it, use `incorrect_concurrency_control`.
2. If the invalid lifecycle edge remains wrong under serialized execution, use
   `incorrect_state_transition`.
3. When state inconsistency exists only because concurrent work was not
   controlled, concurrency control takes precedence.

Idempotency remains a more specific control when repeated executions share one
logical identity and correct deduplication or safe replay alone would prevent a
duplicate outcome.

## Blinded mapping of existing families

The accepted mapping uses construction facts only, not model predictions.

| Family | Outcome | Trigger | Action | Mechanism | Component | Change from v2 |
|---|---|---|---|---|---|---|
| Incident 001 | `duplicate_effect` | `timeout_or_deadline` | `retry_or_rearrival` | `missing_or_ineffective_idempotency` | `operation_executor` | None |
| Incident 002 | `missing_effect` | `malformed_or_unexpected_input` | `no_follow_on_action` | `validation_or_input_handling_failure` | `operation_executor` | None |
| Incident 003 v1 construction under v3 | `inconsistent_state` | `timeout_or_deadline` | `compensation_or_rollback` | `incorrect_concurrency_control` | `workflow_orchestrator` | Mechanism only |

Under the proposed v3 boundary, Incident 003 is no longer ambiguous: its
outcome depends on overlapping execution and compensation both taking effect,
and fencing or cancellation enforcement would prevent that outcome.

## Planned Incident 003 v2

Future implementation should version the protocol and generator instead of
mutating v1. Planned identifiers are:

- `incident-003-generator-v2`
- `incident-003-temporal-protocol-v2`

`temporal-semantics-v1`, the model-visible construction, diagnostic invariants,
and temporal ablation remain unchanged. The planned oracle is:

```text
observed_outcome = inconsistent_state
trigger = timeout_or_deadline
subsequent_action = compensation_or_rollback
failure_mechanism = incorrect_concurrency_control
affected_component = workflow_orchestrator
```

This planned oracle is not implemented or empirically qualified.

## Model-facing prompt boundary

The future `raw-rca-v3` prompt may contain only:

- task and dimension definitions;
- canonical labels with concise operational definitions;
- important exclusions;
- minimal counterfactual and precedence rules;
- response schema and evidence-ID requirements; and
- the ModelView.

It must contain no concrete taxonomy examples. In particular, it must not
contain benchmark-isomorphic examples involving duplicate payments or charges,
fixed-width identifiers, exact-lookup provisioning, a deadline followed by
compensation and late success, rollback racing an active worker, incident names,
or oracle labels.

The full researcher-facing taxonomy may retain positive and contrastive
examples for review and tests, but model visibility must be audited separately.

## Evidence-support v3 design

V3 evidence scoring will represent diagnostic support as semantic proof
obligations with generator-derived alternative paths frozen before provider
execution. Structured rows, lifecycle logs, or preregistered mixed paths may
satisfy one requirement when they deterministically establish the same fact.
Subject binding is mandatory: evidence from different operations may not be
combined to satisfy a target relation. An acceptable path may never be added in
response to a model citation.

### Essential Incident 003 causal requirements

1. Target identity linkage.
2. Deadline before original completion.
3. Compensation after deadline.
4. Execution and compensation overlap.
5. Late successful original effect.
6. Inconsistent terminal workflow/effect state.

### Contrast requirements

1. Legitimate-compensation control.
2. Healthy deadline or benign-slow control.

Contrast coverage measures explicit control and distractor reasoning. It is
reported separately and is not required for direct evidence support.

### Supportive requirements

Supportive requirements may cover orchestrator ownership, executor ownership,
dependency availability, warning comparison, and additional target lifecycle
corroboration.

### Planned primary evidence metrics

- `essential_requirement_coverage`
- `contrast_requirement_coverage`
- `supportive_requirement_coverage`
- `useful_citation_precision`
- `invalid_citation_count`
- `invalid_citation_rate`
- `wrong_subject_citation_count`
- `redundant_citation_count`
- `redundant_citation_rate`
- `evidence_supported`

`evidence_supported` is true only when all essential requirements are
satisfied, essential subject bindings are consistent, no nonexistent citation
is used, and no wrong-target or contradictory evidence is used to satisfy an
essential requirement. Contrast coverage is not required.

The planned overall criterion is:

```text
overall_correct_v3 = exact five-dimensional RCA AND evidence_supported
```

No opaque composite evidence measure will replace the primary metrics. A
derived F1 may be secondary analysis only. Historical v2 exact-ID evidence
precision, recall, and F1 remain unchanged.

## Fresh Incident 003 development policy

The eight v1 provider-observed seeds are historical, regression, or protocol-
debugging inputs only. They may not be presented as fresh qualification evidence
for a revised protocol.

The future selection rule is
`incident-003-v2-first-two-per-temporal-template-unobserved-v1`: begin at seed
1019, inspect only temporal-template metadata in ascending order, retain the
first two previously unobserved seeds for each of the four templates, and stop
when each template has two. Selection must not use position, warnings, expected
difficulty, transformation behavior, or model behavior.

The frozen future set is:

```text
1019, 1020, 1021, 1022, 1023, 1025, 1026, 1028
```

These seeds have not been sent to a provider. No v3 implementation or provider
qualification is authorized by this document.

## Compatibility policy

- Keep `raw-rca-v2`, `rca-taxonomy-v2`, `raw-rca-scorer-v2`, and historical
  observations unchanged.
- Do not reinterpret the Incident 003 v1 result as 8/8 after changing labels.
- Treat any v3 score as a new protocol result, not a correction of v2.
- Use a new manifest schema when v3 evidence fields are implemented.
- Complete static leakage, deterministic evidence-path, and fresh-seed reviews
  before any provider call.
