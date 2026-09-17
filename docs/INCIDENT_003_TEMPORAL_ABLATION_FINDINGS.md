# Incident 003 temporal-ablation findings and shortcut-cue audit

Status: frozen development observation and offline audit, 2026-09-17.

This document freezes the Incident 003 v2 `temporal-ablation-v1` result and
reports a deterministic, provider-free audit of the non-temporal cues that
survived the transformation. Historical Incident 003 v2 construction,
artifacts, oracle, configs, transformations, and observations remain unchanged.

## Frozen observation

| Item | Frozen value |
|---|---|
| Merged `main` used for execution | `03236571c9df16d945714696998904e571874c1f` |
| Condition | `temporal-ablation-v1` |
| Result path | `results/incident_003_v2_temporal_ablation_v1_sol_development_gpt_5_6_sol_medium.jsonl` |
| Result SHA-256 | `aebe64d289c9a0f1d201a8066e6678b0c386bcfaf07026eb73377bc475432922` |
| Raw SHA-256 | `54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915` |
| Relative-time-v1 SHA-256 | `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb` |

Matched five-label RCA was 8/8 for raw, 8/8 for relative time, and 8/8 for
temporal ablation. Under temporal ablation, outcome, trigger, action,
mechanism, and component were each correct in 8/8. Every response selected:

- `inconsistent_state`;
- `timeout_or_deadline`;
- `compensation_or_rollback`;
- `incorrect_concurrency_control`;
- `workflow_orchestrator`.

No response selected `incorrect_state_transition`.

## Frozen evidence-support-v4 result

| Metric | Result |
|---|---:|
| Essential coverage | 0.041667 |
| Contrast coverage | 0.000000 |
| Supportive coverage | 0.200000 |
| Useful citation precision | 0.400000 |
| Evidence precision | 0.400000 |
| Evidence recall | 0.041667 |
| Evidence F1 | 0.058824 |
| Invalid citations | 0/40 |
| Wrong-subject citations | 0 |
| Redundant citations | 0/40 |
| Evidence-supported | 0/8 |
| Overall correct under RCA-v3 + evidence-v4 | 0/8 |

**Exact RCA labels remained 8/8 even though the transformed evidence could not
establish the essential temporal causal chain.** The labels must not be
described as evidence-grounded.

## Frozen interpretation

> Incident 003 remains solvable on these eight development cases despite
> removal of explicit temporal semantics. GPT-5.6 Sol recovered the intended
> five-label RCA from surviving non-temporal operational cues, so this
> benchmark version does not isolate temporal reasoning strongly enough to
> support the intended causal claim.

> Evidence-support-v4 correctly distinguishes label accuracy from evidentiary
> support: the model produced the expected diagnosis but could not establish
> the required temporal relations from the ablated ModelView.

This does not show that the model inferred the hidden temporal sequence, that
temporal reasoning is unnecessary generally, that GPT-5.6 Sol ignores
timestamps, that the entire benchmark is invalid, or that the eight
development cases support statistical or external-generalization claims.

## Audit method

`incident-003-v2-nontemporal-cue-audit-v1` generates only development
constructions 1000–1199, applies the already frozen temporal ablation, groups
visible records using preserved operation identity, and computes categorical
cue and feature signatures. Hidden metadata is used only to label target,
healthy, legitimate-compensation, and benign-slow roles for offline audit; it
does not enter ModelView. No classifier is trained and no provider is called.

The audit inspected 200 target operations, 1,076 healthy-control operations,
200 legitimate-compensation controls, and the 200 benign-slow controls that
are a labeled subset of the healthy controls.

## Cue taxonomy

