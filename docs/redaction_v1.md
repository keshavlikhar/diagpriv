# Naive Redaction v1

## Status and purpose

`redaction-v1` is the first privacy baseline for comparison with the frozen
`raw-rca-v2` condition. It tests the diagnostic effect of removing annotated
sensitive plaintext without attempting to retain diagnostic relationships.

This condition is not tokenization, pseudonymization, HMAC, format-preserving
transformation, or DiagPriv logic. It makes no privacy-security claim.

## Exact transformation rules

The transformation starts from `Incident.model_view()` and consults the
incident's oracle-only `sensitive_fields` annotations. It changes every
occurrence of every annotated `source.field` path and no other field.

Each sensitive value is replaced by a fixed, many-to-one placeholder determined
only by its JSON type and source-qualified field path:

| Input JSON type | Replacement |
|---|---|
| string | `[REDACTED:<source>.<field>]` |
| integer | `0` |
| floating point | `0.0` |
| boolean | `false` |
| null | `null` |
| array | `[]` |
| object | `{}` |

The placeholder is not derived from the plaintext. All string values at one
annotated path collapse to the same placeholder. Source qualification means,
for example, that `payments.request_id` and `logs.request_id` receive different
placeholders even when their original values were equal. The method therefore
does not intentionally preserve equality, inequality, or cross-source identity.

No privacy annotation, oracle label, invariant definition, or expected-evidence
definition is added to the transformed `ModelView`.

## Incident 001 example

Before:

```json
{
  "payments": {
    "evidence_id": "SYN-EVD-27391743",
    "payment_id": "SYN-PAY-95401729",
    "customer_id": "SYN-CUST-92252632",
    "account_id": "SYN-ACCT-35171490",
    "request_id": "SYN-REQ-23555431",
    "amount": "79.44",
    "status": "succeeded"
  },
  "log_attributes": {
    "request_id": "SYN-REQ-23555431",
    "payment_id": "SYN-PAY-95401729"
  }
}
```

After:

```json
{
  "payments": {
    "evidence_id": "SYN-EVD-27391743",
    "payment_id": "[REDACTED:payments.payment_id]",
    "customer_id": "[REDACTED:payments.customer_id]",
    "account_id": "[REDACTED:payments.account_id]",
    "request_id": "[REDACTED:payments.request_id]",
    "amount": "79.44",
    "status": "succeeded"
  },
  "log_attributes": {
    "request_id": "[REDACTED:logs.request_id]",
    "payment_id": "[REDACTED:logs.payment_id]"
  }
}
```

The example leaves the non-sensitive evidence ID, amount, and status unchanged.

## Incident 001 invariant profile

| Invariant | Necessity | Result |
|---|---|---|
| `target_request_equality` | essential | `degenerate_all_to_one` |
| `target_request_cross_source_identity` | essential | broken |
| `unrelated_request_inequality` | essential | broken |
| `target_payment_distinctness` | essential | broken |
| `target_event_order` | essential | `genuine_preservation` |
| `target_success_state` | essential | `genuine_preservation` |
| `target_customer_equality` | supportive | `degenerate_all_to_one` |
| `target_account_equality` | supportive | `degenerate_all_to_one` |
| `target_amount_equality` | supportive | `genuine_preservation` |
| `payment_row_cardinality` | supportive | `genuine_preservation` |
| `exact_rearrival_interval` | discardable | `genuine_preservation` |
| `literal_customer_identity` | discardable | `expected_non_preservation` |
| `literal_account_identity` | discardable | `expected_non_preservation` |

The same profile is verified for development seeds 1000 through 1004.

The original boolean predicate result remains available as `preserved`. The
additional `status` field distinguishes genuine preservation, a false predicate
(`broken`), equality made uninformative by all-to-one collapse
(`degenerate_all_to_one`), and the intended removal of discardable literal
identity (`expected_non_preservation`).
