# DiagPriv Developer MVP — Technical RFC v0.1

Status: review draft, not implemented, tested or certified. October 22, 2026.

## Customer and problem
First customer: data engineers and SREs who use external AI tools to diagnose incidents from logs, traces and SQL results. The narrow job is to transform a supported structured incident bundle into evidence that preserves permitted diagnostic relationships but does not expose prohibited values. Local execution in a customer-controlled environment; no DiagPriv-hosted sensitive-data processing.

## Scope and explicit non-goals
MVP v0: Python SDK and CLI; strict JSON/JSONL parser for one registered schema; independently approved field inventory and policy; one contract, correlate-events-v1; a small reviewed registry of bundle-scoped identifier transformations; property verification, release validation and payload-free refusal. Include structured SQL exports and templated log events only if they conform to the registered schema.
Not MVP v0: arbitrary unstructured logs, production database connectors, autonomous LLM task selection, browser interception, arbitrary MCP traffic, a cloud dashboard, production anonymity certification, or automatic compliance claims. MCP adapter and temporal diagnosis are next milestones, after release gates pass.

## Trust boundary and executable behavior
Input: local EvidenceBundle containing a troubleshooting question, registered source records, event identifiers and metadata; explicit reviewed PolicyBundle and task_contract_id. The policy must independently classify every field, nested item, source and question string. Unknown field, ambiguous classification, unsupported Unicode/binary/encoding, malformed event, missing time or type, or any unhandled free-text surface => refuse.
Planner receives only ModelView-like evidence and independently authored policy metadata, never oracle-bearing Incident or ground-truth annotations. Question text and logs are untrusted data, not instructions.
Output status values: ready, needs_policy_review, infeasible. Only ready contains a released bundle. Denials contain no partial raw data, secret-derived hashes, mapping tables, or sensitive error strings. No network/provider call in the engine. No raw fallback.

## First supported diagnostic contract
correlate-events-v1: preserve typed equality and inequality of the request ID within an explicitly authorized join domain across registered sources; preserve distinct effect identifiers and allowed event status/presence/cardinality when these are permitted by policy. Preserve all occurrences in approved scope, not a single known failing record. Release is infeasible when required counts or joins exceed budget.
A later lifecycle-order-v1 contract may support timestamp order and interval overlap, but only after independent temporal parsing and composition tests. Exact relative time retains time gaps and does not meet a no-duration disclosure policy.

## Policy and transformation rules
Policy versions, field inventory and exact join domains must be explicit; do not silently wildcard future schema. Secrets and unclassified values are never transformed into stable provider-visible tokens; block their release. Use separately versioned, bundle-scoped keyed pseudonymization (or reviewed local vault) and type/domain separation. Test unwanted cross-bundle correlation and known-value dictionary attacks. Existing research hmac-v1 and tokenization-v1 cannot be advertised as production-protective out of the box.
Composition certificates must check linkage + time + shape interactions. Approved profile selection uses a predeclared lexicographic order over a multi-axis disclosure vector after filtering hard policy constraints; unknown exposure bounds cannot satisfy a strict ceiling.

## Implementation architecture
New, separate product repository proposed: diagpriv-developer.
Packages: input/schema, policy/compiler, task/contracts, planner/registry, planner/select, transforms/scoped_identity, verify/properties, verify/release, api, cli. Synthetic tests grouped under schema, invariant, leakage, refusal, CLI, and adversarial suites.
API concept: protect(bundle, approved_policy, task_contract_id) returns only ready/review/infeasible. CLI concept: diagpriv protect evidence.jsonl --policy policy.yaml --task correlate-events-v1 --out safe.json.

## Phased engineering plan
M0: approve threat model, data schema, permitted fields, question rewriting, and refusal cases; no code.
M1: implement policy parser/validator and fail-closed input classification using synthetic examples; default all outputs to denied.
M2: new scoped ID pseudonymizer, structural equality/inequality tests, source joins, collision handling, and safe audit.
M3: certify full transformed payload and release envelopes; test secret canaries, unexpected text, injection, error paths, metadata, cross-session identity and partial failures.
M4: temporal grammar and optional relative-time profile only when privacy budget allows exact gaps and independently verified time semantics.
M5: optional read-only MCP integration for one client, only after auditing text, structured responses, errors and all supported result channels and bypass routes.

## Adversarial acceptance gates
Every known forbidden-field or unknown-field test blocks with no payload. Every declared property passes on the synthetic property suite, including equal and unequal witnesses; cross-source approved joins remain, forbidden joins do not. No unapproved field or secret-like canary in verified outputs, errors, debug files, or audit records under declared fixture coverage. Negative result and refusal counts must be published with denominators. Passing this suite is not a universal privacy guarantee.
Benchmark against an independently configured, policy-compliant fixed pseudonymization plus optional time baseline, not only naive redaction. Measure ability to finish the diagnostic task, policy-authoring effort, refusal and bypass frequency, multidimensional exposure, and p50/p95 local latency.

## Governance
Do not access employer systems, customer data, credentials or real logs without authorization and independent security/governance review. Review authorship, ownership, licenses and commercial rights before open-sourcing or commercialization. Product code must not import benchmark oracle-bearing Incident, and Paper 1 remains frozen.

## Review decisions to make with project lead and coauthors
1. Approve first customer workflow and registered event schema.
2. Independently authorize source/field classifications and disclosure ceilings.
3. Resolve keyed scope and audit retention.
4. Freeze permitted relation certificates, rejected conditions and initial candidate profiles.
5. Agree product/research repository separation and the gate for starting offline coding.

Definition of done for MVP v0: a locally usable CLI and Python SDK which either yields policy-verified transformed evidence for declared supported diagnostic relations, or refuses safely, with synthetic adversarial tests and transparent limitations. Not certified production security.