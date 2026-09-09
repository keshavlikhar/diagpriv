# Format-preserving pseudonymization baseline v1

`format-preserving-v1` is an offline, annotation-driven baseline that replaces
sensitive string values while retaining their mechanically observable shape. It
is constraint-preserving pseudonymization, not standardized format-preserving
encryption, anonymization, or the final DiagPriv method.

## Exact transformation algorithm

1. Make a defensive copy of `incident.model_view()`.
2. Read only oracle-side `Incident.sensitive_fields` annotations. Reject
   duplicate paths, malformed paths, unsupported policies, ambiguous namespace
   components, absent annotated sources or fields, ambiguous log locations,
   composite values, non-string scalars, and non-printable or non-ASCII strings.
   Failure occurs before a `ModelView` is returned.
3. Assign the same semantic namespaces used by the HMAC and tokenization
   baselines:
   - `consistent_pseudonym` uses
     `shared:<classification>:<field>`;
   - `pseudonymize_independently` uses `path:<source>.<field>`;
   - `remove_or_pseudonymize` uses the same path-local namespace because the
     current annotation does not explicitly request shared identity.
4. Parse every sensitive string into an exact structural pattern. Group unique
   plaintexts by `(namespace, pattern)` across the complete ModelView.
5. Before assignment, calculate each pattern's output-domain capacity. Across
   every namespace using that pattern, require enough outputs to be both unique
   and disjoint from every original sensitive plaintext with that pattern. If
   the domain is too small, fail closed.
6. Process groups in byte-stable `(namespace, serialized-pattern)` order. Within
   a group, process unique values by:

   ```text
   SHA-256(
     "format-preserving-v1" NUL "order" NUL namespace
     NUL serialized-pattern NUL plaintext
   ), plaintext
   ```

   The plaintext tie-breaker only resolves the cryptographically unlikely case
   of equal digests; it is never exposed.
7. For each plaintext, derive an initial candidate rank as:

   ```text
   integer(SHA-256(
     "format-preserving-v1" NUL "candidate" NUL namespace
     NUL serialized-pattern NUL plaintext
   )) modulo pattern-domain-size
   ```

   Decode that rank in mixed radix: 26 possibilities at each uppercase or
   lowercase position, 10 at each digit position, and one fixed value at each
   separator position.
8. If the candidate equals any original sensitive plaintext or an output
   already assigned to any namespace with the same pattern, probe ranks
   `(initial + 1) mod capacity`, `(initial + 2) mod capacity`, and so on until a
   free candidate is found. The preflight capacity check and complete cyclic
   enumeration guarantee assignment when the check passes. This is explicit
   collision resolution rather than a negligible-collision assumption.
9. Substitute values in a second pass. The resulting output is one-to-one
   within every namespace and pattern; outputs also remain distinct across
   independent namespaces. Create a `ModelView`, then discard all local
   plaintext-to-pseudonym mappings.

SHA-256 is used here only for deterministic ordering and candidate selection.
There is no secret key and no cryptographic confidentiality claim.

## Structural-pattern rules

The baseline supports printable ASCII strings. Every character is classified
independently:

| Input character | Pattern symbol | Output alphabet |
|---|---:|---|
| `A`–`Z` | `U` | `A`–`Z` |
| `a`–`z` | `l` | `a`–`z` |
| `0`–`9` | `D` | `0`–`9` |
| printable punctuation or space | literal character | that exact character |

For example, `AB-123-xy` has pattern `UU-DDD-ll`; a conforming pseudonym might
be `QF-804-mz`. Exact total length, punctuation, separator position, and the
uppercase/lowercase/digit class at every position are preserved. Original
letters and digits are not copied as fixed literals. Empty strings and strings
containing no variable alphabetic or digit position have a one-value domain and
therefore fail the plaintext-disjoint capacity check.

No benchmark-defined stronger constraint exists for Incident 001. Therefore v1
does not silently add check-digit logic, semantic prefix retention, UUID rules,
or field-specific validation. If a future benchmark declares a stronger
constraint, it must be implemented and versioned explicitly.

## Reproducibility boundary

The assignment is deterministic for the same complete ModelView and candidate
population. It does not depend on Python hash randomization, input traversal or
dictionary insertion order, random UUIDs, or process state. All relevant
sources are transformed together, so shared namespaces preserve intended
cross-source identity.

This is not a persistent token vault. A value is not claimed to receive the same
pseudonym when independently transformed with a different candidate population.
Adding or removing values may introduce a forbidden value or a collision and
therefore change probe outcomes. The ephemeral mapping is never included in a
ModelView, prompt, manifest, result JSONL, log, or repository-tracked artifact.

## Incident 001 example

The following seed-1001 values demonstrate the rules. The examples are
development fixtures, not provider observations.