| Cue class | Model-visible manifestation | Leakage mode | Diagnostic shortcut |
|---|---|---|---|
| Outcome | Troubleshooting question says workflow state does not agree with effect | Natural-language | Nearly states `inconsistent_state` |
| Outcome | `workflow_state=compensated`, execution `result=success`, effect `state=active` | Categorical combination | Target-only terminal contradiction |
| Trigger | `deadline_at` schema name | Schema-name | Announces a deadline even when its value is opaque |
| Trigger | `event_kind=deadline_reached` and deadline messages | Categorical and natural-language | Selects `timeout_or_deadline` without comparing time |
| Action | `compensation_records`, `compensation_state=completed` | Record-type and categorical | Selects compensation/rollback |
| Action | Compensation/rollback message text and event kinds | Natural-language and categorical | Direct action-label cue |
| Mechanism | Compensated + successful execution + active effect | Cross-record categorical | Suggests a race/fencing failure without proving overlap |
| Mechanism | Distinct coordinator and executor roles | Role structure | Makes a coordination framing plausible |
| Component | `orchestrator_alias` field | Schema-name | Near-label leakage for `workflow_orchestrator` |
| Component | `workflow-controller`, `flow-coordinator`, `process-supervisor`, `journey-manager` | Role-name | Strongly signals orchestration ownership |
| Component contrast | Executor aliases and effect/execution ownership | Role-name and source | Distinguishes executor from coordinator |
| Linkage | Repeated `operation_id` across sources | Value/linkage | Lets the model assemble the target tuple |
| Record shape | Target alone has workflow + execution + effect + compensation records | Record-type | Perfect target/control separator |
| Event shape | Target event-kind set combines deadline, compensation, success, effect, and state | Categorical set | Perfect target/control separator |

Temporal values themselves do not leak: every annotated timestamp is a unique,
non-parseable TA1 marker, and chronological log order is removed. The shortcut
is carried by names, categories, messages, record presence, linkage, and their
combinations.

## Message leakage audit

All 22 generated message variants across 11 event kinds appeared in the
200-instance audit.

| Event kind | Message templates | Leaked concept |
|---|---|---|
| `deadline_reached` | “Workflow deadline reached”; “Deadline checkpoint reached” | Explicit deadline trigger |
| `compensation_started` | “Compensation lifecycle update”; “Rollback lifecycle update” | Explicit compensation/rollback action |
| `compensation_completed` | “Compensation result recorded”; “Rollback result recorded” | Completed compensation/rollback |
| `execution_started` | “Execution lifecycle update”; “Worker lifecycle update” | Execution lifecycle/actor |
| `execution_progress` | “Execution progress sample”; “Worker progress sample” | Progress, but not overlap or lateness |
| `execution_completed` | “Execution result recorded”; “Worker result recorded” | Execution result; `result` attribute supplies success/cancelled |
| `effect_recorded` | “Effect record stored”; “Operation effect stored” | Effect presence; `state` supplies active |
| `workflow_state_recorded` | “Workflow state recorded”; “Process state recorded” | Workflow terminal state |
| `workflow_checkpoint` | “Workflow observation recorded”; “Process observation recorded” | Workflow state/checkpoint |
| `dispatch_recorded` | “Workflow dispatch recorded”; “Operation dispatch recorded” | Dispatch lifecycle |
| `dependency_observed` | “Dependency sample recorded”; “Backend sample recorded” | Dependency-health distractor |

No free-text template explicitly says “late,” “overlap,” “still active,”
“not cancelled,” “fencing failed,” “contradictory,” or that the orchestrator is
responsible. The decisive leakage instead comes from explicit deadline and
compensation vocabulary plus categorical state/result combinations. The model
responses' claims about lateness and overlap were inferences unsupported under
`temporal-semantics-unavailable-v1`.

## Exhaustive schema-name and value audit

The ablated ModelView exposes 54 generated schema paths. The table below lists
every path, grouped only where the paths share the same audit classification.

