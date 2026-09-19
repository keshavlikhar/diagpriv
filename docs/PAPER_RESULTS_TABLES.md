# Paper-ready development privacy-exposure tables

Source: `privacy-exposure-analysis-v1`,
`docs/data/privacy_exposure_development_v1.json`; exact metric definitions and
limitations are in `docs/PRIVACY_EXPOSURE_ANALYSIS.md`. All entries are
numerator/eligible denominator from deterministic selected **development**
ModelViews. No single privacy score or inferential statistic is implied.

## Annotated identifiers and shape

| Family | Condition | Direct literal | Equal-pair retention | Distinct-pair separation | Cross-source equal retention | Format shape |
|---|---|---:|---:|---:|---:|---:|
| 001 | raw | 476/476 | 559/559 | 3459/3459 | 326/326 | 476/476 |
| 001 | redaction-v1 | 0/476 | 233/559 | 1709/3459 | 0/326 | 0/476 |
| 001 | hmac-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 0/476 |
| 001 | tokenization-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 0/476 |
| 001 | format-preserving-v1 | 0/476 | 509/559 | 3459/3459 | 276/326 | 476/476 |
| 002 | raw | 190/190 | 300/300 | 2656/2656 | 248/248 | 190/190 |
| 002 | redaction-v1 | 0/190 | 52/300 | 1680/2656 | 0/248 | 0/190 |
| 002 | hmac-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 0/190 |
| 002 | tokenization-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 0/190 |
| 002 | format-preserving-v1 | 0/190 | 300/300 | 2656/2656 | 248/248 | 190/190 |

The 50 Incident 001 cross-source equal pairs lost by each deterministic
pseudonym baseline are independently namespaced `payment_id` joins, not the
essential shared request-ID linkage. The scalar baselines preserve record and
sensitive-field presence, and leave **unannotated** absolute timestamps
visible (Incident 001: 139/139; Incident 002: 478/478). Frequency-histogram
and distinct-count measures are in the machine-readable source; notably,
Incident 001 distinct-count preservation is 35/40 for each deterministic
pseudonym baseline, not 40/40.

## Incident 003 v3 temporal exposure

Four frozen constructions (1319, 1299, 1387, 1222) are counted once each;
target/twin query roles have identical measured exposure vectors. The
ordering/difference denominator includes 5,004 distinct-time pairs.

| Condition | ID literal | Absolute time | Order recoverable | Exact difference recoverable | Presence/cardinality |
|---|---:|---:|---:|---:|---:|
| raw | 192/192 | 204/204 | 5004/5004 | 5004/5004 | 396/396 fields; 24/24 source counts |
| relative-time-v1 | 192/192 | 0/204 | 5004/5004 | 5004/5004 | 396/396; 24/24 |
| temporal-ablation-v1 | 192/192 | 0/204 | 0/5004 | 0/5004 | 396/396; 24/24 |

For ablation, 0/5004 means time semantics are unavailable, not reversed.
Relative-time-v1 retains precise offsets and may permit absolute-time
reconstruction with an external anchor. Neither condition removes operational
identifier literals. This table describes exposure only; pair-level RCA
utility and prospective evidence-support-v5 outcomes remain in the frozen
Incident 003 result documents.

These numbers are not re-identification probabilities, anonymity guarantees,
compliance findings, or evidence of provider-side security. Paper issue #43
should cite the versioned artifact and retain the family-specific denominators.
