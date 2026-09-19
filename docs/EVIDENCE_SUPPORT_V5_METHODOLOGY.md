# Evidence Support v5 Methodology

Status: candidate for methodology review. This protocol was designed offline
after the Incident 003 v3 Stage-1 raw forensic audit. It is post hoc for that
artifact and has not been used for a provider experiment.

## Motivation and historical boundary

The frozen Stage-1 artifact recorded 40 valid citations, no nonexistent IDs,
no wrong-subject citations, and model-visible semantic predicates that were
true for every preregistered v4 path. Nevertheless, v4 scored all eight cases
unsupported because each requirement exposed only one concrete physical path,
usually a complete structured-row set. Semantically equivalent lifecycle-log
proofs were not registered.

This is a path-model limitation, not a generic semantic-evaluator failure.
Evidence support v5 therefore adds alternative representation-specific paths
without weakening the facts each requirement must prove. Evidence v4,
`incident-003-v3-evidence-requirements-v2`, its scores, and every historical
manifest remain unchanged and historically correct under v4.

Identifiers:

| Layer | Identifier |
|---|---|
| Evidence protocol | `evidence-support-v5` |
| Rubric schema | `evidence-rubric-v5` |
| Incident requirement constructor | `incident-003-v3-evidence-requirements-v3` |
| Generic path templates | `incident-003-v3-evidence-path-templates-v1` |
| Semantic evaluator | `incident-003-v3-evidence-semantic-evaluator-v3` |
| Offline construction audit | `incident-003-v3-evidence-v5-construction-audit-v1` |
| Stage-1 secondary analysis | `incident-003-v3-stage1-evidence-v5-secondary-analysis-v1` |

The prompt remains `raw-rca-v3`; ModelView, generator, transformations, RCA
taxonomy, scorer labels, and oracle are unchanged.

## Representation-invariance rule

One semantic requirement may expose multiple minimal evidence paths. Every
path is resolved from generic schema roles or event kinds into the evidence IDs
of a generated case. No response-derived or qualification-case ID appears in a
template.

A path is satisfied only when:

`all required IDs are cited AND the semantic predicate is true on those exact model-visible records`.

There is no prose grading, fuzzy matching, uncited evidence completion, or
partial credit for citation volume. Every accepted path binds to exactly one
registered subject. Raw RFC3339 and `relative-time-v1` use explicit parsers;
opaque temporal-ablation markers have unavailable temporal semantics and fail
temporal predicates closed.

## Identity and linkage

V5 separates two questions that v4 combined:

- `queried_subject_identity` is essential. Any one cited record must visibly
  carry the queried operation ID and match the query binding.
- `queried_cross_source_linkage` is supportive. It requires two distinct
  structured sources, or two distinct lifecycle events emitted by distinct
  service roles, with one shared queried operation ID.

Cross-source linkage does not gate the diagnosis because every multi-record
causal path independently enforces one queried identity. Paired and safe-control
records cannot satisfy queried essentials.

## Essential requirements and sufficient paths

### Target query

| Requirement | Structured path | Log path | Sufficiency |
|---|---|---|---|
| Queried subject identity | any one queried row | any one queried event | visibly binds a cited fact to the query |
| Deadline before completion | workflow + execution | deadline reached + successful execution completed | proves strict deadline-before-success order |
| Compensation after deadline | workflow + compensation | deadline reached + compensation started | proves strict trigger/action order |
| Execution/compensation overlap | execution interval + compensation interval | execution started + execution completed + compensation started + compensation completed | both representations prove valid intervals and strict positive overlap using `max(start) < min(end)`; disjoint and boundary-touch cases fail |
| Late successful original effect | execution + effect + compensation | compensation started + successful execution completed + active effect recorded | proves successful completion and active effect after compensation began |
| Inconsistent terminal state | workflow + execution + effect | successful execution completed + active effect recorded + compensated workflow recorded | proves exactly successful execution + active effect + compensated workflow; compensation completion is not an additional obligation |

### Temporal-twin query

| Requirement | Structured path | Log path | Sufficiency |
|---|---|---|---|
| Queried subject identity | any one queried row | any one queried event | visibly binds a cited fact to the query |
| Successful active effect before deadline | workflow + execution + effect | successful execution completed + active effect recorded + deadline reached | proves strict success/effect/deadline order |
| Compensation after committed success | workflow + effect + compensation | active effect recorded + deadline reached + compensation started | proves exactly active committed effect < deadline < compensation start; compensation result/completion is not an additional obligation |
| Serialized completion before compensation | execution + compensation | successful execution completed + compensation started | proves exactly successful execution completion < compensation start; full interval validity is not part of this requirement |
| Inconsistent terminal state | workflow + execution + effect | successful execution completed + active effect recorded + compensated workflow recorded | proves exactly successful execution + active effect + compensated workflow; compensation completion is not an additional obligation |

No mixed-modality path is registered because neither family requirement needs
one. A response may cite both modalities, but at least one complete structured
or log path must independently pass.

## Contrast and supportive evidence

