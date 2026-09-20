# Minimum privacy-exposure analysis for development ModelViews

Analysis version: `privacy-exposure-analysis-v1`. This document fixes the
measurement definitions before interpreting the generated development table.
The observer sees the complete released `ModelView`: question, structured rows,
log entries, evidence IDs, attributes, messages, order, and source inventory.
The evaluator uses the raw `ModelView` and benchmark sensitive-field
annotations *locally* to select and align measurements. Neither annotations nor
oracle labels enter the released view or the machine-readable artifact.

## Scope and denominators

The deterministic development corpus is Incident 001 seeds 1000–1004,
Incident 002 seeds 1000, 1001, 1003, 1004, 1005, 1017, and Incident 003 v3
constructions 1319, 1299, 1387, 1222 with both `target` and `temporal_twin`
queries. No validation, held-out, retired, or newly selected seed is accessed.
Only implemented, supported combinations are evaluated: raw plus redaction,
HMAC, tokenization, and format-preserving pseudonymization for Incidents 001
and 002; raw, relative-time, and temporal ablation for Incident 003 v3.

An occurrence is one annotated scalar at a source-qualified field path in one
visible evidence row. Rows are aligned by visible `evidence_id`, not hidden
generator metadata or log position; this remains valid when temporal ablation
reorders logs. A semantic comparison group is `(classification, field name)`.
Its field paths may span sources. Typed equality distinguishes, for example,
the string `"1"` from integer `1`. Null values are excluded from literal and
identity-pair denominators but remain in presence/cardinality checks.

Every proportion records `numerator`, `denominator`, `fraction`, and `status`.
An empty denominator is `not_applicable` with a null fraction, not zero
exposure. Family-condition summaries micro-sum counts over constructions.
Incident 003's two query roles are measured individually, but the aggregate
uses one `target` view per construction only after exact vector parity with its
`temporal_twin` is verified. No confidence interval or p-value is attached to
these deterministic selected constructions.

## Frozen dimensions

1. **Protected literal exposure:** fraction of all non-null annotated scalar
   occurrences whose original typed value remains anywhere in the released
   `ModelView`. The **non-temporal direct-literal** subfraction excludes
   `operational_timestamp` annotations. Explicit complementary counts report
   originals **not** verbatim visible, without implying they are uninferable.
   Exact scalar matching includes every
   field and the question. For string literals of at least six characters,
   verbatim embedding in another visible string also counts. This is literal
   disclosure, not identity reconstruction from a token or schema. The
   six-character substring cutoff applies only to this ordinary exposure
   metric, to limit accidental matches for very short values.
2. **Within-view equality and inequality:** among occurrence pairs in the same
   semantic group, report preservation of raw-equal pairs and separation of
   raw-unequal pairs separately. Both released values must be present for a
   positive equality claim. All-to-one redaction may preserve equal pairs
   while failing unequal-pair separation; it must never be called faithful
   linkage solely from the first ratio.
3. **Frequency/multiplicity:** for a semantic group with at least two raw
   distinct entities and at least one repeated entity, compare the sorted
   equality-class-size histogram in raw versus released values. Report the
   fraction of eligible groups with an identical histogram. This measures
   observable multiplicity, not knowledge of which real identity owns a class.
4. **Cross-source linkage:** repeat the equal-pair preservation and
   unequal-pair separation counts only for distinct annotated source paths
   within a semantic group. The metric includes structured↔structured and
   structured↔log joins where present; an absent positive denominator is
   `not_applicable`. Independent namespaces can deliberately lose a join.
5. **Format/shape:** for annotated strings, compare exact length, per-character
   uppercase/lowercase/digit class, and literal separators. Report the
   shape-preserved fraction and counts classified as exact literal, changed
   same-shape, opaque token, generic redaction, relative offset, other changed,
   or absent. This does not claim resistance to candidate-set reconstruction.
6. **Presence/cardinality:** count source buckets (including logs) with their
   record counts unchanged; annotated occurrences whose field remains present
   at the aligned row (a placeholder counts as present); and semantic groups
   with at least two raw distinct entities whose distinct count remains
   unchanged. Source or row removal is not silently recoded as redaction.
7. **Absolute time:** scan the raw visible evidence for strict RFC3339 scalar
   timestamps, including *unannotated* timestamps. Count the fraction of
   original timestamp occurrences still verbatim visible anywhere in the
   released `ModelView`. This exposes retained I001/I002 timestamps even
   though those families do not annotate them as sensitive.
