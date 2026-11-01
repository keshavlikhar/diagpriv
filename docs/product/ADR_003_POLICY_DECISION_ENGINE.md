# ADR-003 — Policy Decision Engine: Destination Eligibility Before Diagnostic Minimization

**Date:** 2026-11-01
**Status:** REVIEW DRAFT, not implemented or security certified.
**Related:** docs/product/ADR_002_DESTINATION_POLICY_AND_MINIMIZATION.md, docs/product/DEVELOPER_MVP_RFC_v0_1.md, docs/paper2/PROTOCOL_RFC_v0_1.md.
**Author decision:** DiagPriv's long-term mission combines information-flow/residency policy enforcement with task-aware minimization. MVP v0 is an offline local policy simulator and evidence-preparation tool; no production traffic interception or region attestation.

## 1. User story

A developer wants to use an AI tool on a failed pipeline and selects a provider/deployment. The organization controls which actor can access which source, for what purpose, with which destinations and disclosure bounds. A trusted local decision component determines whether the proposed *route and purpose* are eligible. Only then may the separate task-aware minimizer attempt a safe representation. A final policy check and a controlled egress enforcement point will be required before any future real network send.

A masked record still contains enterprise information. The minimizer may not downgrade sensitivity classes or whitelist an unapproved destination by itself. A policy exception for approved transformed output must be explicit and independently maintained.

## 2. Security decision inputs: do not trust request claims

The request can identify the proposed task and route, but cannot certify approval.

**Request (untrusted suggestion):** principal reference, data-source reference, purpose, diagnostic task ID, destination profile ID, source bundle handle, requested action.

**Trusted policy/registry metadata:** authenticated principal attributes and enterprise data-access grants; source owner and full classification inventory; organization policy ID and signed/versioned source; approved purposes; destination IDs tied to deployment/account/model and an *approved set of processing and storage regions*; retention/subprocessor/support-access conditions if policy requires them; provider documentation/contract evidence and expiry; explicitly permitted field disclosure and transformation profiles; audit retention rules.

Provider URLs, DNS, IP geolocation, caller-supplied model names or log contents do not authenticate processing geography. Regions are policy-defined sets, not arbitrary free-form strings. Stale or absent trustworthy destination assurance => no external eligibility. A declaration that evidence was sanitized never makes a forbidden route eligible.

Access is always checked against the original resource and authenticated actor, before transformation.

## 3. Two-phase authorization and one enforcement point

**Phase A: pre-plan gate, route eligibility**
1. Authenticate actor / determine organizational tenant and approved access rights.
2. Verify policy provenance/version/expiry and original-data classification.
3. Verify intended purpose and requested action.
4. Resolve destination by *trusted* deployment/route registry; check all approved candidate inference, storage and relevant secondary processing regions.
5. Check retention, logging, provider/subprocessor rules required by policy, and explicit deny overrides.
6. On deny or ambiguity, do not execute a release workflow. Return payload-free reason code.

**Phase B: planner and post-transform release decision**
7. Obtain a reviewed task contract and the immutable disclosure budget for this policy/destination.
8. Locally select a certified transformation or return infeasible/review; no raw fallback.
9. Verify relation preservation plus the *whole* model-visible payload, including the question, source names, evidence IDs, logs, metadata, exception fields and envelope.
10. Evaluate transformed-field release permissions that are *explicit* in company policy. No automatic declassification based on missing email/SSN literals.
11. For future connected deployments, bind final authorization to the exact verified payload, policy version, authenticated principal, action, destination/deployment identity and configured route; enforce at a non-bypassable controlled egress boundary. Require new authorization on route/payload/policy change.

In MVP v0, steps 1–10 are only **deterministic offline simulation over synthetic/trusted test descriptors**, and step 11 is not implemented. Output is a local preview and decision receipt, *not* an enforceable grant to send data or a proof of residency.

## 4. State model and composition semantics

The destination-policy decision returns:
- ELIGIBLE: the trusted hypothetical policy descriptors explicitly approve the actor, data source, purpose and destination profile for consideration, subject to downstream disclosure checks;
- DENIED: one or more explicit prohibitions apply;
- NEEDS_REVIEW: trusted inputs, classification, or route-assurance evidence are missing, ambiguous, malformed or expired. This is also a refusal to release in MVP v0.