| Source | Paths | Classification and exposed concepts |
|---|---|---|
| Root | `troubleshooting_question` | **Strong:** directly describes inconsistent workflow/effect state |
| Logs | `log_evidence` | Neutral container |
| Logs | `log_evidence.evidence_id` | Neutral identifier |
| Logs | `log_evidence.timestamp` | Neutral opaque TA1 marker; no temporal semantics |
| Logs | `log_evidence.level` | Neutral (`INFO`, `WARN`) |
| Logs | `log_evidence.service` | **Strong:** component-role aliases |
| Logs | `log_evidence.message` | **Strong:** event semantics |
| Log attributes | `operation_id` | Weak but necessary cross-source linkage |
| Log attributes | `event_kind` | **Strong:** explicit lifecycle category |
| Log attributes | `compensation_id` | **Strong:** compensation existence |
| Log attributes | `result`, `state`, `workflow_state` | **Strong:** execution/compensation/effect/workflow outcomes |
| Log attributes | `warning` | Weak dependency distractor |
| Log attributes | `effect_id`, `phase` | Neutral alone; informative in an event context |
| Workflow source | `structured_evidence.workflow_attempts` | Weak record-type cue |
| Workflow fields | `evidence_id` | Neutral identifier |
| Workflow fields | `operation_id` | Weak cross-source linkage |
| Workflow fields | `dispatched_at` | Weak event-boundary name; opaque value |
| Workflow fields | `deadline_at` | **Strong:** deadline/trigger schema-name leakage; opaque value |
| Workflow fields | `compensation_state` | **Strong:** compensation action/state |
| Workflow fields | `workflow_state` | **Strong:** terminal workflow state |
| Workflow fields | `orchestrator_alias` | **Near-label:** workflow-orchestrator ownership |
| Execution source | `structured_evidence.execution_observations` | Weak record-type cue |
| Execution fields | `evidence_id` | Neutral identifier |
| Execution fields | `operation_id` | Weak cross-source linkage |
| Execution fields | `started_at`, `completed_at` | Weak event-boundary names; opaque values |
| Execution fields | `result` | **Strong:** `success` versus `cancelled` |
| Execution fields | `executor_alias` | **Strong:** executor-role contrast |
| Effect source | `structured_evidence.effect_records` | **Strong:** effect-record presence |
| Effect fields | `evidence_id`, `effect_id` | Neutral identifiers |
| Effect fields | `operation_id` | Weak cross-source linkage |
| Effect fields | `created_at` | Weak event-boundary name; opaque value |
| Effect fields | `state` | **Strong:** active downstream effect |
| Effect fields | `executor_alias` | **Strong:** executor ownership |
| Compensation source | `structured_evidence.compensation_records` | **Strong:** compensation/rollback action and record type |
| Compensation fields | `evidence_id`, `operation_id`, `compensation_id` | **Strong in this named source:** record/linkage identity |
| Compensation fields | `started_at`, `completed_at` | **Strong action source**, but values remain opaque |
| Compensation fields | `result` | **Strong:** completed compensation |
| Compensation fields | `orchestrator_alias` | **Near-label:** workflow-orchestrator ownership |
| Dependency source | `structured_evidence.dependency_health` | Neutral distractor container |
| Dependency fields | `evidence_id`, `dependency_alias`, `availability_state` | Neutral |
| Dependency fields | `operation_id` | Weak cross-source linkage |
| Dependency fields | `observed_at` | Weak event-boundary name; opaque value |
| Dependency fields | `latency_ms`, `warning` | Weak dependency/latency distractor |

Representative categorical values are themselves informative:
`compensated`, `completed`, `not_started`, `success`, `cancelled`, `active`,
`deadline_reached`, `compensation_started`, `compensation_completed`, and the
four coordinator aliases. No original timestamp value survives.

## Record-type, trigger, component, and mechanism leakage

### Record types

The target alone contains all four operation-linked structured record types:
workflow attempt, execution observation, effect record, and compensation
record. Healthy controls omit compensation; legitimate compensation omits an
effect. This record-presence signature perfectly separates every target from
every control across seeds 1000–1199.

### Trigger

`deadline_at` exists on every workflow row, so its schema name advertises the
general concept but does not identify the target. The target and legitimate
compensation control additionally contain `deadline_reached` event kinds and
messages in 200/200 cases. Healthy and benign-slow controls contain them in
0 cases. Therefore `timeout_or_deadline` can be selected categorically without
comparing any timestamp.

### Component

