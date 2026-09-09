# Deterministic tokenization baseline v1

`tokenization-v1` is an offline, annotation-driven baseline that replaces each
sensitive scalar with a short synthetic ordinal token. It uses an ephemeral
plaintext-to-token mapping constructed independently for each incident. It is
not a persistent token vault, encryption, format-preserving transformation, or
task-aware DiagPriv selection.

## Exact transformation rules

1. Start from a defensive copy of `incident.model_view()`.
2. Read only the oracle-side `Incident.sensitive_fields` annotations. Reject
   duplicate paths, missing sources or fields, unsupported policies, composite
   sensitive values, and ambiguous token-prefix collisions rather than allowing
   sensitive plaintext through.
3. Leave every unannotated field byte-for-byte equivalent at the JSON value
   level.
4. Assign annotation namespaces as follows:
   - `consistent_pseudonym` uses
     `shared:<classification>:<field>`. All annotated sources in that namespace
     share one mapping.
   - `pseudonymize_independently` and `remove_or_pseudonymize` use
     `path:<source>.<field>`. Each source-qualified path has its own mapping.
5. Canonicalize each scalar as `JSON-type NUL compact-JSON-value`. Explicit type
   tags distinguish strings, integers, numbers, booleans, and null.
6. Collect the unique canonical values for every namespace before assigning any
   token. This is the protected, local-only mapping input.
7. Order those values by the bytewise tuple:

   ```text
   SHA-256("tokenization-v1" NUL namespace NUL canonical-value), canonical-value
   ```

   The canonical value is only a deterministic collision tie-breaker. SHA-256
   is used internally to eliminate encounter-order and lexical-rank dependence;
   neither the digest nor the plaintext is placed in the visible token.
8. Assign one-based, six-digit ordinals in that order. Shared namespaces use
   `TOK_<FIELD>_<ordinal>`. Path namespaces use
   `TOK_<FIELD>_<SOURCE>_<ordinal>` so independent paths cannot accidentally
   appear linked.
9. Substitute tokens in a second pass, create a `ModelView`, and discard the
   ephemeral mapping when the call returns. The mapping is never returned,
   logged, serialized, or attached to an experiment manifest.

The fixed field tags in v1 are:

| Field | Tag |
|---|---|
| `request_id` | `REQ` |
| `customer_id` | `CUST` |
| `account_id` | `ACCT` |
| `payment_id` | `PAY` |
| `transport_id` | `TRANS` |
| `name` | `NAME` |
| `ssn` | `SSN` |
| `email` | `EMAIL` |

Other field names use a deterministic uppercase alphanumeric schema-derived
tag. Token prefixes are checked for uniqueness across the incident's declared
namespaces. Token text therefore exposes a coarse field/source class but never
encodes original formatting or sensitive plaintext.

## Reproducibility boundary

Determinism is scoped to the complete transformation input, not to plaintext
values globally:

- Cross-source identity is preserved because every relevant annotated source
  in one complete `ModelView` is collected into the same shared namespace and
  transformed in one operation.
- Repeated transformation of the same complete `ModelView` under
  `tokenization-v1` produces the same tokens across processes. Assignment does
  not depend on Python hash randomization, dictionary or row insertion order,
  UUID generation, or process state.
- Reordering evidence rows, log entries, or sensitive-field annotations does
  not change which token belongs to a value within that complete input.
- The mapping is incident-local and is not a persistent production token vault.
  Tokens are not claimed to remain stable when the same plaintext is later
  transformed independently with a different candidate-value population.
  Adding or removing a distinct value can change ordinal assignments for all
  values in that namespace.
- Deterministic equality, frequency, and within-namespace linkability remain
  visible. An observer with a sufficiently complete candidate set and knowledge
  of the public ordering algorithm may reconstruct assignments.

This input-scoped stability and candidate-set reconstruction risk are explicit
limitations of the experimental baseline.

## Comparison with existing baselines

| Property | `redaction-v1` | `hmac-v1` | `tokenization-v1` |
|---|---|---|---|
| Sensitive output | all-to-one placeholder | full HMAC digest token | short ordinal token |
| Equality preservation | not intentional | deterministic | deterministic |
| Intended cross-source identity | broken by path placeholders | shared keyed namespace | shared ephemeral map |
| Inequality preservation | no | negligible HMAC collision risk | exact within namespace |
| External secret | none | required 32-byte key | none |
| Persistent/reversible vault | none | none | none |
| Original format preserved | no | no | no |

Tokenization retains deterministic equality, frequency, and linkability inside
each declared namespace. An observer with a sufficiently complete candidate set
and knowledge of this public algorithm may be able to reconstruct assignments;
there is no cryptographic confidentiality claim. Compromise of an in-memory
mapping during transformation would also reveal the association. These risks,
and the absence of task-specific minimization, make this a comparison baseline
rather than the final DiagPriv method.

## Incident 001 example

Seed 1001, selected target payment row:

Before:

```json
{
  "evidence_id": "SYN-EVD-27391743",
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
  "evidence_id": "SYN-EVD-27391743",
  "payment_id": "TOK_PAY_PAYMENTS_000008",
  "customer_id": "TOK_CUST_000003",
  "account_id": "TOK_ACCT_000002",
  "request_id": "TOK_REQ_000005",
  "amount": "79.44",
  "status": "succeeded"
}
```

The matching log request identifier is also `TOK_REQ_000005`. Its payment
identifier uses the independent `logs.payment_id` namespace and therefore has a
`TOK_PAY_LOGS_...` token rather than the payment-row token. Evidence IDs,
amounts, states, timestamps, service names, messages, ordering, and cardinality
are unchanged because they are not annotated as sensitive.

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

There are no broken or degenerate all-to-one invariant results. The final two
statuses mean that the declared expectation of discarding literal identity was
met; they do not mean the literal values were retained.

## Prepared development comparison

`experiments/tokenization_v1_development.toml` permits exactly development
seeds 1000 through 1004, one call each, and no validation or held-out seeds. It
retains GPT-5.6 Luna with medium reasoning and omitted temperature, together
with `raw-rca-v2`, `rca-taxonomy-v2`, and `raw-rca-scorer-v2`.

No provider calls were made while implementing this baseline. A future approved
execution would use:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/tokenization_v1_development.toml \
  --results results/tokenization_v1_development_gpt_5_6_luna_medium.jsonl \
  --execute
```
