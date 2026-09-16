# Threat Model

## Scope

This threat model covers synthetic DiagBench evidence as it moves from a
complete oracle-bearing incident to a privacy-transformed ModelView and an
external LLM provider. It guides research comparisons; it is not a formal
anonymization, compliance, or production-security claim.

All current identities and events are fictional. The benchmark deliberately
models fields that would be sensitive in a real operational setting so that
transformation behavior can be measured without handling real personal data.

## Assets

- Direct identifiers such as names, synthetic SSNs, and email addresses.
- Customer, account, request, payment, and transport identifiers.
- Relationships among values across rows, logs, sources, and incidents.
- The HMAC experimental key and provider API credential.
- Oracle labels, expected evidence, invariants, and privacy annotations.
- Held-out instances and protocol decisions that protect experimental validity.
- Raw and transformed model responses, manifests, and cost/usage metadata.

## Adversaries and observers

The relevant observer may be:

- the external model provider receiving a prompt;
- a researcher or collaborator who can read prompts or result artifacts but not
  the external HMAC key;
- a curious party with auxiliary knowledge about likely identifiers;
- an accidental repository recipient; or
- code that mistakenly serializes oracle data or secrets across a trust boundary.

A fully compromised development host or secret manager, malicious benchmark
maintainer, provider-side compromise, and cryptanalytic break of HMAC-SHA-256 are
outside the current experimental guarantee. They remain operational risks.

## Trust boundaries

1. **Oracle boundary:** `Incident` contains ground truth and annotations;
   `ModelView` contains only troubleshooting evidence and the question.
2. **Transformation boundary:** privacy code may read annotations and an external
   key but must return only a ModelView.
3. **Provider boundary:** the provider receives the rendered prompt and model
   settings, never the Incident, annotations, oracle, expected evidence, API-key
   value, or HMAC key.
4. **Artifact boundary:** result JSONLs may contain model-visible evidence and
   responses, but no credentials or HMAC key material.
5. **Repository boundary:** tracked configuration may name environment variables
   and non-secret key IDs, but may not contain secret values.

## Transformation properties

### Raw

Raw evidence provides no transformation protection. Current data is synthetic,
but raw establishes the maximum-utility reference condition.

### `redaction-v1`

Redaction removes annotated plaintext using generic placeholders. It avoids
intentional linkability, but all-to-one collapse can create false equality and
destroy true inequality or cross-source identity. It is a naive comparison
condition, not proof of privacy.

### `hmac-v1`

HMAC uses an external 256-bit key, SHA-256, canonical typed input, and domain
separation. Without the key, the token does not reveal the original value by
direct reversal. Different values collide only with cryptographically negligible
probability under the construction.

HMAC intentionally leaks deterministic equality and frequency within a
namespace. `consistent_pseudonym` namespaces also expose selected cross-source
linkability. Path-specific namespaces reduce linkage across attributes but do
not hide repetition within a path. Token persistence can enable longitudinal
correlation if the same key is reused broadly.

HMAC does not hide:

- which fields are present or absent;
- row, log, and source cardinality;
- ordering, timestamps, status, amounts, service names, or messages when those
  fields are not annotated sensitive;
- equality/frequency in a deterministic namespace; or
- facts inferable from non-sensitive context.

If the key is exposed, low-entropy or enumerable identifier domains may be
tested offline. Key secrecy, namespace scope, rotation, and artifact access are
therefore part of the experimental exposure model.

### `relative-time-v1`

Relative time removes annotated calendar dates, wall-clock times, timezones,
epochs, RFC3339 strings, and original timestamp formatting. It intentionally
preserves exact incident-local millisecond offsets, equality, order, duration,
gaps, overlap, deadline crossing, and total span. Those relations are required
for the first Incident 003 matched diagnostic comparison.

Exact relative timing can still be distinctive and correlatable with outside
knowledge. If an observer independently knows the absolute time of one
transformed event, exact relative offsets can permit reconstruction of the
absolute times of other events in that transformed incident. Non-temporal
identifiers are deliberately unchanged in v1 so the experiment isolates
temporal representation. The condition does not claim
anonymity, unlinkability, zero re-identification risk, or optimal data
minimization.

## Required controls

- Use only synthetic data until a separate real-data governance review exists.
- Treat privacy annotations as oracle-only and test that every annotated value is
  transformed while every non-sensitive field remains unchanged.
- Fail closed on missing or unsupported annotated fields.
- Store `OPENAI_API_KEY` and `DIAGPRIV_HMAC_KEY_HEX` outside the repository.
- Never log, serialize, hash-as-an-identifier, or print secret values. A
  human-assigned non-secret key ID is allowed; a secret-derived fingerprint is
  not currently required.
- Use one reviewed experimental key per declared key ID and do not silently
  replace it.
- Keep `.env`, private-key, and results artifacts ignored by Git.
- Sanitize provider errors using an allowlist; never persist Authorization
  headers or arbitrary response headers.
- Scan tracked and staged content before collaboration or push.
- Keep oracle and ModelView serialization tests mandatory.

## Experimental-validity threats

Privacy and research integrity are separate. Current validity threats include:

- answer leakage through incident wording, labels, service names, or taxonomy;
- memorization of a small, single-family generator;
- tuning transformations or prompts on validation/held-out observations;
- treating infrastructure failures as RCA failures;
- post hoc retries or exclusion of incorrect responses;
- provider/model changes under an unchanged experiment label; and
- interpreting invariant preservation as model utility without an LLM result.

The retired 10000–10999 range cannot be used because it was mechanically
audited before evaluation. Held-out seeds 20000–20999 must remain unseen until
the complete final protocol is frozen.

## Non-goals and residual risk

The current work does not claim differential privacy, k-anonymity,
unlinkability, resistance to arbitrary auxiliary information, protection from a
compromised key, secret detection in unannotated fields, production-grade key
management, or regulatory compliance. A field-classification mistake can leave
sensitive context untouched; automated tests cover declared fields, not unknown
future fields.

Before any production-data study, the team would need data minimization,
retention/deletion policy, provider terms review, access controls, audit logging
that cannot leak payloads, formal incident response, and independent privacy and
security review.
