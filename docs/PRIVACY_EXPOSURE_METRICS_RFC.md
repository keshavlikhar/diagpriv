# RFC: privacy-exposure metrics for matched DiagPriv comparisons

Status: proposed, for issue #24. This document defines a prospective measurement
plan; it does not change transformations or authorize experiments. Repository
claims below are based on main commit `85e0c1a`. No new observations were made.

## Question and threat boundary

Which observable properties does each transformation disclose, to which observer,
over which scope, and at what diagnostic utility? An exposure vector should
replace a single unqualified claim of being "more private."

Follow [THREAT_MODEL.md](THREAT_MODEL.md): the primary observer sees the complete
rendered ModelView and public algorithm/schema, but not oracle annotations,
mapping tables, or HMAC keys. Separate observers may see multiple incident
prompts, have a candidate identity dictionary, know a timestamp anchor, or have
access to a compromised key. The last scenario is a sensitivity scenario, not
part of the primary key-secret threat model. Provider retention and host
compromise are outside these measurements.

The audit receives raw synthetic evidence and annotations locally to measure
disclosure. That privilege belongs to the evaluator, never the proposed planner
or provider. Include the question, log messages, row order, evidence IDs, schema,
and retained context in the release surface, not just transformed scalar fields.

## Measurement contract

Let X be the raw view, Z the released view, O a preregistered set of annotated
scalar occurrences, and P_s the eligible occurrence pairs in scope s. Alignment
is evaluator-only, by source/row/field or stable evidence reference. It must not
be inferred from pseudonyms. Define typed equality on the original values.

Report numerators and denominators per field class, incident, and scope, then
macro-average over constructions with equal weight. Also report micro totals.
An empty eligible set is `not_applicable`, never zero exposure. Unknown coverage
is `unknown`, not a successful privacy result. Freeze missing/type-error policy.

| Dimension | Proposed operational measure | Interpretation and limitation |
|---|---|---|
| Direct identity | Fraction of O whose original typed value appears verbatim in the released payload, using field-aware matching; separately count unannotated identifier canaries | Measures literal disclosure, not inference. Public placeholders and short coincidental substrings need separate categories. |
| Within-field equality | On P_s, true-positive rate of output equality conditional on raw equality, and false-positive rate conditional on raw inequality | Always report both: all-to-one redaction can retain every positive match while destroying identity discrimination. |
| Frequency | Sorted equality-class count histogram, maximum class fraction, and normalized histogram distance against raw | Token frequencies remain visible even if the identity attached to each class is unknown. |
| Cross-field linkage | Pairwise precision/recall of linking occurrences from different field paths against true typed identity | Report allowed shared namespaces separately from independent paths; naming a field does not establish linkage. |
| Cross-source linkage | Same pair measures for distinct structured sources and structured/log pairs | A requested join and an unintended join are separate exposure entries. |
| Cross-incident linkage | Link precision/recall over preregistered repeated identities across different incidents, plus fraction of tokens stable for the same identity | Requires a controlled synthetic identity-reuse design. Independent generators with disjoint IDs cannot estimate this risk. |
| Format | Exact-match fractions for length, per-position letter case/digit class, alphabet, and literal separator layout | Publish each coordinate. A single "format preserved" flag hides which information is released. |
| Cardinality | Exact recovery of row/log/source counts and distinct-value counts; absolute error when altered | Baselines retaining every row disclose record counts even when identity is hidden. Distinct counts are different from record counts. |
| Presence/absence | Recovery of source, field, null, event-kind, and record-type presence vectors | Include sparse or rare inventory signatures, not only the number of fields. |
| Temporal | Recoverability of equality, strict order, interval overlap, duration, inter-event gap, total span, and absolute anchor | Distinguish unavailable semantics from wrong inferred order. Do not sort opaque tokens as timestamps. |
| Attributes and ranges | Exact value retention, recoverable units/types, and interval width for numeric values; preserved sign/order/ratio relations | Unannotated amounts, states, services, and messages may disclose values directly. Report field-specific coverage. |
| Auxiliary reconstruction | Top-1 identity accuracy, top-k recall, candidate-set reduction, and timestamp reconstruction error under a declared attack | An attack result requires its own adversary knowledge, budget, corpus, and baseline; it is not a universal privacy bound. |

For equality/linkage, define TP, FP, FN, TN explicitly on P_s using the released
equality predicate and true identity. Precision = TP/(TP+FP), recall =
TP/(TP+FN), FPR = FP/(FP+TN). If no positive predictions exist, precision is
undefined. Record the eligible field-pair list so unrelated types do not inflate
TN. Hash collisions, accidental equal placeholders, and genuine preserved
identity must have distinct audit categories.

For temporal relations, report both semantic coverage (fraction of eligible
relations evaluable in Z) and correctness among evaluable relations. For gaps,
use exact millisecond recovery plus absolute error with preregistered tolerances.
The denominator includes every preselected pair, including unavailable pairs.
For strict overlap require valid intervals and `max(start) < min(end)`.

For a numeric value disclosed only as interval [a,b], record b-a in declared
units; compare relative to a fixed, externally specified domain width. Do not
normalize using a secret sample minimum/maximum. Current baselines do not
implement interval generalization; this coordinate supports future candidates.

## What the current conditions expose by construction

All entries concern annotated fields unless stated otherwise. Read the actual
namespace and annotation set for the incident family. Nonannotated values stay
unchanged under the scalar privacy baselines.

