# ADR-002 — Destination-Aware Policy Enforcement and Task-Aware Minimization

**Date:** 2026-11-01  
**Status:** PROPOSED for coauthor, lead-author and security review. No implementation, deployment, provider calls, or geolocation assurance.  
**Context:** DiagPriv's long-term goal is to help organizations use external and private AI tools without surrendering control over sensitive enterprise information or permitted geographic processing. The initial developer MVP remains narrow and local-first.

## Decision in plain language

There are **two independent checks**, in this order:

1. **Can information be sent to this AI destination at all?** Check organization policy, data classification, identity/purpose, provider and deployment, processing/storage/retention geography, approved transfer routes, and available trustworthy configuration evidence.
2. **If a transfer is allowed, what is the least evidence that still supports this approved diagnostic task?** Choose a reviewed transformation preserving necessary relationships, check the output and all disclosure surfaces, then enforce release through the permitted channel.

A transformation must never change a forbidden destination into an allowed one just because names, emails, or IDs disappeared. Any downgrade/reclassification of data after transformation is an **explicit reviewed policy decision**, not an automatic inference by the minimization planner.

**Priority:** security and routing policy constraints are hard rules; RCA utility is optimized only within those rules. If the destination is unapproved, unknown, or contradicted, the result is **blocked** even if task-aware minimization could produce useful evidence.

## Proposed layered architecture

    Developer or agent request (identity, task, approved tool)
        |
        v
    Controlled local tool-output and evidence boundary
        |
        v
    Trusted field inventory + classification + source access check
        |
        v
    Destination / purpose / residency Policy Decision Point (PDP)
        | deny/unknown => BLOCK, no outbound payload
        v
    Approved task contract + local minimum-exposure planner
        | no compliant profile => BLOCK
        v
    Deterministic transform, property checks, whole-payload release scan
        | check fails => BLOCK
        v
    Destination-bound release ticket (policy+route+payload fingerprint metadata)
        |
        v
    Policy Enforcement Point (PEP) bound to approved route and exact payload
        | mismatch, route drift, unsupported channel => BLOCK
        v
    Approved provider/deployment or local/private model

The route and provider capability registry is administered by trusted operators. A question, log line, environment variable set by an untrusted agent, model response, or arbitrary file metadata cannot declare a destination approved, override residency restrictions or declassify data. Identity/authorization and purpose are checked separately from transformation.

This is a **target architecture**, not today's Python research implementation. The first MVP does not contain a full network interception point, enterprise identity integration, or proof of provider-side data location.

## Three operating policy modes

**Mode 1 — Local-only.** The organization forbids external processing; all external destinations are denied. DiagPriv can prepare evidence for an independently approved local/private model only when that workflow has a controlled path and passed all local policy checks. No external fallback.

**Mode 2 — Approved external destination.** Organization policy may permit a specific provider, model deployment, contractual region(s), retention/administrative access posture and data classes. The minimizer transforms the evidence to a permitted view and the PEP sends only that view to the approved destination. The destination must not be inferred solely from URL, DNS, cloud source region, IP geolocation, or vendor branding.

**Mode 3 — No trustworthy destination facts / route unknown.** Deny external release, issue safe explanation and return a local review/refusal state. Sanitization does not confer residency compliance.

Some policies may permit transformed records outside a region but prohibit underlying customer records. Treat any such exception as a separately approved data classification and release rule. Do not assume replacement of direct identifiers makes sensitive metadata or commercial content non-sensitive.

## What a policy must eventually express

The policy is versioned and approved independently of the incident and any LLM:

- **Source/asset:** data owner, source class, record/field classification (public, internal, confidential, restricted, secret, unknown), protected combinations, query/row authorization.
- **Actor and purpose:** authenticated developer/team/service role, case/task class, access rights, approved model/tool functionality.
- **Destination:** provider, product/deployment/model endpoint identity, account/tenant, region or allowed geography, process and storage locations, subprocessors/retention where applicable, egress channel, approval evidence/version and expiration.
- **Disclosures:** prohibited raw or transformed fields, supported join scopes, time/shape/granularity budgets, allowed purpose and retention; no automated declassification.
- **Decision precedence:** explicit deny wins, missing or expired provider evidence fails closed, deviations and fallbacks require fresh authorization, and cloud/model retries must remain inside approved route constraints.
- **Audit:** only safe policy/decision identifiers, algorithm versions, route identity, refusal code and encrypted/protected operational traces as approved. Never plaintext sensitive values, secret-derived fingerprints, mapping tables or oracle labels in general audit logs.