The minimizer result is independently READY, NEEDS_POLICY_REVIEW or INFEASIBLE.

The combined preview result can be:
- PREPARED_LOCAL_PREVIEW: route eligibility simulated as ELIGIBLE, minimizer READY, verified output and release classification pass. The output may be previewed locally but is *not* sent.
- BLOCKED_BY_POLICY: DENIED or NEEDS_REVIEW at either authorization stage; output contains no releasable payload.
- BLOCKED_INFEASIBLE: approved task requires disclosures exceeding the budget; no payload.
- BLOCKED_VALIDATION: a transformation or whole-output check fails; no payload.

Real deployment should eventually expose a distinct SENT_THROUGH_CONTROLLED_ROUTE status, only from a trusted policy enforcement point after transport confirmation. Never call locally prepared data "residency verified", "approved for any AI", "fully anonymous", or "safe for all providers".

Explicit deny > explicit permit > default deny; unknown is not permission. Route/purpose approval is necessary but **not sufficient** for release. A successful pseudonymizer is necessary for some policies but **not sufficient** for authorization.

## 5. Synthetic declarative policy examples

The following illustrative YAML is not runnable schema; all identities and destinations are fictional. Do not use it to declare real provider processing geography.

~~~yaml
policy_version: synthetic-policy-v0
policy_id: example-eng-001
resource: synthetic-payment-incident
class: confidential
actor_role: incident-responder
purpose: incident-diagnosis
default_external: deny
allowed_external_destinations:
  - id: demo-regional-approved
    deployment: hypothetical-us-profile-a
    processing_region_set: [us-east-1, us-east-2]
    storage_region_set: [us-east-1]
    evidence_source: reviewed-provider-terms-fixture
    evidence_expires: 2027-01-01
    permitted_release: policy-reviewed-transformed-diagnostic-fields
forbidden_destinations: [demo-global-unapproved]
allowed_local_deployments: [demo-company-managed-local]
disclosure_budget:
  direct_customer_identifiers: forbidden
  credentials: forbidden
  cross_investigation_token_linkability: forbidden
  request_join_within_bundle: permitted
  exact_absolute_timestamps: forbidden
  record_inventory: explicitly_permitted
~~~

A real policy would need distinct, versioned rules for encrypted data handling, provider retention, data storage and processing, support/subprocessor access, and authorized tasks. The sample's region sets are *synthetic expected metadata*, not provider attestations.

### Scenario A — Approved external route, transformed fields permitted

Input: trusted actor/role approved for resource and diagnosis purpose, destination ID demo-regional-approved, region-set/evidence valid, question asks about repeated request effects, budget permits within-bundle request joins but forbids customer literals. Expected result: route ELIGIBLE; minimizer may select a reviewed scoped transform; complete checks may yield PREPARED_LOCAL_PREVIEW. No network send or claim of actual region processing.

### Scenario B — Forbidden external route

Same data/question, requested destination demo-global-unapproved. Expected result: DENIED immediately and BLOCKED_BY_POLICY regardless of what masking might achieve. Do not try a permissive provider automatically.

### Scenario C — Local-only organization

Policy has no allowed external destinations, but has an approved local/private route. External request => DENIED. Approved local route => eligible to proceed only if task/field policy and local deployment access permit it. No automatic model call in v0.

### Scenario D — Unknown or expired region evidence

Requested approved-looking provider/deployment but the documented possible processing/storage region set is absent, conflicts with policy, or its trusted evidence is expired. Expected result: NEEDS_REVIEW and BLOCKED_BY_POLICY; do not infer US processing from endpoint URL.

### Scenario E — Authorized route, impossible diagnostic disclosure

Approved region, actor and task, but policy forbids the cross-source equality needed by correlate-events-v1. Expected result: ELIGIBLE route, INFEASIBLE minimizer, BLOCKED_INFEASIBLE. Do not silently delete diagnostic relations and claim the task is supported.

