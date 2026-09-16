# RCA v3 Methodology Decision

## Status

This document records the approved design and its offline implementation. The
following versions are implemented and tested but have not been sent to a
provider:

- `rca-taxonomy-v3`
- `raw-rca-v3`
- `raw-rca-scorer-v3`
- `evidence-support-v3`

New observations use `raw-rca-manifest-v9`. The frozen `raw-rca-v3` template
SHA-256 is
`a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`.

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

## Other mechanism boundaries

### `missing_or_ineffective_idempotency`

Use when repeated executions share one logical identity and suppression or safe
replay alone would prevent the duplicate outcome. It takes precedence over
generic retry and concurrency framing when that counterfactual is satisfied.

### `non_atomic_commit_or_rollback`

Use when a logically indivisible multi-part commit or rollback can partially
apply under serialized execution. If the failure requires overlapping actors,
the concurrency-control category applies instead.

### `incorrect_retry_policy`

Use only when the retry decision, timing, or bounds remain defective assuming
effective idempotency. A harmless retry that becomes harmful only because
deduplication is missing is an idempotency failure, not a retry-policy failure.

### `stale_or_inconsistent_data`

Use when a well-formed but obsolete or divergent view is itself the proximal
defect. Corrupted data or an integrity-constraint violation is
`data_integrity_failure`. If the conflicting state was admitted because
fencing, version checking, compare-and-set, locking, or serialization was
missing, the proximal mechanism is `incorrect_concurrency_control`.

### `dependency_contract_failure`

Use when a producer and consumer disagree about an established
inter-component promise. Use `validation_or_input_handling_failure` when the
responsible local component fails to reject, normalize, parse, bound, or look
up input under its own obligation. These boundaries are stored in the
machine-readable taxonomy metadata as exclusions, confusables, and decision
guidance.

## Blinded mapping of existing families

The accepted mapping uses construction facts only, not model predictions.

| Family | Outcome | Trigger | Action | Mechanism | Component | Change from v2 |
|---|---|---|---|---|---|---|
| Incident 001 | `duplicate_effect` | `timeout_or_deadline` | `retry_or_rearrival` | `missing_or_ineffective_idempotency` | `operation_executor` | None |
| Incident 002 | `missing_effect` | `malformed_or_unexpected_input` | `no_follow_on_action` | `validation_or_input_handling_failure` | `operation_executor` | None |
| Incident 003 v1 construction under v3 | `inconsistent_state` | `timeout_or_deadline` | `compensation_or_rollback` | `incorrect_concurrency_control` | `workflow_orchestrator` | Mechanism only |

Under the v3 boundary, Incident 003 is no longer ambiguous: its
outcome depends on overlapping execution and compensation both taking effect,
and fencing or cancellation enforcement would prevent that outcome.

## Incident 003 v2 offline implementation

The protocol and generator are versioned instead of mutating v1. Identifiers
are:

- `incident-003-generator-v2`
- `incident-003-temporal-protocol-v2`

`temporal-semantics-v1`, the model-visible construction, diagnostic invariants,
and temporal ablation remain unchanged. The implemented v3 oracle is:

```text
observed_outcome = inconsistent_state
trigger = timeout_or_deadline
subsequent_action = compensation_or_rollback
failure_mechanism = incorrect_concurrency_control
affected_component = workflow_orchestrator
```

This oracle is implemented offline but not empirically qualified. The v1
instance's v2 oracle remains present and unchanged; no historical observation
is relabelled or rescored.

## Model-facing prompt boundary

The `raw-rca-v3` prompt contains only:

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

The implementation is split deliberately:

- `diagpriv/evaluation/evidence_support_v3.py` contains only family-neutral
  rubric types, validation, canonical serialization, hashing, and scoring;
- `diagpriv/evaluation/incident_003_v2_evidence.py` declares the Incident 003
  v2 subjects, requirements, and alternative paths; and
- `diagpriv/evaluation/evidence_protocols.py` dispatches a family/protocol to
  its rubric builder outside the generic scorer.

The generic evaluator receives a completed rubric and ModelView. It imports no
Incident 003 generator or family identifier and contains no Incident 003
source, deadline, or compensation semantics.

### Canonical rubric and preregistration

The normative rubric representation is compact UTF-8 JSON with sorted object
keys and no insignificant whitespace or trailing newline. Subject bindings,
requirements, alternatives, evidence-ID lists, and semantic parameters are
sorted by stable identifiers so the digest does not depend on Python object
identity, collection insertion order, pretty-printing, platform newline
behavior, or builder traversal order. The representation includes every
semantic field: protocol version; requirement ID, necessity class, and
normative description; alternative ID; required and optional evidence IDs;
semantic predicate and parameters; subject binding; redundancy class; and
minimum-group requirement. Runtime caches are excluded.

For each planned observation, the rubric is constructed and validated during
input preflight, its SHA-256 is compared with the tracked per-seed value, and
the same construction/hash check occurs again during run preparation before
provider invocation. A missing evidence ID, unresolved/cross-subject binding,
unsupported predicate, or hash mismatch fails closed before provider setup in
the CLI preflight.