Contrast remains a separately reported evidence-quality dimension, not a gate
on `evidence_supported`. A valid diagnosis of the queried operation does not
scientifically require citing an unrelated paired operation or safe control.
The contrast requirements still test whether citations establish:

- the paired target/twin temporal distinction; and
- cancellation, inactive effect, and settled-before-compensation behavior in
  the safe control.

Supportive coverage is also reported separately. The single v4 seven-log
volume requirement is replaced by meaningful semantic units:

- queried cross-source linkage;
- deadline followed by compensation initiation; and
- successful active effect plus compensated terminal workflow state.

These units receive no partial credit unless their complete semantic path is
cited and true.

## `evidence_supported`

V5 returns `evidence_supported = true` exactly when:

1. every essential semantic requirement has at least one satisfied path;
2. no cited ID is nonexistent; and
3. no unsupported wrong-subject citation is present.

A complete registered contrast path may cite its paired/control subject without
becoming a wrong-subject citation. Partial unrelated-subject citations do not
gain that exception. Contrast and supportive coverage never compensate for a
missing essential.

The existing essential, contrast, supportive, useful-precision, invalid,
wrong-subject, contextual, redundant, and compatibility P/R/F1 fields remain.
Their v5 values must be labeled with the v5 protocol; they are not replacements
for historical v4 fields.

## Anti-overfitting procedure and audits

The requirement templates were derived from the Incident 003 schema and
semantic definitions. Generic raw/relative/ablation and negative tests were
implemented and passed before the frozen Stage-1 submitted citations were
rescored.

Across all 200 development constructions, seeds 1200–1399, and both query
roles:

- raw complete structured paths passed 200/200 per role;
- raw complete log paths passed 200/200 per role;
- relative-time structured and log paths passed 200/200 per role;
- temporal-ablation structured and log temporal proof was rejected 200/200 per
  role;
- wrong-role evidence was rejected 200/200 per role; and
- safe-control evidence was rejected as queried failure proof 200/200 per role.

Focused negative tests cover wrong temporal relations, strict-overlap failure,
post-deadline twin effects, wrong subjects, lone deadline/success/compensation
events, incomplete overlap and serialized paths, safe-control confusion,
nonexistent IDs, other operations, and target/twin cross-use. Structured and
log overlap paths are also compared under genuine overlap, compensation fully
before execution, execution fully before compensation, equality at a boundary,
and malformed execution or compensation intervals. Both representations return
the same truth value in every case. Structured/log parity tests separately
exercise valid and adversarial cases for compensation-after-success, terminal
state inconsistency, and serialized completion. They verify strict boundaries,
inactive/cancelled/non-compensated states, and that non-normative compensation
completion fields do not silently strengthen only the structured path. The
four frozen qualification constructions—1319, 1299, 1387, and 1222—pass the
same generic benchmark-derived complete-path checks for both roles.

## Raw, relative-time, and ablation expectations

- Raw uses `temporal-semantics-v1` and permits structured or log paths.
- `relative-time-v1` uses `relative-time-semantics-v1`; all required relations
  remain provable without calendar identity.
- `temporal-ablation-v1` uses explicit unavailable temporal semantics. Identity
  and terminal-state facts may remain satisfiable, but order, overlap,
  deadline-crossing, and serialized-transition requirements cannot pass from
  opaque markers.

V5 therefore preserves the structural negative control.

## Stage-1 secondary analysis

The explicit offline analyzer verifies the frozen JSONL SHA-256 before loading,
does not rewrite it, and emits a separate report. Results are documented in
`docs/INCIDENT_003_V3_STAGE1_EVIDENCE_V5_ANALYSIS.md`.

V5 evidence support is independent of RCA-label correctness. In particular,
`1222:temporal_twin` can have supported evidence while its frozen mechanism
label remains incorrect. The supported language is:

> V5 uses a broader representation-invariant semantic evidence model developed
> post hoc after the Stage-1 forensic audit.

It is not appropriate to say that v4 was wrong.

## Manifest recommendation

No provider manifest schema is added in this task. Manifest v11 has the fields
needed for evidence version, requirement hash, and evaluator provenance, but
its frozen validator intentionally permits v4 only. A future provider run using
v5 should therefore introduce manifest v12 rather than broaden v11 in place.
That decision should occur with prospective v5 approval and experiment
preregistration. Offline secondary analysis requires no provider manifest.

## Limitations

- V5 is post hoc for raw Stage 1 and is not experimentally validated.
- The positive-overlap requirement uses explicit start and completion endpoints
  for both intervals and rejects malformed intervals. The separate serialized
  requirement intentionally asks only whether a successful execution completion
  strictly precedes compensation start; it does not certify full interval
  well-formedness. Equality at either strict boundary does not pass.
- Flat citation lists cannot express which statement each ID was intended to
  support; the deterministic scorer selects the smallest passing path.
- Contrast non-gating is a methodology choice, not evidence that controls are
  unimportant.
- Development seeds 1200–1399 support construction auditing only; no validation
  or held-out claim follows.
- Prompt citation instructions were not changed. A future prompt-v4 study would
  be a separate variable and experiment.
