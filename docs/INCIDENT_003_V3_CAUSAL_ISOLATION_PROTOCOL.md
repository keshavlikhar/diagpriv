# Incident 003 v3 causal-isolation protocol

Status: **READY TO COMMIT after the reviewed offline positional and paired-query
correction.** No provider configuration or observation exists.

## Motivation and versioning

Incident 003 v2 produced 8/8 exact RCA under raw, `relative-time-v1`, and
`temporal-ablation-v1`, while temporal-ablation evidence support was 0/8. The
provider-free cue audit found perfect target/control separation from terminal
states, record presence, and event kinds without temporal semantics. V2 remains
immutable historical evidence; v3 is separately versioned:

- family: `incident_003_temporal_compensation_v3`;
- generator: `incident-003-generator-v3`;
- temporal protocol: `incident-003-temporal-protocol-v3`;
- audit: `incident-003-v3-causal-isolation-audit-v1`;
- projection: `incident-003-v3-nontemporal-projection-v1`;
- requirements: `incident-003-v3-evidence-requirements-v2`;
- semantic evaluator: `incident-003-v3-evidence-semantic-evaluator-v2`;
- paired query cases: `incident-003-v3-paired-query-v1`;
- raw-log anchor allocation:
  `incident-003-v3-role-neutral-anchor-allocation-v1`;
- final identifier/position audit: `incident-003-v3-final-leakage-audit-v1`.

The candidate retains `rca-taxonomy-v3`, `raw-rca-v3`,
`raw-rca-scorer-v3`, and `evidence-support-v4`. No global prompt, taxonomy, or
scorer change is required.

## Scientific question and construction

The benchmark asks whether correct RCA depends on deadline-relative ordering,
execution/compensation overlap, and settling sequence rather than recognizable
non-temporal signatures. The target mechanism remains
`incorrect_concurrency_control`.

Each construction contains three model-visible operations:

1. **Target:** execution remains active when post-deadline compensation starts;
   the intervals overlap; original execution succeeds and records an active
   effect.
2. **Temporal twin:** execution succeeds and records the same active effect
   before the deadline; later compensation is serialized. Its identical
   terminal tuple is an `incorrect_state_transition` contrast.
3. **Safe compensation:** the deadline occurs, execution is cancelled and
   settles, its effect is inactive, and compensation starts afterward without
   overlap.

The neutral model-facing question is:

> Determine the root cause for operation `<operation_id>` from the available
> operational evidence and cite supporting evidence IDs.

The operation ID supplies subject binding, not a label. Normalizing it makes
the target and twin question templates identical. Oracle labels remain outside
ModelView.

## Temporal-twin principle

The target and temporal twin share workflow state `compensated`, successful
execution, an active effect, completed compensation, all five structured record
types, the same nine event kinds, source and field names, service aliases,
dependency values, message family, identifier cardinality, and cross-source
linkage topology.

The non-temporal projection normalizes operation/effect/compensation/evidence
identifiers, neutralizes timestamps, canonically sorts records, and excludes
hidden roles. Across seeds 1200–1399 all 200 target/twin projections are exactly
equal. There are no residual differences. Any future difference fails closed
as unreviewed label leakage.

## Known-shortcut mitigation

| V2 shortcut | V3 treatment | Offline result |
|---|---|---|
| Compensated + success + active effect + compensation | Exact target/twin match | Collision in 200/200 pairs |
| Deadline fields/events/messages | Same categories in target and twin | Not target-specific |
| Compensation fields/events/messages | Same categories in target and twin | Not target-specific |
| Record-type combination | Exact five-source inventory match | Collision in 200/200 pairs |
| Event-kind combination | Exact nine-kind inventory match | Collision in 200/200 pairs |
| Outcome-revealing question | Neutral subject-specific request | No outcome/mechanism wording |
| Orchestrator-like aliases | Neutral codenames shared across roles | No near-label alias |
| Operation linkage | Same linkage topology | Subject binding only |