Every operation exposes coordinator and executor roles, but the field name
`orchestrator_alias` and aliases `workflow-controller`, `flow-coordinator`,
`process-supervisor`, and `journey-manager` strongly map to
`workflow_orchestrator`. Across 200 instances their counts were 57, 46, 38,
and 59 respectively. Executor aliases were `action-runner` (58),
`effect-processor` (48), `operation-worker` (51), and `task-executor` (43).
These names make component ownership substantially easier than a neutral-role
encoding would.

### Mechanism shortcut

The target-only non-temporal conjunction is:

`workflow compensated`

`+ execution succeeded`

`+ active effect exists`

`+ compensation record exists`

`+ separate coordinator and executor actors are visible`.

That tuple occurred in 200/200 targets and 0/1,076 healthy controls, 0/200
legitimate-compensation controls, and 0/200 benign-slow controls. It is
reasonable for a model to associate the tuple with missing cancellation or
fencing and choose `incorrect_concurrency_control`, but the tuple does not
prove overlap. It is a diagnostic shortcut or benchmark label prior, not the
required causal evidence.

## Frozen-seed surviving-cue matrix

All eight observed temporal-ablation cases had the same target cue profile.
`Y` means visible; `N` means absent/unavailable.

| Seed | Deadline lexical | `deadline_at` name | Compensation record | Compensation lexical | Success | Active effect | Compensated workflow | Contradiction | Orchestrator role | Executor role | Cancellation/fencing text | Temporal relation | Exact RCA |
|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1019 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1020 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1021 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1022 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1023 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1025 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1026 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |
| 1028 | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | N | N | Y |

No target contained literal “late,” “overlap,” “not cancelled,” or fencing
failure text. Exact RCA therefore coexisted with complete temporal-semantic
unavailability and incomplete evidentiary support.

## 200-instance cue-frequency matrix

Healthy denominator is 1,076 operations. Benign-slow is a separately reported
200-operation subset of healthy controls.

| Cue | Target | Healthy | Legitimate compensation | Benign slow |
|---|---:|---:|---:|---:|
| Explicit deadline lexical cue | 200/200 | 0/1,076 | 200/200 | 0/200 |
| `deadline_at` schema-name cue | 200/200 | 1,076/1,076 | 200/200 | 200/200 |
| Compensation record | 200/200 | 0/1,076 | 200/200 | 0/200 |
| Compensation/rollback lexical cue | 200/200 | 0/1,076 | 200/200 | 0/200 |
| Successful execution | 200/200 | 1,076/1,076 | 0/200 | 200/200 |
| Active effect | 200/200 | 1,076/1,076 | 0/200 | 200/200 |
| Compensated workflow | 200/200 | 0/1,076 | 200/200 | 0/200 |
| Terminal contradiction tuple | 200/200 | 0/1,076 | 0/200 | 0/200 |
| Orchestrator-role cue | 200/200 | 1,076/1,076 | 200/200 | 200/200 |
| Executor-role cue | 200/200 | 1,076/1,076 | 200/200 | 200/200 |
| Cancellation/fencing lexical value | 0/200 | 0/1,076 | 200/200 (`cancelled`) | 0/200 |
| Literal late/overlap language | 0/200 | 0/1,076 | 0/200 | 0/200 |
| Temporal relation available | 0/200 | 0/1,076 | 0/200 | 0/200 |

## Counterfactual separability

No ML model was trained. Deterministic categorical signatures were compared
directly between target and control operations.

| Non-temporal signature | Target signatures | Healthy signatures | Legitimate signatures | Target/control collisions | Perfect separation |
|---|---:|---:|---:|---:|:---:|
| Full categorical content | 1 | 1 | 1 | 0 | Yes |
| Terminal-state tuple | 1 | 1 | 1 | 0 | Yes |
| Structured record-type presence | 1 | 1 | 1 | 0 | Yes |
| Log event-kind set | 1 | 1 | 1 | 0 | Yes |

All 200 target operations were separable without timestamp values, timestamp
ordering, row order, log order, or marker ordering. The strongest likely
shortcuts are, in order:

1. target-only terminal contradiction tuple;
2. target-only combination of effect and compensation record types;
3. target-only event-kind set;
4. explicit deadline and compensation categories/messages;
5. outcome-revealing troubleshooting wording;
6. near-label orchestrator schema and aliases.

## Candidate Incident 003 v3 repair

Historical v2 must remain immutable. A future repair should use separately
versioned `incident-003-generator-v3` and
`incident-003-temporal-protocol-v3` and should be reviewed offline before any
provider call.

Recommended principles:

1. Give each target at least one hard control with the same non-temporal
   terminal-state, record-type, event-kind, role, and linkage signature.
2. Include deadline fields/events, compensation records, successful execution,
   and active-effect observations in target and hard controls; distinguish the
   mechanism using ordering and overlap.
3. Consider controls with the same outcome, trigger, action, and component but
   a serialized state-transition mechanism, so concurrency versus state-machine
   failure depends on time rather than record presence.
4. Balance deadline, timeout, compensation, rollback, success, and effect
   vocabulary across target and controls.
5. Remove literal “late,” “overlap,” “still executing,” “after rollback,”
   cancellation-failure, and fencing-failure text unless matched controls use
   equally suggestive language.
6. Replace near-label role/schema names with realistic but neutral aliases;
   keep a hidden canonical component mapping.
7. Use a less outcome-revealing troubleshooting question.
8. Preserve realistic cross-source identity and operational plausibility; do
   not make the task a synthetic timestamp puzzle.
9. Preserve raw/relative temporal invariants exactly while making the ablated
   target collide with hard controls on preregistered non-temporal signatures.
10. Keep v3 deterministic, development-only during construction review, and
    separately version every generator, protocol, prompt-impacting schema, and
    audit.

One feasible design is to represent effect and compensation as histories
rather than only terminal snapshots. Target and control can then share the same
record types and categorical observations while differing in whether execution
and compensation overlapped or were safely serialized. This requires careful
domain review so that controls remain operationally credible.

## Proposed offline acceptance criteria for v3

Before any provider experiment:

1. Raw temporal invariants distinguish target from every hard control.
2. `relative-time-v1` preserves every distinguishing relation exactly.
3. `temporal-ablation-v1` makes those relations explicitly unavailable.
4. Every target has at least one hard control with an identical preregistered
   non-temporal categorical signature.
5. Terminal-state, record-type, and event-kind signatures are not perfectly
   target/control separable.
6. No single categorical value or schema path uniquely identifies trigger,
   mechanism, or component.
7. Target/hard-control message-category frequencies and cause-bearing lexical
   templates are balanced exactly by construction.
8. Component aliases are neutral and require evidence-based ownership mapping.
9. Timestamp, row-order, log-order, evidence-ID-order, and token-order ablation
   cannot be bypassed by another ordering channel.
10. Controls pass deterministic plausibility, cardinality, linkage, and
    distractor audits across the full development construction range.
11. A mandatory counterfactual-separability report shows collisions rather
    than perfect separation for every frozen non-temporal signature family.
12. Validation and held-out ranges remain ungenerated and uninspected during
    design.

These are qualitative design gates plus exact construction properties; no
post-result model-accuracy threshold is introduced.

## Research implication

The result is methodologically useful rather than wasted. Showing
`Raw = Relative-time` demonstrates preservation but not necessity. A
privacy-preserving diagnostic benchmark must also show that destroying the
claimed invariant removes information needed for the task.

Candidate paper contribution, not yet a final claim:

> Diagnostic-invariant privacy evaluation requires both preservation tests and
> destructive controls; otherwise a model may appear robust because the
> benchmark can be solved through invariant-independent shortcuts.

## Execution status

The following configs and hashes remain frozen, but provider execution is:

**PAUSED — pending benchmark-cue investigation**

- `redaction-v1`;
- `hmac-v1`;
- `tokenization-v1`;
- `format-preserving-v1`.

No config or preregistered hash is deleted or modified by this finding.