### Subject binding and flat-citation policy

Every visible evidence ID that may legitimately appear is bound to one frozen
subject role: target, designated contrast/control, or an explicitly allowed
supportive subject. A requirement path is confined to one binding, and rubric
validation rejects paths that combine subjects. A citation is:

- contributing when it belongs to a selected satisfied path;
- redundant when it repeats an ID or supplies an additional interchangeable
  path already satisfied elsewhere;
- contextual when its subject is allowed but it contributes to no selected
  path;
- wrong-subject when its visible subject is incompatible with every declared
  role; or
- nonexistent when its evidence ID is absent from ModelView.

Because the response schema exposes one flat evidence list rather than a
claim-to-citation mapping, v3 adopts the conservative deterministic rule that
any wrong-subject citation makes `evidence_supported=false`. Nonexistent IDs
also veto support. Duplicate, redundant, and allowed contextual citations do
not veto support; they remain visible in precision/redundancy metrics.

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

### Primary evidence metrics

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
satisfied, no nonexistent citation is used, and the flat citation list contains
no wrong-subject citation. Contrast coverage is not required.

The implemented overall criterion is:

```text
overall_correct_v3 = exact five-dimensional RCA AND evidence_supported
```

No opaque composite evidence measure will replace the primary metrics. A
derived F1 may be secondary analysis only. Historical v2 exact-ID evidence
precision, recall, and F1 remain unchanged.

The implementation retains secondary `evidence_precision`, `evidence_recall`,
and `evidence_f1` fields solely for reporting compatibility. They are derived
from useful-citation precision and essential-requirement coverage and do not
replace the primary semantic metrics.

## Fresh Incident 003 development policy

The eight v1 provider-observed seeds are historical, regression, or protocol-
debugging inputs only. They may not be presented as fresh qualification evidence
for a revised protocol.

The implemented selection rule is
`incident-003-v2-first-two-per-temporal-template-unobserved-v1`: begin at seed
1019, inspect only temporal-template metadata in ascending order, retain the
first two previously unobserved seeds for each of the four templates, and stop
when each template has two. Selection must not use position, warnings, expected
difficulty, transformation behavior, or model behavior.

The frozen future set is:

```text
1019, 1020, 1021, 1022, 1023, 1025, 1026, 1028
```

These seeds had not been sent to a provider when this methodology was frozen.
The later raw v3 qualification is recorded separately and does not change this
preregistration decision.

The tracked preparation config freezes both exact rendered model-input and
evidence-requirement-set hashes:

| Seed | Model input SHA-256 | Evidence requirement-set SHA-256 |
|---:|---|---|
| 1019 | `2fdd467c9408b66de7a370b5bf7f9877316dfbfa4204bb93ff4c250b9822f452` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| 1020 | `454b06bcb400c718ac4ed6a29e4fba618d7b280f2bec13c1d03198246c4ac18e` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| 1021 | `4d5c3f69abfd5d8eb795fbf1dd5044e4a4621d49f8457ae9778780b2dae02f29` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| 1022 | `2135b32e0712b9feb2744a70f182b33c784f4d7797322b0e3f901aa9b6b71fba` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| 1023 | `f9c14cb3c14036565bd1a026fc96fce1c33abe88e8011a7f0e5926c88960c8c4` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| 1025 | `6275bcc7cc6531bdefacd060655c6613b504413c2b4053b897c3b74f6f52b2bc` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| 1026 | `be72cf270b660c9dd857a08fe7878d9adf1405dcbd73107097371b66a23eba6b` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| 1028 | `1acbf564bb312397a57935dbb81d8bd7307465b6a2e6d3667f834e110e030b14` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |

The corrected canonical ordering changed these rubric digests from the
audit-derived provisional values; no prior v3 provider observation exists.

## Manifest and reporting compatibility

`raw-rca-manifest-v9` records prompt/taxonomy/scorer/evidence-protocol versions,
Incident generator and protocol versions, the prompt-template SHA-256, exact
`model_input_sha256`, exact `evidence_requirement_set_sha256`, provider/model
and decoding provenance, execution/failure metadata, and the v3 score's
individual requirement outcomes and selected path IDs. Historical v2-v8
schemas and artifacts are not rewritten.

Summary serialization omits the nullable v3-only aggregate fields for legacy
observations, preserving the prior v2 report shape. V3 summaries expose the
semantic coverage and citation classifications explicitly.

## Compatibility policy

- Keep `raw-rca-v2`, `rca-taxonomy-v2`, `raw-rca-scorer-v2`, and historical
  observations unchanged.
- Do not reinterpret the Incident 003 v1 result as 8/8 after changing labels.
- Treat any v3 score as a new protocol result, not a correction of v2.
- Use a new manifest schema when v3 evidence fields are implemented.
- Complete static leakage, deterministic evidence-path, and fresh-seed reviews
  before any provider call.
