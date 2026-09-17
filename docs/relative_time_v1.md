# `relative-time-v1` protocol

Status: implemented, audited offline, and evaluated once on the frozen Incident
003 v2 matched development set. The result is immutable.

## Research intent

`relative-time-v1` removes literal timestamp identity while retaining the
incident-local temporal relations required to diagnose Incident 003. It is a
task-aware temporal representation, not conventional timestamp format
preservation, fake timestamp generation, cryptographic protection, or a claim
of anonymization.

The preregistered directional hypothesis for Incident 003 is:

`Raw ≈ Relative-time-v1 > Redaction / HMAC / Tokenization / existing Format-preserving`

The completed run tests only the raw-versus-relative portion of this qualitative
development hypothesis. Destructive temporal conditions have not run under the
matched v3 protocol, so the complete ordering is not an empirical result.

## Frozen semantics

| Property | Value |
|---|---|
| Transformation | `relative-time-v1` |
| Parser | `relative-time-semantics-v1` |
| Manifest | `raw-rca-manifest-v10` |
| Anchor | `earliest-model-visible-annotated-timestamp-v1` |
| Precision | integer milliseconds |
| Syntax | `T+<nonnegative-integer>ms` |
| Annotation classification | `operational_timestamp` |
| Scope | `annotated-model-view-fields-only` |
| Transformation-config SHA-256 | `cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660` |

The hash preimage is deterministic compact UTF-8 JSON with sorted keys, no
insignificant whitespace, and no trailing newline:

```json
{"anchor_rule":"earliest-model-visible-annotated-timestamp-v1","annotation_classification":"operational_timestamp","precision":"milliseconds","representation":"T+<nonnegative-integer>ms","scope_policy":"annotated-model-view-fields-only","temporal_semantics_version":"relative-time-semantics-v1","transformation_version":"relative-time-v1"}
```

The algorithm is:

1. Copy the complete ModelView defensively.
2. Select every sensitive-field annotation classified as
   `operational_timestamp`.
3. Strictly parse every selected value with unchanged
   `temporal-semantics-v1` RFC3339 semantics.
4. Choose the minimum parsed visible instant across all structured sources and
   logs as the single incident-local anchor.
5. Replace every selected value with its exact millisecond offset from that
   anchor. The minimum becomes `T+0ms`.
6. Preserve every non-temporal field and all row/log ordering exactly.

The anchor does not use target metadata, generator role, oracle labels,
invariants, expected evidence, or scoring metadata. Equal source instants map to
one equal offset even when they appear in different evidence sources.

Example from development seed 1019 (the anchor is an earlier visible control,
so the target begins after `T+0ms`):

| Target field | Raw | Relative |
|---|---|---|
| dispatch | `2036-08-29T05:46:13.770Z` | `T+360561ms` |
| deadline | `2036-08-29T05:46:37.770Z` | `T+384561ms` |
| compensation start | `2036-08-29T05:46:41.770Z` | `T+388561ms` |
| execution completion | `2036-08-29T05:46:50.770Z` | `T+397561ms` |
| effect creation | `2036-08-29T05:46:50.991Z` | `T+397782ms` |

## Precision decision

Milliseconds are the minimum safe precision for the current generator. Across
development construction seeds 1000–1199, all source values are
millisecond-aligned, the smallest positive observed separation is 10 ms, and
2,531 adjacent distinct instants would collapse into a tie if offsets were
reduced to whole seconds. Millisecond offsets therefore preserve current strict
ordering without retaining unused microsecond precision.

Inputs not aligned to milliseconds fail closed. A future generator requiring
different precision needs a new reviewed transformation version or explicit
protocol revision.

## Alternatives considered

- **Exact offsets (selected for v1):** removes literal calendar identity while
  preserving exact equality, ordering, durations, gaps, overlap, and deadline
  relationships. This gives the cleanest first controlled comparison.
- **Bucketed offsets (deferred):** leak less precision but can introduce ties or
  change threshold relations.
- **Order-only values (deferred):** retain sequence but discard duration,
  overlap magnitude, and deadline gaps.
- **Threshold-preserving values (deferred):** could retain only registered
  boundary crossings, but needs a separate leakage and task-dependence review.

Exact offsets are not claimed to be privacy-optimal. The deferred designs are
future ablations, not silently interchangeable implementations of v1.

## Information removed

For annotated timestamp fields, the ModelView no longer contains the original:

- calendar date or year/month/day representation;
- wall-clock time;
- timezone or UTC offset;
- Unix epoch;
- RFC3339 string; or
- timestamp formatting.

The privacy audit checks every original timestamp occurrence, rejects surviving
literal timestamp strings, and rejects calendar, wall-clock, timezone, RFC3339,
or epoch syntax in transformed temporal values. This does not prove anonymity.

## Information intentionally preserved

The condition intentionally exposes:

- exact incident-local offsets at millisecond precision;
- total incident-local temporal span;
- ordering and same-instant equality;
- durations and gaps;
- positive interval overlap; and
- deadline crossings.

Operation/evidence IDs, aliases, states, results, effect and compensation IDs,
source names, log messages, warnings, latency fields, row cardinality, and row
order are unchanged. `relative-time-v1` does not combine temporal conversion
with redaction, HMAC, tokenization, or format-preserving pseudonymization.

## Residual privacy risk

Exact gaps, durations, equality/frequency, temporal span, and relative event
sequence remain linkable. An observer with outside timing knowledge may
correlate a distinctive sequence even without literal date or wall-clock time.
If an observer independently knows the absolute time of one transformed event,
the exact relative offsets can permit reconstruction of the absolute times of
other events in the same transformed incident.