The initial product may use a reviewed local YAML policy and a static synthetic destination registry for **offline decision testing** only. Such tests prove policy logic over simulated descriptors, not the actual physical location of cloud processing.

## Residency evidence and what we cannot promise

A request addressed to an endpoint in one country can be processed by an inference profile in additional regions. For example, AWS Bedrock differentiates geographic and global cross-Region inference, and some geographic profiles still route among multiple regions within that geography. Provider routing changes, hidden subprocessors, support access and retention policy can matter.

We must distinguish:

1. **Configured route compliance:** Does a request use the exact approved provider/deployment/region profile and organization network policy?
2. **Provider-assured geographic processing:** Is there currently sufficient provider documentation/contractual or operational assurance for where inference is processed and stored, and who accesses it?
3. **Independent proof of actual processing location:** Not available from endpoint selection or DiagPriv's transformation code. Cannot honestly claim this without additional trustworthy evidence.

A deployment cannot claim region compliance merely because its IP geolocates within the allowed country. Providers may introduce failover and routing; destination controls should validate an approved region set and deny unapproved retries. If required residence facts cannot be established at the selected assurance level, block.

External standards context, to verify periodically:
- AWS geographic cross-Region inference: https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- AWS cross-Region distinction: https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
- MCP core/version guidance: https://modelcontextprotocol.io/specification/2026-07-28/basic
- MCP authorization security considerations: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/security-considerations.mdx

## Trust-boundary limitation and bypasses

A sanitizer protects **only inputs and egress channels it actually intercepts**. Agents may bypass an MCP result by reading a file, running a shell command, calling another tool, retrieving an unprotected resource, or pasting source data into a chat. A generic CLI cannot prevent these paths. Product architecture must make coverage explicit and eventually use trusted network/tool controls to enforce approved paths; blocking all alternative channels requires broader infrastructure and organizational policy.

Never claim customer-wide AI DLP, data residency enforcement, end-to-end protection or absence of bypass for MVP v0.

## Paper 2 boundary: what we actually research

Paper 2 focuses on **task-aware minimization under externally specified disclosure and destination policies**, not on proving cloud residency or regulating global AI infrastructure. The destination/policy gate is independently supplied and verified in deterministic synthetic cases; the planner cannot weaken or rewrite it.

Potential study arms:
- A fully allowed destination with two different diagnostic tasks and multiple admissible transformation profiles.
- A denied external destination with otherwise informative synthetic data: all release decisions must block.
- An approved destination whose disclosure ceiling forbids required linkability or time relationships: the task is infeasible, not silently truncated.
- Unknown or expired route-assurance metadata: no outbound release.
- Approved destination with a valid policy but hidden-oracle mutation: planner decision must be invariant to hidden answer.
- Matched fixed baseline with identical legal/policy destination restrictions, to prevent unfair comparisons.

Measure separately (a) authorization and route-policy correctness in synthetic logic, (b) structural/certified disclosure, (c) RCA utility in separately authorized provider experiments, and (d) refusal and coverage. Do not conflate policy-simulator success with verified physical processing location, model-side retention, legal compliance or anonymity.

A possible research question refinement:
> Under independently specified destination and disclosure constraints, can a deterministic task-aware planner select a locally verifiable diagnostic representation that preserves declared task relations, reduces residual exposure relative to strong fixed baselines and refuses unsupported transfers?

The **novelty** must be attributed only to well-defined, empirically supported contributions; policy engines, data minimization, routing restrictions, pseudonymization and geography-bound inference are not new by themselves.

## MVP v0: deliberately narrow and honest