8. **Relative temporal structure:** over every pair of distinct raw visible
   instants, report the fraction with two parseable released values
   (`temporal_pair_evaluability`), the fraction retaining strict order, and
   the fraction retaining the exact inter-event difference in microseconds.
   Parsing accepts only the repository's strict RFC3339 or canonical
   `T+<integer>ms` semantics; mixed or opaque strings are unavailable, never
   lexically ordered. A zero under ablation means the relation is not
   recoverable from timestamp representations, not that its reversed order
   was observed. An additional matched-pair construction audit, not this
   scalar ratio alone, addresses the Incident 003 causal distinction.
9. **Secret literal exposure:** fields explicitly classified `secret` or
   assigned `never_release` policy are checked against the entire released
   view. String secrets use exact typed matching and verbatim substring
   scanning of every visible string, with **no minimum length**; non-string
   secrets use typed exact matching only, without string coercion. Any match
   fails closed with an exception that contains neither the value nor the
   transformed view. The current development
   benchmark has no such annotation, so its secret ratio is
   `not_applicable`; synthetic tests exercise both failure and safe removal.

The exact detector does not estimate inferability from public pseudonym
algorithms, auxiliary dictionaries, known time anchors, or retained context.
The ordinary metric's short-string embedding cutoff limits accidental substring
matches and may miss a short literal embedded in a longer free-text field;
the classified-secret fail-closed check does not use that cutoff. Counts concern
annotated fields except the explicitly broader timestamp scan; unannotated
identifiers, message text, evidence IDs, inventory, and question context can
remain exposed and are not covered by a claim of comprehensive de-identification.

## HMAC analysis key and applicability

The offline HMAC comparison derives a fixed **public, synthetic, test-only**
32-byte key from a versioned label. It does not read the operational
`DIAGPRIV_HMAC_KEY_HEX`, persist a key, or model compromise of a real key.
Consequently the exact HMAC token bytes in this offline analysis are not the
historical provider experiment's token bytes; only exposure properties of
the same transformation and namespace policy are compared.
HMAC v1's existing namespace construction omits incident identity; the same
typed value in the same namespace under one key yields the same token across
incidents. A synthetic identity-reuse test verifies that property. Independent
generator samples do not constitute a cross-incident identity-reuse attack
corpus, so no empirical cross-incident link rate is inferred from them.

The analysis never runs a model. It does not alter any generator, oracle,
transformation, RCA protocol, or frozen experimental JSONL. The machine-readable
artifact contains counts, ratios, versions, case IDs, and aggregation rules,
but no original protected values, secret key, prompt, or provider output.

## Deterministic development results

The checked-in machine-readable record is
`docs/data/privacy_exposure_development_v1.json`. It contains 79 per-case
vectors and 13 family-condition summaries. For Incident 003, both query roles
were measured and had identical exposure vectors for all four constructions
and three conditions; the summary counts each underlying construction once.
The artifact records the synchronized baseline `main` SHA, generator/protocol
versions where declared, actual transformation versions, counts, and the
micro-sum aggregation rule. It contains no protected literals or HMAC key.
Per-case ratio numerators and denominators are encoded as two-element arrays;
the family summaries also serialize the derived fraction and applicability
status. This compact encoding does not discard any measured count.

The following ratios are numerator/eligible denominator, not a weighted
privacy score. `Direct` is non-temporal annotated literal exposure; `Equal`
is raw-equal pair preservation; `Separate` is raw-unequal pair separation;
`Cross` is cross-source raw-equal pair preservation; `Freq` is eligible
frequency-histogram preservation; `Shape` is protected string shape retention.

| Family | Released condition | Direct | Equal | Separate | Cross | Freq | Shape |
|---|---|---:|---:|---:|---:|---:|---:|
| 001 | raw | 476/476 | 559/559 | 3459/3459 | 326/326 | 20/20 | 476/476 |
| 001 | redaction-v1 | 0/476 | 233/559 | 1709/3459 | 0/326 | 0/20 | 0/476 |
| 001 | hmac-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 15/20 | 0/476 |
| 001 | tokenization-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 15/20 | 0/476 |
| 001 | format-preserving-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 15/20 | 476/476 |
| 002 | raw | 190/190 | 300/300 | 2656/2656 | 248/248 | 6/6 | 190/190 |
| 002 | redaction-v1 | 0/190 | 52/300 | 1680/2656 | 0/248 | 0/6 | 0/190 |
| 002 | hmac-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 6/6 | 0/190 |
| 002 | tokenization-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 6/6 | 0/190 |
| 002 | format-preserving-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 6/6 | 190/190 |