Deadline and compensation names remain realistic strong schema cues but occur
in both target and twin. The design tests reasoning without relying on
vocabulary obscurity.

## Message and schema audits

Target and twin use the same neutral per-construction message template. Messages
do not state “after,” “before,” “late,” “concurrent,” “overlap,” “still
executing,” cancellation failure, fencing failure, or a rollback race. Event
kinds remain realistic but match exactly.

Strong balanced schema cues include `deadline_at`, compensation records,
execution result, effect state, workflow state, and event kind. Service
ownership uses one neutral `service_alias` field in every structured source,
with opaque internal codenames as values; linkage is a necessary weak cue. The
audit finds no near-label component alias and exact source, field, and
cardinality matching.

## Signature, feature, and conjunction audits

| Non-temporal signature | Target/twin collisions |
|---|---:|
| Full categorical content | 200/200 |
| Terminal-state tuple | 200/200 |
| Structured record-type inventory | 200/200 |
| Log event-kind inventory | 200/200 |

Every categorical/string-derived token in the paired projection is compared.
No single target-only or twin-only feature exists in 200 pairs. Deterministic
conjunctions of sizes 2, 3, and 4 over known v2 cue families yield zero
separators. This targeted audit is not an exhaustive proof against every learned
representation.

## Temporal invariants

Every target satisfies:

`dispatch < execution_start < deadline < compensation_start < original_completion`

plus positive execution/compensation overlap, an active successful effect after
compensation starts, the inconsistent terminal tuple, and cross-source linkage.

Every temporal twin satisfies:

`dispatch < execution_start < original_completion < effect < deadline < compensation_start < compensation_completion`

with no overlap. Every safe control satisfies deadline before
cancellation/settling, settling before compensation, and no overlap. All target
and control invariants pass in 200/200 raw constructions.

## Relative time and temporal ablation

Unmodified `relative-time-v1` uses one incident-local millisecond anchor. In
200/200 constructions it preserves all 51 timestamp slots, equality, strict
ordering, pairwise duration, target overlap, control non-overlap, deadline
crossing, and every declared invariant.

`temporal-ablation-v1` is extended only to accept the new family ID. It retains
its historical behavior: every annotated timestamp becomes a unique
non-parseable marker and log order is replaced by non-temporal audit order. In
200/200 constructions temporal values and relations are unavailable, while
target/twin non-temporal projections remain equal.

## Evidence-support-v4

The query-role-aware constructor does not reuse v2 rubric hashes. Target-query
essentials are:

1. subject identity/linkage;
2. deadline before original completion;
3. compensation after deadline;
4. execution/compensation overlap;
5. successful active effect after compensation begins;
6. inconsistent terminal workflow/effect state.

The twin-query essentials are:

1. subject identity/linkage;
2. successful execution and active effect before deadline;
3. compensation after the already committed success;
4. serialized execution completion before compensation, establishing no
   concurrency is required;
5. the inconsistent terminal workflow/effect state.

For a target query, the twin is the serialized contrast. For a twin query, the
overlapping target is the concurrency contrast. The safe operation remains a
contrast and queried lifecycle evidence remains supportive. With all
preregistered evidence cited, raw and relative time satisfy both query-role
rubrics in 200/200 constructions. Temporal ablation leaves four of six target
essentials and three of five twin essentials unsatisfied, so neither mechanism
is evidence-identifiable. Generic evidence-support-v4 semantics are unchanged.

## Acceptance gates

| Gate | 200-instance result |
|---|---|
| Deterministic generator/oracle | Pass |
| Target temporal invariants | 200/200 |
| Twin and safe-control temporal invariants | 200/200 |
| Relative-time preservation | 200/200 |
| Temporal-ablation destruction | 200/200 |
| Four v2 signature families collide | 200/200 each |
| Single-feature separators | Zero |
| Known 2/3/4-feature conjunction separators | Zero at every size |
| Normalized question equality | 200/200 |
| Record/event inventory matching | 200/200 |
| Role/message/linkage balancing | 200/200 |
| Raw and relative evidence-v4 satisfiable | 200/200 |
| Ablated temporal essentials unavailable | 200/200 |
| Validation/held-out access | None |

