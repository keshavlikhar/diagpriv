# Incident 002 Privacy Comparison Protocol

## Status and scope

This document preregisters the matched Incident 002 privacy comparison before
any privacy-condition provider observation. The frozen raw comparison baseline
is the GPT-5.6 Sol development result: 6/6 valid responses, 4/6 exact RCA, and
4/6 `overall_correct`. Outcome, trigger, subsequent action, and failure
mechanism were correct in 6/6; affected component was correct in 4/6. The raw
result SHA-256 is
`b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f`.

The comparison prepares all four privacy conditions together:
`redaction-v1`, `hmac-v1`, `tokenization-v1`, and
`format-preserving-v1`. The transformation implementations, namespace rules,
benchmark, oracle, prompt, taxonomy, scorer, invariants, evidence, model, and
seed set are frozen before execution. `format-preserving-v1` is described as
format/constraint-preserving pseudonymization, not cryptographic FPE.

Every condition uses Incident 002, seeds 1000, 1001, 1003, 1004, 1005, and
1017, one call per seed, GPT-5.6 Sol, medium reasoning, omitted temperature,
`raw-rca-v2`, `rca-taxonomy-v2`, `raw-rca-scorer-v2`, and
`raw-rca-manifest-v6`. Validation and held-out lists are empty.

## Preregistered outcomes and hypothesis

The primary reporting metrics remain exact five-dimensional RCA,
`overall_correct`, each of the five RCA dimensions, evidence precision/recall/F1,
valid-response and failure counts, token usage, and estimated cost. Incident
002's preregistered diagnostic dimensions are `trigger` and
`failure_mechanism`, because the frozen raw Sol baseline achieved 6/6 on both.
Affected-component accuracy remains fully reported and is not downweighted.

The development hypothesis is:

`Raw ≈ Format-preserving > HMAC / Tokenization / Redaction`

particularly for `trigger = malformed_or_unexpected_input` and
`failure_mechanism = validation_or_input_handling_failure`. This is a
hypothesis, not an expected result to enforce. Contrary observations must be
retained unchanged.

## Offline invariant audit

The audit evaluates only visible transformed ModelViews. Hidden generator
metadata does not satisfy a structural predicate. In particular, seed 1005's
hidden cause remains `leading_zero_loss`, while its visible structural delta is
`numeric_run_leading_position_deletion`.

Status codes are `G` = genuine preservation, `B` = broken, `D` = degenerate
pattern collapse, and `—` = invariant not declared for that seed. The invariant
columns are:

- `HIPC`: `healthy_identifier_pattern_consistency`
- `TIPA`: `target_identifier_pattern_anomaly`
- `TIDS`: `target_identifier_defect_signature`
- `TILD`: `target_identifier_length_delta`
- `TICSI`: `target_identifier_cross_source_identity`
- `CICSI`: `control_identifier_cross_source_identity`
- `TLMS`: `target_lookup_miss_state`
- `CLSS`: `control_lookup_success_state`
- `CEP`: `control_effect_presence`
- `TEO`: `target_event_order`
- `TEA`: `target_effect_absence`
- `TACID`: `target_and_control_identifier_distinctness`

| Condition | Seed | HIPC | TIPA | TIDS | TILD | TICSI | CICSI | TLMS | CLSS | CEP | TEO | TEA | TACID |
|---|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Redaction | 1000 | D | B | B | B | B | B | G | G | G | G | G | B |
| Redaction | 1001 | D | B | B | B | B | B | G | G | G | G | G | B |
| Redaction | 1003 | D | B | B | — | B | B | G | G | G | G | G | B |
| Redaction | 1004 | D | B | B | B | B | B | G | G | G | G | G | B |
| Redaction | 1005 | D | B | B | B | B | B | G | G | G | G | G | B |
| Redaction | 1017 | D | B | B | B | B | B | G | G | G | G | G | B |
| HMAC | 1000 | B | B | B | B | G | G | G | G | G | G | G | G |
| HMAC | 1001 | B | B | B | B | G | G | G | G | G | G | G | G |
| HMAC | 1003 | B | B | B | — | G | G | G | G | G | G | G | G |
| HMAC | 1004 | B | B | B | B | G | G | G | G | G | G | G | G |
| HMAC | 1005 | B | B | B | B | G | G | G | G | G | G | G | G |
| HMAC | 1017 | B | B | B | B | G | G | G | G | G | G | G | G |
| Tokenization | 1000 | D | B | B | B | G | G | G | G | G | G | G | G |
| Tokenization | 1001 | D | B | B | B | G | G | G | G | G | G | G | G |
| Tokenization | 1003 | D | B | B | — | G | G | G | G | G | G | G | G |
| Tokenization | 1004 | D | B | B | B | G | G | G | G | G | G | G | G |
| Tokenization | 1005 | D | B | B | B | G | G | G | G | G | G | G | G |
| Tokenization | 1017 | D | B | B | B | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1000 | G | G | G | G | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1001 | G | G | G | G | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1003 | G | G | G | — | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1004 | G | G | G | G | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1005 | G | G | G | G | G | G | G | G | G | G | G | G |
| Format/constraint-preserving | 1017 | G | G | G | G | G | G | G | G | G | G | G | G |

