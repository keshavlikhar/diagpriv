# DiagPriv Policy Engine — Offline Decision Test Matrix v0.1

Status: proposed expected results only. Not executed, not implemented, not a security certification. Date: 2026-11-01. Parent: ADR_003_POLICY_DECISION_ENGINE.md.

## Synthetic fixture defaults
- Authenticated role incident-responder with source-access grant to a fictional payment incident and incident-diagnosis purpose.
- Resource classification confidential; raw customer email and credentials forbidden. Within-bundle request join and effect distinctness are required for correlate-events-v1.
- Destination demo-regional-approved: synthetic reviewed provider-deployment record, possible processing regions US-East-1/US-East-2, storage region US-East-1, valid evidence and an explicit transformed-field release rule. This is NOT an assurance regarding any real provider.
- Destination demo-global-unapproved: forbidden by policy. Destination demo-company-managed-local: approved fictional local inference route.
- All output is local preview only. No network send, real provider connection or production information.

## Test matrix
| ID | Change from default | Expected policy stage | Final result | Why |
|---|---|---|---|---|
| 01 | Approved principal, role, source, purpose, route, transformation, release | ELIGIBLE | PREPARED_LOCAL_PREVIEW | Positive control, no network |
| 02 | Select forbidden external deployment | DENIED | BLOCKED_BY_POLICY | Masking never repairs forbidden route |
| 03 | Local-only company requests external destination | DENIED | BLOCKED_BY_POLICY | No external fallback |
| 04 | Local-only company chooses approved private deployment | ELIGIBLE | PREPARED_LOCAL_PREVIEW if all other checks pass | Local does not exempt minimization |
| 05 | Destination name not in trusted registry | NEEDS_REVIEW | BLOCKED_BY_POLICY | No endpoint/name guessing |
| 06 | Processing region set missing | NEEDS_REVIEW | BLOCKED_BY_POLICY | Residency fact unknown |
| 07 | Route-assurance evidence expired | NEEDS_REVIEW | BLOCKED_BY_POLICY | Expiry is enforced |
| 08 | At least one possible processing region prohibited | DENIED | BLOCKED_BY_POLICY | Evaluate full possible region set |
| 09 | Storage or retention terms unknown and required | NEEDS_REVIEW | BLOCKED_BY_POLICY | Region is not the whole story |
| 10 | Principal lacks resource access | DENIED | BLOCKED_BY_POLICY | Access checked on original resource |
| 11 | Purpose changes to marketing (not approved) | DENIED | BLOCKED_BY_POLICY | Purpose is explicit |
| 12 | Allow and explicit deny both apply | DENIED | BLOCKED_BY_POLICY | Deny overrides allow |
| 13 | Allowed route, required request join forbidden by budget | ELIGIBLE | BLOCKED_INFEASIBLE | Never drop required invariant quietly |
| 14 | Allowed route, unknown nested field present | ELIGIBLE | BLOCKED_BY_POLICY | Unknown information cannot leak |
| 15 | Raw secret copied into question or error envelope | ELIGIBLE | BLOCKED_VALIDATION | Whole release must be checked |
| 16 | Log message tries to override security policy | ELIGIBLE at route | BLOCKED_BY_POLICY unless tightly templated input is safely handled | Untrusted log cannot select rules |
| 17 | Approved route profile changes after decision | ELIGIBLE before drift | BLOCKED_BY_POLICY on recheck | Future route-bound enforcement |
| 18 | Transformed output has no explicit release-class permission | ELIGIBLE | BLOCKED_BY_POLICY | No implicit declassification |
| 19 | Same evidence with allowed vs forbidden destination | ELIGIBLE vs DENIED | PREPARED_LOCAL_PREVIEW vs BLOCKED_BY_POLICY | Planner cannot override deny |
| 20 | Task changes to shape preservation forbidden by policy | ELIGIBLE | BLOCKED_INFEASIBLE | Task-budget conflict |
| 21 | Unknown policy version or unknown policy key | NEEDS_REVIEW | BLOCKED_BY_POLICY | Strict policy parser |
| 22 | Request claims elevated role while trusted identity lacks role | DENIED | BLOCKED_BY_POLICY | Caller cannot self-authorize |
| 23 | Pseudonym collision makes different IDs equal | ELIGIBLE | BLOCKED_VALIDATION | Equality and inequality must hold |
| 24 | Raw ID remains in evidence_id or metadata | ELIGIBLE | BLOCKED_VALIDATION | Whole payload, not only IDs |
| 25 | Local-only policy and model requests unapproved retry destination | DENIED | BLOCKED_BY_POLICY | No automatic external retry |
| 26 | Source owner explicitly prohibits all external sharing | DENIED | BLOCKED_BY_POLICY | Classification limits hard |
| 27 | Destination approval revoked after prior decision | DENIED or NEEDS_REVIEW | BLOCKED_BY_POLICY on recheck | Revalidate before send |
| 28 | Processing location documented but storage geography unknown | NEEDS_REVIEW | BLOCKED_BY_POLICY | Provider assurances distinguish processing and storage |

## Acceptance assertions
1. Each fixture uses trusted authenticated identity, data source classification, route registry, policy provenance and task contract distinct from untrusted question/log content.
2. The decision order is authorization and destination eligibility, local task planner, whole-output verification, and final release policy. Any deny blocks all external transfer.
3. Every non-ready case asserts no output bundle, raw/partial stdout, stderr, unsafe audit or failure-file artifacts. Redacted errors contain only approved safe reason codes.
4. PREPARED_LOCAL_PREVIEW asserts no provider/network call, no external routing claim, preservation of certified task relations, explicit transformed release-class permission and local-only artifact.
5. A request's URL, model ID, log, filename, DNS name or untrusted role may not determine route approval, data declassification or bypass policy.
6. Test full possible processing and storage region sets, policy expiry, destination change, retry, and provider-profile identity separately. A synthetic match is not proof of physical residency.
7. Test typed equality/inequality, false join collapse, source-specific join permissions, null/missing values, canonicalization, Unicode, nested fields, question and evidence IDs.
8. Add fuzz tests and count false refusals, not just successful blocks. A tool that always blocks every request is not an adequate product.
9. Negative tests use synthetic canaries, never provider keys, employer logs, or customer identity.
10. No provider calls, no protected held-out cases, and no changes to Paper 1 experiments are authorized by this specification.

## Freeze gate
Before implementation, authors must independently approve trust provenance, policy input schema and output statuses, the exact allowed transformed-data exception semantics, and all expected refusal outcomes. After that, a bounded offline unit implementation may be separately authorized.