No provider configuration may be prepared until methodology review. A failed
major gate means `BLOCKED — DO NOT PREPARE PROVIDER RUN`.

## Final identifier, position, and ordering audit

The first order-sensitive audit found a material shortcut: operation windows
were always anchored in target, twin, safe-control order, so their nine-record
raw-log blocks always occupied indices 0–8, 9–17, and 18–26. Because the
question named the target, its first-block position exposed the hidden role.
That finding blocked the candidate before any provider preparation.

The correction retains globally chronological raw logs. A dedicated
SHA-256-domain-separated RNG stream assigns the three absolute anchor slots
independently of role, query role, oracle, mechanism, and the main construction
stream. Each operation's internal offsets and causal facts are unchanged. Logs
are globally sorted by their genuine timestamps with the existing neutral
evidence-ID tie-breaker. Across seeds 1200–1399, target first/middle/last block
counts are 65/73/62, twin counts are 60/64/76, and safe-control counts are
75/63/62. Their mean first-log indices are 8.865, 9.720, and 8.415; every median
is 9. No raw-log role-position separator remains.

## Paired-query principle

Every construction now supports two query cases over exactly the same evidence
and exact same serialization:

- `query_role = target` names the overlap case and has mechanism
  `incorrect_concurrency_control`;
- `query_role = temporal_twin` names the serialized-invalid-transition case and
  has mechanism `incorrect_state_transition`.

The construction seed, all structured rows, all logs, identifiers, timestamps,
messages, source ordering, and row ordering are identical between query cases.
Only the operation ID in the neutral question, hidden query-case metadata, and
the mechanism-specific oracle explanation change. The five scored dimensions
share outcome `inconsistent_state`, trigger `timeout_or_deadline`, subsequent
action `compensation_or_rollback`, and component `workflow_orchestrator`; only
failure mechanism differs. Taking both query roles for each construction yields
an exactly balanced future population without consuming additional seeds.

This pairing establishes a structural identifiability check. Under raw and
relative-time semantics, the target query has positive overlap/late-effect
evidence and the twin query has positive serialized post-success-compensation
evidence in 200/200 constructions. After temporal ablation, query-independent
evidence serialization remains exact, normalized question templates match,
and the canonical queried-subject slices are isomorphic in 200/200 pairs. The
two hidden mechanism oracles still conflict, while neither evidence rubric is
satisfied. This is a structural benchmark property, not statistical proof of
model behavior.

The audit did not find a literal-identifier shortcut. Operation, effect,
compensation, and evidence identifiers use fixed class-neutral prefixes and
eight random decimal digits. Their numeric ranges overlap; first/last digit,
parity, and lexical ranks overlap by role. Identifier generation uses a
SHA-256-domain-separated seed to initialize an incident-local PRNG, and the
fixed internal creation order is not encoded as an ordinal in the literal.
Evidence-ID minimum/maximum ranks show finite-sample imbalance but no perfect
separator.

Structured-row shuffling also prevents a fixed position. Target row-index
counts for indices 0/1/2 were 57/78/65 in `workflow_attempts`, 80/79/41 in
`execution_observations`, 75/64/61 in `effect_records`, 81/68/51 in
`compensation_records`, and 55/73/72 in `dependency_health`. Every role appears
at every position in every source. After temporal ablation, target first-log
positions were 0/1/2 in 71/67/62 constructions; twin counts were 64/63/73 and
safe-control counts were 65/70/65. No ablated-log positional separator exists.