The discardable `literal_external_reference_identity` invariant has expected
non-preservation under every privacy transformation. No other per-defect
exception was observed. Seed 1003 lacks `target_identifier_length_delta` by
design because case-class mismatch does not change identifier length.

The empirical high-level matrix therefore matches the preregistration:

| Condition | Equality/linkage | Identifier structure |
|---|---|---|
| Raw | preserved | preserved |
| Redaction v1 | damaged | unavailable; pattern equality is degenerate |
| HMAC v1 | preserved | unavailable |
| Tokenization v1 | preserved | unavailable; token-pattern equality is degenerate |
| Format/constraint-preserving v1 | preserved | preserved |

## Frozen transformed-input provenance

`prompt_sha256` remains the template hash
`744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d`.
Manifest schema v6 records `model_input_sha256` over the exact rendered prompt.
The configurations preregister the following expected hashes, and dry-run and
execution preflight reconstruct all six transformed prompts and fail before
provider setup if a hash differs. A new manifest schema is unnecessary.

| Condition | 1000 | 1001 | 1003 | 1004 | 1005 | 1017 |
|---|---|---|---|---|---|---|
| Redaction v1 | `4ead5fc58caf…b3a2` | `10e655bd365b…155e` | `10eddbe3ea2f…34d8` | `a23e5deb3ba1…193` | `3d66f5311dc0…26f0` | `33eab7a6961a…5e4` |
| HMAC v1 | `94813c0294fd…212c` | `eba260443389…a746` | `c7803f059390…7de5` | `d43e37d02604…8f80` | `5260a58dafd1…6b20` | `64c301cac97a…5ffd` |
| Tokenization v1 | `66a3b9aa3b4a…1cb0` | `6bb0c75d95db…228c` | `bd440ccc4fa0…a48c` | `df838a3a2edf…c345` | `a765a7e0b310…06f6` | `dc1e58d27ab0…da01` |
| Format/constraint-preserving v1 | `76cd30855d3e…e53a` | `b7f553459d8a…05b0` | `de629ae11487…e86b` | `f0b7182216c5…4e4b` | `3c8d8d944602…6e3d` | `e61aa72f7251…d331` |

The complete hashes are stored in the four experiment configurations. No
`transformed_model_view_sha256` field is added: the exact rendered-input hash
already provides the required per-observation provenance without changing
historical manifest semantics.

HMAC uses external variable `DIAGPRIV_HMAC_KEY_HEX`, key ID
`hmac-v1-synthetic-experiment-key-001`, and non-secret key fingerprint
`fd04c65f6329f9e8c42b392ea8b9253a6c88da58e6f3858a322228bee907997d`.
The key itself is not stored in configuration, prompts, manifests, JSONL,
logs, exceptions, or object representations.

## Configurations and prospective artifacts

| Condition | Configuration | Prospective ignored result |
|---|---|---|
| Redaction v1 | `experiments/incident_002_redaction_v1_sol_development.toml` | `results/incident_002_redaction_v1_sol_development_gpt_5_6_sol_medium.jsonl` |
| HMAC v1 | `experiments/incident_002_hmac_v1_sol_development.toml` | `results/incident_002_hmac_v1_sol_development_gpt_5_6_sol_medium.jsonl` |
| Tokenization v1 | `experiments/incident_002_tokenization_v1_sol_development.toml` | `results/incident_002_tokenization_v1_sol_development_gpt_5_6_sol_medium.jsonl` |
| Format/constraint-preserving v1 | `experiments/incident_002_format_preserving_v1_sol_development.toml` | `results/incident_002_format_preserving_v1_sol_development_gpt_5_6_sol_medium.jsonl` |

Preparation and dry runs do not authorize any provider call. All four
conditions require separate human execution approval and the explicit
`--execute` flag.