Incident 001's 50 lost equal pairs and 50 lost cross-source equal pairs
under HMAC, tokenization, and format-preserving pseudonymization are the
`payment_id` joins deliberately placed in independent path namespaces. This
does not contradict their preservation of the essential request-identity
linkage. Their 15/20 frequency result also reflects that namespace split.
Redaction is not faithful linkage merely because some equal pairs remain
equal: it also collapses many distinct values, as the separation and
frequency columns show. Format-preserving-v1 retains per-character shape;
the opaque baselines do not. These results are not a claim that the public
format-preserving algorithm provides cryptographic FPE or anonymity.

Record counts and annotated field presence were preserved for **every**
condition above: Incident 001 has 20/20 source-bucket record counts and
476/476 annotated field occurrences; Incident 002 has 30/30 and 190/190.
Distinct-entity counts are separate: Incident 001 preserved 40/40 raw,
2/40 redacted, and 35/40 under each deterministic pseudonym baseline; the
five misses in the latter are again the independent `payment_id` namespaces.
Incident 002 preserved 6/6 raw and under each deterministic pseudonym
baseline, but 0/6 after redaction.
Crucially, those families' **unannotated** visible timestamps were also
preserved verbatim by every scalar condition: 139/139 in Incident 001 and
478/478 in Incident 002. Removing annotated identifiers does not hide all
temporal context in those incidents.

For Incident 003 v3, the 204 raw visible timestamp occurrences and 5,004
distinct-time pairs below are micro-totals over the four unique constructions,
not duplicated across the two query roles. `ID literal` counts annotated
non-temporal operational identifiers. `Order` and `Difference` use only
parseable model-visible time semantics, never lexical marker order.

| Released condition | ID literal | Absolute timestamps | Order | Exact differences | Timestamp shape | Record counts / field presence |
|---|---:|---:|---:|---:|---:|---:|
| raw | 192/192 | 204/204 | 5004/5004 | 5004/5004 | 204/204 | 24/24 / 396/396 |
| relative-time-v1 | 192/192 | 0/204 | 5004/5004 | 5004/5004 | 0/204 | 24/24 / 396/396 |
| temporal-ablation-v1 | 192/192 | 0/204 | 0/5004 | 0/5004 | 0/204 | 24/24 / 396/396 |

Relative-time-v1 hides the original absolute timestamp literals but retains
all measured ordering and exact differences at its declared millisecond
precision. Temporal-ablation-v1 replaces them with non-temporal markers;
temporal-pair evaluability is 0/5004, so its zero order/difference rates mean
**unavailable**, not observed reversal. The separate matched-pair construction
audit establishes that the target and temporal twin need conflicting temporal
mechanisms while their ablated views are structurally isomorphic after
identifier normalization. These metrics characterize the representation;
they do not alone prove why the model answered as it did. Both temporal
conditions leave annotated operational identifier literals 192/192 visible.

The existing HMAC namespace formula has no incident identifier. Under the
same key and namespace, a controlled synthetic repeated identifier maps to
the same token across incidents. This is a measured implementation property,
not an estimated cross-incident attack success rate; independently generated
development incidents do not provide a controlled identity-reuse corpus.
No current development field is annotated as a secret, so the secret-exposure
ratio is `not_applicable`, not a measured zero-risk claim. Synthetic tests
confirm that a literal secret in *any* released field fails closed.

## Reproduction and manuscript boundary

```bash
uv run python -m diagpriv.privacy.exposure --output docs/data/privacy_exposure_development_v1.json
uv run python -m diagpriv.privacy.exposure --check docs/data/privacy_exposure_development_v1.json
```

The first command regenerates the deterministic JSON; the second verifies
exact byte identity without rewriting it. No wall-clock time or dynamic HEAD
is serialized. The companion compact manuscript table is
`docs/PAPER_RESULTS_TABLES.md`. Issue #43 should import the counts and
definitions from these files rather than recalculate or round them from prose.

Manuscript-ready factual statements are: annotated direct literals are absent
under the four scalar baselines in the selected Incident 001/002 ModelViews;
HMAC/tokenization preserve many, but not all, cross-source links in Incident
001; format-preserving pseudonymization retains the measured original
character-class patterns; relative-time removes absolute timestamp literals
while retaining exact measured inter-event differences; and temporal ablation
removes parseable time relations in the selected Incident 003 v3 views.

These are exposure properties of synthetic development representations—not
re-identification probabilities, membership-inference success, compliance
assessments, differential privacy, k-anonymity, legal de-identification,
provider retention/security findings, or proof of zero risk. Candidate-set
reconstruction, known-anchor reconstruction, cross-incident reuse, and
auxiliary-data attacks require separately specified adversaries and tests.