- Offline, local Python SDK + CLI operating on **one reviewed structured synthetic evidence bundle** at a time.
- An approved local policy describes classification, allowed task contract, allowed transformation profiles and optional illustrative destination/region metadata.
- **Before any transformation**, run a deterministic policy gate: explicit forbid/unknown route -> deny any proposed external export. No automatic downgrading of information classes.
- Run the supported diagnostic-contract minimizer and verifier only when task/policy compatible.
- Generate a safe local decision receipt plus a sanitized artifact for **manual review**; do NOT label the artifact "safe for any AI" or assert that downstream copies remain controlled.
- In v0 there is **no direct network send**, no provider call, and no claimed ability to force user/agent egress through the CLI. The policy gate is independently tested on synthetic, configured destination descriptors only.
- Separate future milestone: one trusted MCP read-only path with adapter-owned output and route-bound enforcement; later expand to enterprise proxy/policy enforcement for all supported channels. The 2026-07-28 MCP design treats transport as stateless; transport or process identity must not be used as investigation or approval continuity.

The first product win is verifiable, policy-bound evidence preparation for developers; it is not a universal enterprise DLP or worldwide data-residency gateway.

## Invariants / negative tests to freeze before implementation

1. Destination forbidden => no external release, even if all content is pseudonymized.
2. Unknown provider, inferred/expired region, unmatched model profile, forbidden retention terms => deny.
3. Local-only mode never triggers fallback to external models.
4. Strong "need more context" model instruction cannot override a disclosure limit.
5. Data-class change after sanitization requires explicit reviewed rule, not string matching.
6. A task requiring prohibited equality, counts, time or shape fails as infeasible.
7. Valid task + approved destination selects only allowed profile; output verified including question, logs, metadata, error channels and envelope.
8. Route changes between authorization and send require reauthorization; planned route-bound ticket becomes invalid upon mismatch.
9. Two independently authorized investigations do not accidentally reuse persistent tokens.
10. If a tool or shell path bypasses the controlled adapter, report *coverage gap*, do not represent the system as fully enforcing egress.
11. All negative test outcomes include denominators and safe reason codes; no raw or partially sanitized payloads in errors or logs.
12. The existing Paper 1 frozen files, provider transcripts and held-out boundaries remain untouched.

## Staged long-term roadmap

**Stage 0 — Product hypothesis + offline sandbox:** local synthetic structured evidence, independent policy gate, task-aware transformation, structural verification, manual output review. No actual residency assurance.

**Stage 1 — Narrow enforced integration:** a single controlled read-only MCP tool-result flow, authenticated caller, explicit approved route, bound egress checks, fail-closed refusals, end-to-end tests of supported result surfaces.

**Stage 2 — Enterprise controls:** independent tenant policy, admin approvals, provider/model-region registry verified against docs/contracts, identity integration, network/endpoint egress restrictions, response handling, protected audit and investigation sessions, clear bypass coverage.

**Stage 3 — Broader tool ecosystem:** more connectors, coding-agent inputs/files, policy-as-code, multiple sanctioned models including private deployments, customer security review and independent penetration assessment. Expand only with evaluated coverage.

## Product success criteria separate from paper metrics

- Engineers can diagnose supported incidents with less unneeded disclosure *without circumventing the guardrail*.
- Security/IT can specify permitted providers, regions and classes without the research planner making security decisions on its own.
- The extra protection reduces adoption friction compared with current enterprise controls, with fewer blocked but otherwise legal troubleshooting sessions than blanket deny/redact.
- The product's enforcement scope is clear enough for a security reviewer to verify, and its failure states do not leak sensitive payloads.

## Authors' review gates

- Project lead: approve the two-gate mission, user story, first MVP and intended scope.
- Research coauthors: check new Paper 2 hypotheses and strong baseline fairness; confirm independent policy and oracle separation.
- Security and infrastructure reviewer: approve the trusted policy provenance, route identity, no-downgrade behavior, bypass boundary, and provider-attestation requirements.
- Commercial/product review: confirm real customer pain around data transfer and AI usefulness through interviews; don't assume every company permits transformed exports.
- No provider experiments, held-out access, implementation merge or real-data pilots without their respective separate approvals.

**Status reminder:** This ADR is a *design and governance proposal*, not deployed enforcement, independently verified data residency, or research evidence.