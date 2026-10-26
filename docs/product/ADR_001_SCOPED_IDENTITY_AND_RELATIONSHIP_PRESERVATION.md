# ADR-001 — Scoped Diagnostic Identity and Release-Safety Contract

**Status:** proposed for team and coauthor review; not security certified or implemented. **Date:** 2026-10-26. **Review target:** DiagPriv PR #57; related to Paper 2 Protocol RFC v0.1 and Developer MVP RFC v0.1.

## Scope and why this matters

Paper 1 tested annotation-driven transformations; current hmac-v1 derives tokens from a single key and a namespace that does not include an investigation, so it can produce identical tokens across incidents. Tokenization-v1 uses a deterministic local ordinal mapping whose output can reveal field type and population ordering/candidate information. Neither function should be silently repurposed as a production API; their inputs include oracle-bearing benchmark Incident and annotations. This ADR proposes NEW runtime components and tests, not a Paper 1 change.

Foundational problem: authorize relational *capabilities*, not merely mask isolated columns. Define what the investigator needs to join, how long that join must remain possible, to whom information is released, which other joins are forbidden, and what happens when a safe transformation is infeasible. This is not a cryptographic privacy/anonymity proof.

## Independent technical review: positions and dissent

- Research: a proof that equality is preserved does not prove its sufficiency for causal diagnosis; test independent task contracts against plausible alternatives, not case-oracle annotations. Reject novelty claims based only on HMAC or pseudonymization.
- Cryptography: choose standard HMAC-SHA-256 and HKDF (RFC 2104, RFC 5869), not custom reversible encoding. Domain-separate keys and typed inputs. Do not invent a security proof for the entire release.
- Security/privacy: investigation-scoped tokens mitigate direct cross-session token reuse, but contextual content, timing, cardinality, frequency, rare patterns, known plaintext and chosen-input access remain correlation/identification channels. Refuse unknown/free-text fields.
- Distributed systems: equality must survive legitimate joins across sources and, eventually, multiple batches within one authorized investigation; source path spelling alone is not a join definition. Scope lifetime must be explicit.
- Developer experience: start with one atomic offline bundle and explicit schema/task contract. Multi-process resumability and token-vault administration make v0 much harder and are not justified without user evidence.
- Product: a manually configured strong pseudonymization baseline already offers many of these properties (including Google Cloud referential integrity/context tweaks). The product must show an advantage in task-contract governance, verification, developer effort, or safety before claiming differentiation.
- Red team: adversarially test collisions, null/missing semantics, free-text leaks, prompt and filename paths, candidate-set identity recovery, cross-session reconstruction, key misuse, and error artifacts.

## Decision summary (proposed, not final)

**MVP v0:** a single local atomic evidence-bundle processing operation. Generate a fresh 256-bit secret from a CSPRNG for each independently authorized processing scope; keep it in memory and discard it after release checks. Derive per-domain subkeys with a vetted HKDF implementation, using explicit purpose, schema/policy/version and join-domain encoding as context. Use HMAC-SHA-256 over unambiguous typed, length-framed canonical values, with a non-shape-preserving opaque result. Never log keys, canonical identifiers, input-output mappings, fingerprints of sensitive values, or rejected payloads. If a multi-file input must be correlated, it is ingested as one authorized bundle for v0.

**Next milestone:** named, operator-approved investigation sessions spanning multiple tool results, with explicit creation, expiration and authorized resumption. Implement secure session key storage and key lifecycle only after choosing a credible protected storage mechanism; default separation across sessions, not across individual records or unrelated source paths. A session ID must be random and trusted, not derived directly from customer identity, incident content, user-supplied filenames, or external model instructions.

**Why not use a global HMAC key?** It yields stable identifiers across unrelated investigations and tenants. **Why not use an ephemeral token vault first?** It requires protected retention of sensitive mappings, persistence and crash/recovery policy, which v0 does not need. **Why not unkeyed deterministic ordinal tokens?** Their assignment depends on candidate populations and public computation, creating extra inference opportunities. **Why not format-preserving substitutes first?** Shape disclosure requires a separate authorized task/property budget and creates reidentification opportunities.