The transformation deliberately preserves exact gaps, durations, ordering,
same-instant equality, interval overlap, deadline crossings, and the total
incident-local temporal span. It is an absolute-time-removal transformation,
not a complete temporal anonymization mechanism, proof of anonymity, or proof
of zero re-identification risk. This is an intended research tradeoff.

The transform also preserves all non-temporal identifiers, because this first
experiment isolates only the temporal variable. The protocol therefore makes
no claim of unlinkability, anonymity, zero re-identification risk, or
production readiness.

## Parser and historical compatibility

`temporal-semantics-v1` remains RFC3339-only and unchanged. Canonical relative
values use the separate `relative-time-semantics-v1` parser. Offline invariant
evaluation selects the relative parser explicitly; the default remains the raw
parser. Historical transformations, prompts, scorers, and observations retain
their prior meaning.

Manifest v10 persists the transformation version, parser semantics, anchor
rule, precision, representation, annotation classification, scope policy, and
the preregistered SHA-256 of their canonical compact JSON representation. The
configuration hash is recomputed during dry-run and immediately before provider
initialization. It is not part of the model-visible prompt.

## Offline audit

The deterministic audit generated only development construction seeds
1000–1199. It evaluated 17 per-instance properties for 200 instances: 3,400 of
3,400 checks passed. The checks cover determinism, literal removal, one shared
anchor, parseability, equality, strict ordering, duration, overlap, deadline
crossing, essential/control/legitimate-compensation temporal invariants,
non-temporal equality, cardinality, row order, evidence IDs, and linkage.

Seed 1021 was audited separately: raw execution completion equals compensation
completion, and both transform to the same parsed relative offset. This is
genuine equality, not placeholder collapse.

The offline condition matrix is:

| Condition | Literal secrecy | Parseable time | Equality | Order/duration/overlap/deadline | Required temporal invariants |
|---|---|---|---|---|---|
| Raw | broken | genuine | genuine | genuine | genuine |
| Redaction-v1 | genuine | expected non-preservation | degenerate collapse | expected non-preservation | expected non-preservation |
| HMAC-v1 | genuine | expected non-preservation | expected non-preservation | expected non-preservation | expected non-preservation |
| Tokenization-v1 | genuine | expected non-preservation | expected non-preservation | expected non-preservation | expected non-preservation |
| Format-preserving-v1 | genuine | expected non-preservation | expected non-preservation | expected non-preservation | expected non-preservation |
| Relative-time-v1 | genuine | genuine | genuine | genuine | genuine |

These are code/invariant observations, not LLM utility results.

## Evidence-support compatibility and preregistration

The v3 evidence requirement meanings, subject bindings, evidence IDs, and
acceptable paths do not change. Consequently, each transformed seed has the
same evidence-requirement-set SHA-256 as raw. The rendered model-input hashes
change because literal timestamps are replaced.

| Seed | Transformed `model_input_sha256` | Evidence requirement-set SHA-256 |
|---:|---|---|
| 1019 | `606420ee8a2832b5e2ceee584ceb0c5133dec90785632d7ee1e28a8c32d23cda` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| 1020 | `ffff6212ea681333d391b0271635c91222c15b05d0f45daeb26b9e76f3939523` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| 1021 | `b70bf4170fc96755b1ad2e97e80f3c307edbdf0fbdbce61d4ec91336e4f0a8c0` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| 1022 | `782134836be932b1510abadd833a58437d56afaa5b56df715e6576e99012e90b` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| 1023 | `c9df2c0f54c9b99747f846d3414df86a7864570046b5ca258a89a0cce5fdfd9e` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| 1025 | `603990c45c51cfa4f28fb522404f73c9e0422a4436ab6d6a9d12fb74dc112723` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| 1026 | `4a62763f53e76517d7f4c30ce0861c3df081ad177250f05ff30681fc3a2ee40b` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| 1028 | `03426719e9173d5a562713673a602b588fb49f38e42f1b56c868f36ed51bbf6d` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |

The completed matched configuration is
`experiments/incident_003_v2_relative_time_v1_sol_development.toml`. It used the
same eight fresh seeds, GPT-5.6 Sol, medium reasoning, omitted temperature,
`raw-rca-v3`, `rca-taxonomy-v3`, `raw-rca-scorer-v3`,
`evidence-support-v3`, and manifest v10. Its frozen ignored result is:

`results/incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl`

SHA-256:
`0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb`.

## Frozen matched finding

Both raw and `relative-time-v1` produced 8/8 valid responses and 8/8 exact
five-dimensional RCA. Relative time retained all eight raw-correct cases. Raw
had 0/8 evidence-supported responses; relative time had 1/8. Citation
completeness therefore remained substantially weaker than RCA-label accuracy.

> On these eight fresh matched Incident 003 development cases with GPT-5.6 Sol, replacing absolute timestamps with exact incident-relative millisecond offsets preserved all five RCA dimensions.

This is not evidence of statistical significance, validation or held-out
performance, behavior of other models, anonymity, or superiority over
destructive temporal transformations. See
`docs/INCIDENT_003_RELATIVE_TIME_V1_FINDINGS.md` for the complete frozen result,
artifact hashes, evidence analysis, usage, and interpretation limits.

The next separately reviewed comparison may include `temporal-ablation-v1`,
redaction-v1, HMAC-v1, tokenization-v1, and format-preserving-v1 on the same
eight seeds. None is authorized or executed by this document.
