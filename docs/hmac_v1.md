# HMAC baseline v1

`hmac-v1` is a deterministic pseudonymization baseline for comparison with the
frozen raw-v2 and `redaction-v1` development observations. It is not reversible
encryption, format-preserving transformation, or task-aware DiagPriv selection.

## Exact transformation rules

1. Begin with `incident.model_view()` and a defensive copy.
2. Visit exactly the source-qualified paths in the incident's oracle-only
   `sensitive_fields` annotations. Reject duplicate, missing, composite, or
   unsupported annotated fields rather than allowing plaintext through.
3. Leave every non-sensitive field unchanged.
4. Convert each annotated JSON scalar to canonical compact JSON and add an
   explicit JSON type name. This distinguishes strings, numbers, booleans, and
   null values.
5. Construct this byte message, where `NUL` is one zero byte:

   ```text
   hmac-v1 NUL namespace NUL JSON-type NUL canonical-value
   ```

6. Compute HMAC-SHA-256 using the external 32-byte experimental key.
7. Encode the full 256-bit digest as unpadded URL-safe Base64 and prefix it with
   `HMAC1_`. Every transformed scalar therefore has one fixed pseudonym format;
   original formatting is not retained.

Namespaces are determined only from privacy annotations:

- `consistent_pseudonym` uses
  `shared:<classification>:<field-name>`. The same customer, account, or request
  identifier therefore maps identically across annotated evidence sources.
- `pseudonymize_independently` uses `path:<source>.<field>`. Equality and
  inequality are deterministic within that path, but matching plaintext at a
  different path is intentionally not linked.
- `remove_or_pseudonymize` also uses `path:<source>.<field>`. Direct identity
  fields are pseudonymized independently and are not linked across attributes.

Different canonical values within any namespace have different pseudonyms
except with the cryptographically negligible collision probability of a full
SHA-256 HMAC. Domain separation also prevents accidental equality across
unrelated namespaces.

## Experimental key and reproducibility protocol

The experiment uses one randomly generated 256-bit key identified by the
non-secret label `hmac-v1-synthetic-experiment-key-001`.

1. Generate the key exactly once with a cryptographically secure random source,
   for example `openssl rand -hex 32`.
2. Store the resulting 64 hexadecimal characters outside this repository in a
   local secret manager or untracked environment file as
   `DIAGPRIV_HMAC_KEY_HEX`.
3. Reuse that exact key for every seed and any later matched split assigned to
   this experimental key ID. Reproduction requires retrieving the same external
   secret; generating a replacement key produces structurally equivalent but
   byte-different pseudonyms.
4. Never place the key, a derived key, or an Authorization value in a benchmark
   fixture, TOML file, ModelView, manifest, JSONL result, prompt, or log.
5. Rotate to a new external key and a new non-secret key ID for a distinct
   experiment rather than silently replacing this key.

The repository contains public test-vector keys only. They are deliberately
non-secret and must never be used for an experiment.

## Incident 001 example

The following seed-1001 test vector uses the public byte sequence `00` through
`1f`, not the experimental key.

Before:

```json
{
  "payment_id": "SYN-PAY-95401729",
  "customer_id": "SYN-CUST-92252632",
  "account_id": "SYN-ACCT-35171490",
  "request_id": "SYN-REQ-23555431",
  "amount": "79.44",
  "status": "succeeded"
}
```

After:

```json
{
  "payment_id": "HMAC1_rDz1LSykpupLleyWCu-von7mA9zAcKYkzJaHYNkC8Rg",
  "customer_id": "HMAC1__rwLaPYSDZIjNPaEAMrM_fC_AFGt_hoBBtJ4nLkjhnU",
  "account_id": "HMAC1_HHWojiYeMlDNNsZhNGqo0ec3qnOXKGL6RCay54nhMf0",
  "request_id": "HMAC1_1oEsGYTJYIhjCMvAmBcsVKK4nOspCZ5ggDWJWKvEP_U",
  "amount": "79.44",
  "status": "succeeded"
}
```

The matching log `request_id` becomes the same
`HMAC1_1oEsGYTJYIhjCMvAmBcsVKK4nOspCZ5ggDWJWKvEP_U`, while its independently
pseudonymized `transport_id` receives a different token. Evidence IDs,
timestamps, levels, services, messages, amounts, and statuses are unchanged
because they are not annotated as sensitive.

## Incident 001 invariant profile

Offline evaluation is identical for development seeds 1000 through 1004:

| Invariant | Necessity | Status |
|---|---|---|
| `target_request_equality` | essential | `genuine_preservation` |
| `target_request_cross_source_identity` | essential | `genuine_preservation` |
| `unrelated_request_inequality` | essential | `genuine_preservation` |
| `target_payment_distinctness` | essential | `genuine_preservation` |
| `target_event_order` | essential | `genuine_preservation` |
| `target_success_state` | essential | `genuine_preservation` |
| `target_customer_equality` | supportive | `genuine_preservation` |
| `target_account_equality` | supportive | `genuine_preservation` |
| `target_amount_equality` | supportive | `genuine_preservation` |
| `payment_row_cardinality` | supportive | `genuine_preservation` |
| `exact_rearrival_interval` | discardable | `genuine_preservation` |
| `literal_customer_identity` | discardable | `expected_non_preservation` |
| `literal_account_identity` | discardable | `expected_non_preservation` |

All exact predicate results are true. The final two mean that the invariants'
declared expectation of discarding literal identity was met.

By contrast, `redaction-v1` degenerately preserved three within-path equalities
and broke request cross-source identity, unrelated-request inequality, and
payment distinctness. `hmac-v1` genuinely preserves those relationships while
introducing deterministic linkability inside its declared namespaces.

## Prepared development comparison

The reviewed offline configuration is `experiments/hmac_v1_development.toml`:

- development seeds 1000 through 1004 only;
- no validation or held-out seeds;
- one call per seed;
- GPT-5.6 Luna, medium reasoning, temperature omitted;
- condition `hmac-v1`;
- prompt `raw-rca-v2`, taxonomy `rca-taxonomy-v2`, and scorer
  `raw-rca-scorer-v2`.

The future result path is
`results/hmac_v1_development_gpt_5_6_luna_medium.jsonl`. Omitting `--execute`
performs a dry run and makes no provider calls.