Fresh per-run keying makes token BYTES intentionally different on repeated independent runs. The structural-preservation property and deterministic *planning*, given fixed metadata, remain testable. When using a fixed explicitly injected *synthetic test key*, exact pseudonym bytes may be regression tested offline, but no production key is embedded in fixtures.

## Formal requirements

Let a source field occurrence o have raw scalar v(o), reviewed source-path classification, entity type t(o), join domain d(o), and processing scope s. Let C_t(v) be the approved typed canonical encoding. For each allowed domain d, produce:

    K_(s,d) = HKDF-SHA256(session_key_s, info = framed("diagpriv/v2", policy_version, schema_version, d))
    P(o) = opaque(HMAC-SHA256(K_(s,d), framed(t(o), C_t(v(o)))))

This is explanatory notation, not a complete final cryptographic serialization specification. A production implementation must use a reviewed library, authenticated domain metadata and a precise wire format. No naive string concatenation, delimiter ambiguity, value-dependent field discovery, or truncated tokens without collision analysis.

**Equality preservation:** for non-null occurrences a,b in the same approved canonical type and join domain, C(v(a)) = C(v(b)) implies P(a) = P(b).

**Distinctness preservation:** for non-null occurrences a,b in the same domain, C(v(a)) != C(v(b)) requires P(a) != P(b) in each released bundle. Cryptographic digest collisions are fantastically unlikely, but a READY release must explicitly validate its observed output mapping. Any collision fails closed. Don't say HMAC mathematically guarantees an injective mapping over all possible input values.

**Domain separation:** the same original value in different non-joining domains is NOT intentionally connected. Explicitly approved source-path aliases share d, otherwise they do not. Different types remain separate unless schema metadata approves a lossless canonical bridge and tests it.

**Scope separation:** the same original value processed in independent sessions gets computationally independent tokens when independent keys are used. This prohibits simple stable-token equality across sessions, but does NOT guarantee anonymization or overall cross-session unlinkability from metadata or auxiliary knowledge.

**Entity semantics:** Null, absent, empty string, sentinel, zero, mixed numeric/string types, case, whitespace and Unicode normal forms are not interchangeable by default. SQL NULL is not an ordinary join key. If the task needs a specific equivalence (e.g. case-insensitive ID), specify and test it explicitly. Never use implicit universal lower-casing or stripping. Distinguish preserving typed equal/not-equal relations from preserving business equality or SQL join semantics.

**Release completeness:** the same forbidden value may occur in structured fields, questions, log messages, evidence IDs, source labels, file names, exception strings, metadata and provider envelopes. Whole-release construction follows an allowlisted schema and approved structured question templates; unknown free-text blocks release in v0. Verification and audit cannot themselves contain raw values.

**Atomicity:** nothing is written to the approved output path or provider-facing channel until all transformation, property, exposure and serialization checks pass. On failure, no partial transformed data should remain. Secure handling of temporary files, stdout/stderr and crash dumps is part of the supported boundary.

**Task sufficiency:** a verified equality property alone does NOT imply an LLM can diagnose the incident. Independent contract completeness, diagnostic accuracy and evidence support are evaluated separately, prospectively.

## Attack-model table and expected outcomes

| Attack or failure | Security requirement | Planned test |
|---|---|---|
| Same ID in two approved sources | intentional within-scope join | identical tokens, consistent question reference |
| Two different requests in one domain | preserve inequality | distinct tokens, detect collision |
| Same ID in unrelated fields | no unintended join | different domains; no shared token by equality |
| Same original ID across separate sessions | no stable pseudonym | different tokens; report context-derived correlation separately |
| SQL NULL and absent values | no false entity match | explicit null/missing semantics, reject ambiguous inputs |
| Mixed "0012" and 12 | no accidental normalization | distinct unless explicit reviewed canonical conversion |
| Case/Unicode variants | no silent collapse | schema-specific normalizer tests, otherwise reject/keep distinct |
| Log says "ignore policy" | untrusted content never selects security policy | parse as data or refuse, no policy override |
| Raw ID inside question/error/file name | entire release checked | transform by typed template or refuse |
| Small identifier candidate dictionary | pseudonym not anonymity | measure known-input and chosen-input attacker capability |
| Repeated rare timing/frequency pattern | residual correlation | report exposure across multiple released sessions |
| Bundle size/row counts prohibited | impossible task-policy combination | infeasible, not covertly dropping rows |
| Key lost at session restart | operational limitation | cannot resume token identity without approved protected key lifecycle |