## 6. Why we do not build a custom all-purpose authorization language now

Policy rules are existing technology. Strong reference points:
- Cedar: explicit permit/forbid rules with implicit default deny and forbid-overrides semantics; authorization language and validation intended for fine-grained permissions. See https://docs.cedarpolicy.com/auth/authorization.html.
- Open Policy Agent (OPA): policy-decision engine separated from policy enforcement; Rego supports declarative policy across tools/services. See https://www.openpolicyagent.org/docs and https://www.openpolicyagent.org/docs/integration.

For **MVP v0**, implement only a small typed input policy contract and deterministic validation in an offline prototype. We can benchmark and adopt a mature embedded Cedar or OPA backend during enforcement integration after defining realistic deployment, operational and versioning needs. Do not market the offline rule evaluator as a novel policy framework or production-grade PDP.

## 7. Research and product validation

Paper 2 treats actor, destination and disclosure rules as independently provided constraints, not the novelty. Its inference planner must remain unaware of oracle labels and cannot alter upstream permissions. Synthetic study arms should include same evidence/task with varied policy, same policy/evidence with varied diagnostic questions, unknown destination metadata, forbidden equality/shape/time, and otherwise safe payload under a forbidden route. Report route-policy accuracy, correct refusal, relation preservation, exposure and separately authorized diagnostic performance.

MVP user research should separately ask: why does the engineer's organization block an AI tool (model location, data classification, contract, retention, lack of approved route, general policy)? A product is differentiated only if it solves a recurring deployment problem and improves diagnostic outcomes within approved policies relative to existing tools.

## 8. Attack and failure considerations

- Untrusted client may substitute policy IDs, actor claims, task descriptions or destination names; trusted registry and authenticated identity must prevail.
- Destination and policy facts can expire or change between decision and use; future enforcement must fail closed on stale policy/route or changed payload.
- Request can be injected into a log text or model prompt; log instructions never authorize data movement.
- Redacted/hashed data can still leak via context, group sizes, absolute/relative time, rare values and free-text; check whole release and retain residual exposure records.
- MCP tool responses may include text, structured content, resource links, errors and metadata; a controlled adapter covers only tested paths and must not imply protection of shell/files or other unmonitored traffic.
- A product cannot independently prove the actual data center that processed an external model request solely from a requested endpoint or configuration. Provider assurances/contracts and controls need separate review.
- No employer/customer data, credentials, provider calls or held-out research cases are permitted by this review draft.

## 9. Proposed acceptance test matrix

See docs/product/POLICY_ENGINE_OFFLINE_TEST_MATRIX_v0_1.md for the concrete synthetic decision table. Freeze the core tests before implementing the first offline policy engine.

## 10. Team review questions and recommendations

1. **Research scientist:** Does a policy-independent contract retain the information needed for plausible competing diagnoses? Recommend preserving all declared task-domain relationships, not only known failing path.
2. **Security architect:** Can the requester impersonate an approved route or cause unreviewed data-class downgrade? Recommend trusted registry, immutable constraints and explicit post-transform release rule.
3. **Platform engineer:** Can the authorization change between checking and transmitting? Require route-bound, payload-bound enforcement later; MVP v0 never transmits.
4. **Developer UX:** Will the developer understand a refusal? Emit a safe code (e.g. DESTINATION_UNAPPROVED or JOIN_FORBIDDEN), suggested authorized route category where policy permits, no raw metadata.
5. **Product:** Would customers accept a local preview if it does not itself stop alternate egress? Use it only as research/usability validation; controlled integrations are required for a saleable enforcement claim.
6. **Red team:** Can a malformed, unclassified or synthetic-to-real destination exploit optimistic fallback? Require deny by default and comprehensive negative fixtures.
7. **Governance:** Can coauthors and outside reviewers trace every policy requirement to an independently approved source? Maintain versioned approval, provenance and explicit owner.

**Next gate:** Lead author and coauthors review the policy schema, route-evidence requirements, consent/approval provenance, and default refusal semantics; independent security review before enforcement implementation. These are proposed decisions, not automatically final approvals.