Audit-only canonical renaming, consistent identifier permutation, and
non-semantic row permutation each preserved oracle and evidence semantics in
200/200 constructions. The strongest order-preserving rendered non-temporal
comparison is performed on `temporal-ablation-v1`, which removes temporal
values and deliberately replaces chronological log order. It normalizes only
linked identifiers and timestamp values, retains source, field, record,
message, event-kind, categorical, and rendered row order, and finds target/twin
isomorphism in 200/200 pairs. The raw view is not used for that non-temporal
comparison because its chronological event order intentionally carries the
temporal mechanism under test.

Normalized target/twin question templates match in 200/200. Hidden role,
mechanism, oracle, and template metadata is absent from every ModelView. TA1
markers retain the historical
`TA1::<source>::<evidence_id>::<field>` representation; their structure is
role-neutral, all corresponding target/twin lexical comparisons vary across
seeds, and ablated log reordering introduces no perfect role separator.

| Final leakage gate | Result |
|---|---|
| No literal identifier property perfectly separates roles | Pass |
| No queried-subject positional property perfectly separates roles | Pass |
| No non-temporal structured/ablated row order perfectly separates roles | Pass |
| Canonical ID renaming preserves conclusions | 200/200 |
| ID permutation preserves oracle and evidence semantics | 200/200 |
| Row permutation preserves oracle and evidence semantics | 200/200 |
| Order-preserving rendered non-temporal isomorphism | 200/200 |
| Question wording neutral after ID normalization | 200/200 |
| Hidden metadata absent from ModelView | 200/200 |
| TA1 markers introduce no class-correlated artifact | 200/200 |
| Existing 25 gates remain passing | Pass |

Perfect-separator counts after correction are zero for literal identifier,
target position, source-row index, evidence-ID pattern, grouping/order,
question position, and TA1-derived properties. The known size-2/3/4
non-temporal conjunction counts also remain zero.

| Updated paired-query gate | Result |
|---|---|
| Raw-log role position is not a perfect separator | Pass |
| Queried position is not a mechanism separator | Pass |
| Query roles share underlying evidence | 200/200 |
| Serialization is independent of query role | 200/200 |
| Balanced paired population is constructible | 200 target + 200 twin |
| Raw target concurrency evidence is satisfiable | 200/200 |
| Raw twin state-transition evidence is satisfiable | 200/200 |
| Relative time preserves both query diagnoses | 200/200 each |
| Ablated query-pair isomorphism | 200/200 |
| Ablated paired mechanism oracles conflict | 200/200 |
| Non-temporal single-feature separators | Zero |
| Known size-2/3/4 conjunction separators | Zero |
| Literal-ID mechanism separator | Zero |
| TA1 role/mechanism separator | Zero |
| Safe-control invariants | 200/200 |

All original 25 gates and the earlier identifier/renaming/permutation gates
remain passing. Offline readiness is `READY TO COMMIT`. Provider configuration
and execution remain a separate, later checkpoint.

## Operational plausibility and limitations

- The twin models a serialized state-machine defect: compensation is committed
  after successful completion. It shares the target snapshot but not its
  concurrency mechanism.
- The safe control's inactive effect record represents observed non-application,
  allowing record inventories to remain matched without claiming an active
  effect.
- Naming the queried operation avoids a multi-fault question and is treated as
  subject binding, not an answer cue.
- Neutral internal codenames reduce component-label leakage but are less
  descriptive than some production service names. Ownership must be inferred
  from emitted deadline, compensation, and workflow events.
- Exact projection equality is a construction property, not proof that every
  model will use temporal evidence or that the benchmark is externally valid.
- The audit is development-only on seeds 1200–1399. No validation or held-out
  construction was generated or inspected.

## Execution status

No provider config, model-input preregistration, result JSONL, or provider call
exists for v3. The final leakage audit is offline and development-only. The four
remaining v2 destructive baselines remain frozen and paused pending benchmark
redesign/cue-isolation review.