The product must not call a result secure merely because no literal string is present. The complete record structure, question, row order, frequencies, temporal precision and field presence remain possibly revealing.

## Comparative baseline matrix

| Method | Approved cross-source equality | Default cross-session token reuse | Persistent sensitive state | Key issue |
|---|---|---|---|---|
| Path-wise blanket redaction | Generally no useful entity join | Often same placeholder | None | Collapses unequal values |
| Global namespace HMAC | Yes if namespaces match | Yes | Long-lived key | Broader correlation |
| Session-scoped HMAC/HKDF (proposed) | Yes via explicit domain | No stable equality by default | Ephemeral key for v0 | Context leakage, no resumption |
| Session-scoped random token vault | Yes with mapping | No by default | Token/plaintext map | Secure retention & lifecycle |
| Consistent cloud de-identification | Often yes with appropriate keys/context | Policy-dependent | Cloud-managed keys / service | Strong existing competitor; policy setup |
| Format-preserving substitution | Often yes | Policy-dependent | Mapping/key dependent | Reveals length/class/grammar |

We should benchmark against a **strong manually configured, policy-compliant fixed pseudonymization** method. Comparing only with naive redaction is insufficient to claim an advantage.

## Minimal implementation and certification obligations

Phase A — approved schema: structured question template, source paths, join domains, entity types, null semantics, record inventory and field policy; perform offline inspection only.

Phase B — scope/key handling: CSPRNG test, per-domain HKDF reference vectors, stable encoding, intentional same-domain joins, distinctness, cross-domain separation, cross-scope difference; no permanent key system in v0.

Phase C — transformation executor: identity values rewritten across all approved occurrences and approved question placeholders. Unknowns, schema drift, unrecognized free text, missing classifications and unsupported task contracts block.

Phase D — verifier: independent local relation evaluator proves every declared scoped equality/inequality witness from raw vs output, checks entire released payload including metadata; explicit exposure vector and all refusal paths; atomic release.

Phase E — evaluation: construct prospective task-controlled contrast sets, exposure budgets and strong baselines without using Paper 1 hidden answers. Publish false denial rates, throughput and failure cases. Obtain separate approval before provider evaluations or held-out access.

Review gating: a second engineer/security reviewer should inspect scope/serialization/key-management implementation before customer trials. Tests reduce risk; they do not confer product-level certification.

## Conditions that would change the decision

If engineers need long-lived multi-agent troubleshooting sessions and cannot accept rekeying/reprocessing after a process restart, add protected session storage and authenticated resumption, or revisit a vault. If meaningful tasks require literal ID shape, assess a separately certified shape-preserving transform and residual exposure. If most real logs require arbitrary natural language, investigate safe structured extraction locally with explicit fail-closed validation before expanding scope. If existing managed tokenization yields the same utility, exposure and authoring time, revise the product differentiation.

## Decisions and owners (to resolve with Keshav, Harsh and Mohit)

1. Define the first typed *business equality* model, not just JSON scalar equality. (Research + engineering)
2. Define and validate the investigation scope and lifetime; decide whether v0 single-bundle limit is acceptable. (Engineering + product)
3. Author and review independent source-domain policies without oracle leakage. (Research + security)
4. Freeze pre-release exposure ceilings and strict unknown-field refusal. (Security)
5. Choose strong baseline, null/missing semantics, adversarial and metamorphic tests. (Research + red team)
6. Approve cryptographic implementation library, key lifecycle and collision-detection strategy before coding. (Security engineer independent review)
7. Review licensing/IP and launch claims before product distribution. (Project authors)

**Status of this ADR:** technical recommendation only; explicitly invites dissent and coauthor review. No provider experiments, held-out access, product deployment, or change to frozen Paper 1.