| Condition | Identity/equality/linkage | Shape and other retained information |
|---|---|---|
| Raw | Literal values and all explicit joins | Full visible format, values, inventory, temporal information, and context |
| `redaction-v1` | Path/type placeholders collapse values; no intentional identity linkage | Retains record inventory/order and coarse JSON type; null remains null. Placeholder paths reveal schema. Unannotated context remains raw. |
| `hmac-v1` | Typed deterministic equality/frequency within namespace; shared namespaces link selected sources | Fixed digest representation loses input shape; row counts, presence, and unannotated context remain. Reused key enables cross-incident token persistence. |
| `tokenization-v1` | One-to-one, incident-population-local ordinal map within namespace; shared namespaces link sources | Prefixes disclose field/source class and distinct-value counts. Public deterministic assignment permits candidate-set attacks; no key protects it. |
| `format-preserving-v1` | One-to-one mapping with collision resolution and shared/path namespaces | Retains exact length, letter/digit classes, and literal punctuation; public deterministic candidate selection may enable dictionary attacks. Not standardized format-preserving encryption. |
| `relative-time-v1` | Non-temporal identifiers remain raw | Replaces annotated absolute time with exact offsets from the earliest visible annotated instant; retains temporal equality/order/gaps/durations/overlap and existing row order. |
| `temporal-ablation-v1` | Non-temporal identifiers and context remain raw | Removes timestamp semantics via distinct markers and deterministic log reordering. Inventory and marker-associated event presence remain; it is a diagnostic negative control, not a comprehensive privacy transform. |

Tokenization and format-preserving maps are not persistent vaults. A value can
change pseudonym when the candidate population changes, but incident-local maps
do not establish unlinkability: identical populations, distinctive shapes,
public deterministic algorithms, or retained context can still correlate them.
Relative-time releases remain reconstructable if an observer knows an event's
absolute anchor: `time(event) = known_time(anchor_event) + offset_difference`.

Evidence: [HMAC implementation](../diagpriv/transformations/hmac_v1.py),
[tokenization specification](tokenization_v1.md),
[format specification](format_preserving_v1.md),
[relative-time specification](relative_time_v1.md), and
[ablation implementation](../diagbench/audits/incident_003.py).
These are repository-derived properties, not external empirical findings.

## Resolve HMAC scope explicitly

`hmac_token` hashes version, namespace, JSON type, and canonical value under a
key. Its payload contains no incident ID. `consistent_pseudonym` uses
`shared:<classification>:<field>`; independent/remove-or-pseudonym policies use
`path:<source>.<field>`. Thus equal typed values under the same key and namespace
produce equal tokens even across incidents. Shared classification alone is not
enough: the field component also has to agree. Independent paths separate
sources, but repeating a path across incidents does not provide incident scope.

Proposal: evaluate all three scopes: within incident, across sources, and across
incidents. Report key scope and namespace scope separately. The current v1
comparison describes its actual reused-key scope. A future incident-scoped key
derivation or incident-bound namespace would require a new transformation
version and separate protocol; it cannot be claimed for v1.

HMAC's keyed construction is specified in [RFC 2104](https://www.rfc-editor.org/info/rfc2104/).
The scope conclusions above come from this repository's message construction;
HMAC itself does not choose an application's linkage policy.

## Measured exposure versus adversary-dependent risk

Direct retention, counts, equality classes, structural signatures, and temporal
relations can be measured deterministically on paired synthetic X/Z. The
observer need not know raw truth; the evaluator uses it solely for measurement.

Re-identification success cannot be inferred from those measurements alone.
Preregister separate synthetic attacks: a fixed candidate dictionary, a known
event anchor, a repeated-identity cross-incident corpus, and a public-algorithm
candidate-population attack. Freeze attack effort, candidate set size, attacker
training/test separation, and no-release/retained-context baselines. Compare
attack advantage over those baselines and stratify by dictionary entropy.
An attacker with the HMAC key is a separately labeled scenario.

Do not treat a zero score from one attack as a cryptographic bound, nor combine
an attack score and a deterministic preservation rate as interchangeable units.

## Matched comparison and exposure interface

Match construction, query, model, repetition, and scoring protocol first. Attach
an exposure record to each condition with `metric_version`, `observer_profile`,
`field_scope`, `namespace_scope`, `key_scope`, `numerator`, `denominator`,
`status`, and `measurement_method`. Raw IDs and key values stay local. Public
reports aggregate counts; even stable raw-data hashes may enable guessing.

Use a vector E and componentwise exposure ceilings B. Only compare utility at
the same preregistered exposure envelope when every required coordinate is
measurable and inside its ceiling. Describe incomparable vectors as a Pareto
tradeoff. Do not assert matched privacy merely because both conditions remove
names: format-preserving and HMAC differ in shape leakage, and relative time
retains identity. If current fixed baselines cannot meet a common envelope,
report that limitation; do not tune them after seeing utility results.

The planner RFC consumes conservative capability bounds plus schema-derived
counts. Empirical attack accuracy is not a runtime safety certificate. A scalar
weighted score can be secondary only with predeclared units/weights and
sensitivity analysis; it must not let low leakage in one field offset a secret.

## Acceptance and decisions to freeze

Before any evaluation, approve observer profiles, eligible pair sets, field
classifications, key lifetime, incident reuse corpus, temporal tolerances,
exposure ceilings, attack resources, aggregation rules, and report redaction.

Offline implementation acceptance should demonstrate:

- all-to-one redaction reports false equality rather than perfect linkage;
- shared and independent namespaces produce distinguishable scope reports;
- HMAC reuse and rotation scenarios are labeled separately;
- an empty denominator and unavailable temporal semantics never become zero risk;
- unchanged fields, query text, inventory, and timing side channels are included;
- metric output cannot serialize secrets, oracle content, or raw identities;
- identical inputs and metric versions produce identical deterministic reports.

These criteria are proposed future tests. This RFC neither runs attacks nor
produces exposure measurements, privacy guarantees, or new provider results.