| Field and namespace behavior | Before | After |
|---|---|---|
| request ID, shared across payments/logs | `SYN-REQ-23555431` | `QZW-YMW-26983924` |
| payment ID in `payments.payment_id` | `SYN-PAY-95401729` | `LTI-IWR-41055397` |
| same payment plaintext in independent `logs.payment_id` | `SYN-PAY-95401729` | `XVX-NKD-78646075` |
| customer ID, shared across sources | `SYN-CUST-92252632` | `PHU-MXBA-77833576` |
| account ID, shared across sources | `SYN-ACCT-35171490` | `WLC-XTDB-64565588` |
| customer name, path-local | `Rowan Placeholder (Fictional)` | `Clmvz Sbgwmfzjdrw (Xswhwpbhd)` |
| SSN, path-local | `000-88-3435` | `211-97-2919` |
| email, path-local | `rowan.placeholder.2@example.invalid` | `tvypn.nvyodwevkvz.4@sselsho.yymjcpp` |

The target request pseudonym is identical in the payment row and all matching
logs. The identical payment plaintext intentionally receives different outputs
in the independent payment-row and log namespaces. Evidence IDs, amounts,
statuses, timestamps, messages, services, ordering, and row counts are
unchanged because they are not annotated as sensitive.

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
statuses mean the declared expectation of removing literal identity was met.

Beyond these diagnostic invariants, the baseline preserves every sensitive
string's exact length, separator characters and positions, per-position case or
digit class, SSN-like shape, email-like punctuation layout, identifier segment
widths, and deterministic equality/frequency within its namespace.

## Comparison with earlier baselines

| Property | `redaction-v1` | `hmac-v1` | `tokenization-v1` | `format-preserving-v1` |
|---|---|---|---|---|
| Sensitive output | all-to-one placeholder | keyed digest token | short ordinal token | same-pattern pseudonym |
| Equality/inequality | generally destroyed | preserved | preserved | preserved |
| Intended cross-source identity | destroyed | shared keyed namespace | shared ephemeral map | shared ephemeral map |
| Exact one-to-one guarantee in candidate set | no | probabilistic collision bound | yes | yes, with probing |
| Original shape | no | no | no | length, classes, separators |
| External secret | none | required | none | none |
| Persistent/reversible vault | none | none | none | none |

## Privacy limitations and methodological scope

Format preservation deliberately leaks more than HMAC or generic tokenization:

- original length;
- exact separators and their positions;
- uppercase, lowercase, and digit positions;
- recognizable schemas such as SSN- or email-like layouts;
- deterministic equality, frequency, and within-namespace linkability;
- candidate-set information through the public deterministic algorithm; and
- potentially recognizable prefixes when their character-class structure is
  distinctive, even though literal prefix letters are not retained.

Candidate-set reconstruction may be possible. In-memory mapping compromise
would also reveal associations. This baseline makes no claim of anonymization,
zero re-identification risk, cryptographic security, or task-aware data
minimization.

Incident 001 does not test whether format preservation is necessary for RCA:
its diagnosis depends on equality, inequality, cross-source identity, event
order, success state, amounts, and cardinality—not sensitive-value shape. A
future incident family should make a malformed identifier, truncation,
leading-zero loss, separator corruption, fixed-width mismatch, check-digit
failure, or another declared structural constraint genuinely diagnostic. That
future family is intentionally outside this baseline task.

## Frozen development observation

`experiments/format_preserving_v1_development.toml` permits exactly seeds 1000
through 1004, one call per seed, with no validation or held-out seeds. It keeps
GPT-5.6 Luna, medium reasoning, omitted temperature, `raw-rca-v2`,
`rca-taxonomy-v2`, and `raw-rca-scorer-v2`.

The reviewed development execution produced five valid responses and 4/5 exact
RCA. Outcome, trigger, subsequent action, and failure mechanism were correct in
5/5 cases; affected component was correct in 4/5. Seed 1000 selected
`request_ingress` instead of the frozen `operation_executor` oracle. Evidence
precision was 1.0000, recall was approximately 0.742857, and F1 was
approximately 0.848018. Total usage was 23,918 tokens, with estimated cost
$0.00840885 under the configured pricing snapshot.

This is an immutable five-instance development observation, not a general
conclusion. It must not be rerun, and the transform, oracle, or protocol must not
be tuned to the component disagreement. No format-preserving validation or
held-out observation has been generated.

The result does not show whether preserving format improves utility beyond
ordinary relationship-preserving pseudonymization because Incident 001 does not
require format information for diagnosis. A future family must explicitly make
truncation, leading-zero loss, separator corruption, malformed identifier shape,
fixed-width mismatch, or a structural/check-digit violation causal evidence.

The oracle remains `operation_executor` because this RCA field identifies the
role that owns the missing idempotency control and produces the duplicate durable
effect. The ingress component observes the deadline and accepts the re-arrival,
but the executor persists both operations. Component ownership is plausibly
more model-sensitive than the other four dimensions and should later be tested
across models and repeated trials without revising this frozen observation.
