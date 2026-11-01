# DiagPriv Paper 2 — Prospective Research Protocol RFC v0.1

**Status:** DESIGN DRAFT FOR AUTHOR REVIEW; **not preregistered, approved, or implemented**. Created October 22, 2026. Related to issue #27 and docs/TASK_AWARE_PLANNER_RFC.md. This file proposes future work; it neither modifies nor interprets new frozen Paper 1 observations.

## 0. Non-negotiable research boundaries

- Paper 1 remains frozen, with published revised version DOI 10.5281/zenodo.23302664 (all-versions DOI 10.5281/zenodo.23142444). Do not modify historical generator definitions, prompts, scorers, experiment records, evidence-support protocols, hashes, or results.
- Do not inspect protected held-out data or seed ranges, trigger provider experiments, access real production/customer data, or construct new validation results as part of this RFC.
- Planner inference must not import the oracle-bearing Incident object, its hidden diagnostic invariants, private expected evidence, target/twin role, answer, or seed-specific mechanism labels. Independently reviewed schema/policy metadata is permitted.
- Any development implementation and product adaptation must use separately versioned APIs and new test fixtures. This protocol must be approved before we publish causal, optimality, or security claims.

## 1. Research question and scientific positioning

**Primary question:** For supported operational troubleshooting tasks, can a local, deterministic, policy-constrained planner select a transformation that retains independently declared diagnostic relationships, respects an exposure budget, and reduces model-visible disclosure relative to strong, policy-compliant fixed transformation baselines?

**Secondary questions:**
1. How often are task contracts incomplete, ambiguous, or infeasible when developed independently of case oracles?
2. Does the resulting transformed evidence preserve RCA accuracy and cited-evidence quality when evaluated prospectively?
3. What exposure remains through linkability, format, timing, cardinality, unstructured messages, prompts, and combination of released properties?
4. How often does the planner correctly abstain under incomplete schema classification, untrusted instructions, and conflicting requirements?

**Positioning / close prior work to check in detail before novelty freeze:** MINIM (ICML 2026, privacy-aware minimal agent UI views), Adaptive Text Anonymization (ACL Findings 2026, task-specific privacy–utility optimization), Operationalizing Data Minimization for Privacy-Preserving LLM Prompting (2025 preprint), and Google's established deterministic pseudonymization preserving joins. Task-awareness and data minimization by themselves are NOT novel. A candidate contribution is a typed, certifiable diagnostic-relation contract coupled to strict release constraints and operational RCA evaluation. No priority claim until thorough related-work comparison and independent review.

## 2. Formal contract and limits of the word "sufficient"

Let x be the complete local operational evidence and q the troubleshooting question. Let p be an independently authored policy and task-contract bundle; let C be a finite, reviewed registry of candidate composite transformation profiles.

Each approved contract defines a set of scoped, typed required properties R(q,p), including possible equality/inequality, cross-source linkage, reference shape, ordering, strict overlap, duration granularity, cardinality, event presence, and numeric-unit relations. A profile c has a reviewed capability certificate Cert(c), and is executed as T_c(x,q). Its **entire model-visible release** Z includes the transformed question, structured rows, log text, IDs, field names, source inventory, and any other provider-visible surface.

The planner can release only if:
- its profile's verified property guarantees cover R(q,p), including composition-specific checks;
- no classified forbidden or unknown field is released;
- each conservative exposure bound E_i(c,x,p) satisfies the matching policy ceiling B_i(p);
- whole-release postconditions pass; and
- the question, policy, and inferred contract are consistent.

Unknown bounds do not pass strict ceilings. Among feasible candidates, report the nondominated exposure frontier and choose using a *predeclared*, explicit lexicographic priority and stable tie-break. If none qualifies: infeasible; for ambiguous contracts/classifications: needs_policy_review. **No partial output or raw fallthrough.**

A structure-preservation certificate shows that specified mathematical relationships survived the transformation. It DOES NOT prove that those requirements are *complete*, that an LLM will produce the right diagnosis, that released data is anonymous, or that an information-theoretic minimum has been achieved. "Minimum" is only relative to the reviewed candidate registry and explicit constraints.

Competing explanations may have multiple different sets of sufficient observable evidence. We must allow multiple candidate requirement sets and report unresolved ambiguity rather than claiming a uniquely minimal diagnostic explanation.

## 3. Proposed hypotheses (falsifiable; no results yet)

**H1 — Property correctness.** On approved prospective synthetic workloads, a ready planner output preserves every property certified and required by its independently authored contract. Failure: any mismatched certified property among releases.

**H2 — Relative minimization.** Among cases with multiple feasible profiles, task-aware selection reduces at least one prespecified exposure dimension without increasing any other protected dimension beyond the policy budget, relative to the best *eligible fixed policy* baseline. Count ties and non-comparability. Failure: no measured advantage or a materially worse frontier; avoid an unqualified global privacy score.

**H3 — Diagnostic utility.** Relative to the strongest compliant fixed baseline(s), task-aware evidence retains non-inferior RCA accuracy under a predeclared practically relevant margin. This is empirical and requires a separately authorized provider evaluation, appropriate repetitions and sample-size analysis. If non-inferiority cannot be supported, report uncertainty.

**H4 — Task relevance.** For the same x and policy p but two genuinely different approved questions, the chosen profiles differ when task requirements demand it, yet no profile reveals hidden oracle/target/twin metadata. If the choices never vary, task-awareness is unsubstantiated. Also report occasions when identical profiles are the correct result.

**H5 — Abstention/security boundary.** All known forbidden-field, missing classification, ambiguity, budget-conflict, injection, unknown join, and missing-composition-certificate fixtures are blocked with a payload-free result. Any tested forbidden release is a blocker, even if average metrics look favorable. Passing tested cases does not imply universal prevention.

## 4. Independently authored task contracts and benchmarks

Initial reviewed contract families to *design* (not implement in this RFC):
- Cross-source repeated-request / duplicate-effect correlation.
- Lifecycle, deadline, duration, overlap, and state-transition analysis.
- Reference-validation and shape-sensitive lookup; explicit allowed shape leakage.
- A genuinely different operational task family, such as fan-out/incomplete batch processing, to challenge transfer beyond Paper 1.
- One no-release/infeasible task where privacy policy forbids a truly necessary relationship.

Use Paper 1's existing families solely as transparent development sanity checks, not as the claimed final evidence of Paper 2 generality. Author novel schemas, mechanism contrasts, nuisance/negative controls, question variants over matched x, and admissible privacy policies *before* evaluating planner outputs. Make non-temporal signals matched for temporal mechanism contrasts when feasible. Independently review oracle-free contract authoring and adjudicate disagreements without peeking at per-instance ground truth.

Prospective test data must be distinct from development; access only after designs, scoring, baselines, thresholds, model settings, and code are locked and authorized. Do not repurpose Paper 1's reserved held-out data or assume any hidden range is available.

## 5. Baselines and fairness rules

1. Raw evidence: diagnostic upper-context comparator; label as policy-ineligible where appropriate.
2. Naive field-wise redaction: weak diagnostic control; cannot be sole comparator.
3. Best policy-feasible **fixed** pseudonymization/relative-time profile selected once using development data: mandatory strong baseline.
4. Independently specified *manual task-aware* policy: mandatory human/expert comparator if a credible manual alternative is feasible.
5. Task-agnostic minimum-disclosure profile within the same registry, if supported.
6. Planner ablations: without question conditioning; without relation certificates; without composition checks (offline diagnostic only, never allowed to release to an actual provider if unsafe).
7. Oracle-aware planner: optional offline ceiling only, explicitly invalid for product use and never part of inference or provider-visible input.

Match the data, evidence question, field schemas, provider prompt, model configuration, token treatment where practicable, and exposure-budget legality. Report no-release as a legitimate outcome; do not quietly exclude it from utility or count it as a wrong RCA without a specified policy.

## 6. Evaluation

**Offline primary safety/structural outcomes**
- Ready / needs_policy_review / infeasible coverage by task and policy.
- Equal-pair true-positive retention AND unequal-pair false-positive collapse.
- Cross-source and cross-incident linkage, shape/signature retention, time-gap accuracy and overlap/order coverage, numeric relations, count and field presence.
- Forbidden-literal exposure, unclassified/unhandled-field occurrences, text/question leakage, mapping/error leakage, configuration-independent shortcuts.
- Full multi-axis exposure vector, all denominators and not_applicable/unknown distinctions; registry-relative Pareto dominance.
- Adversarial dictionary/candidate-set and known-time-anchor reconstruction tests under fixed attacker knowledge.

**Prospective model outcomes, only after approval**
- Exact five-label RCA and separately defined mechanism/trigger/component accuracy, evidence-support sufficiency and citation validity.
- Paired target/twin discrimination and nuisance controls; model response failure coverage.
- Predeclare model families, call repetition, analysis unit, confidence intervals, non-inferiority margin, multiple-comparison priorities, and sample size before provider calls. Use independent *incident construction* clusters rather than treating repeated model calls as independent cases. Do not infer equal performance from small raw count differences.

**Product-facing measurements (separate from academic evidence):** median/p95 local processing latency on stated payload sizes, failed-release UX, policy authoring burden, manual-debugging time, and developer task success with synthetic data. Product usability is not a research security guarantee.

## 7. Shortcut/leakage and metamorphic suite

For every supporting fixture: alpha-rename identifiers; reorder rows where semantics permit; vary batch candidates; permute irrelevant fields; swap target/twin role metadata; mutate hidden oracle without changing model view; inject malicious instructions into logs, question, and file paths; introduce unknown nested keys, secrets, malformed timestamps, mixed units, missing endpoints, high-cardinality joins, and all-to-one token collisions.

Verify plan equivalence where only oracle facts changed. Check provider-visible *question text*, structured rows, free-text logs, error fields, evidence IDs, returned envelopes, and residual identifiers. An attacker may correlate timing plus shape plus joins; certificates for individual transforms alone are insufficient for compositions.

## 8. Approval gates / owner's participation

**Gate P2-0 (this RFC):** Authors review the research question, novelty challenge, threat boundary and hypotheses; all unsettled items explicitly assigned. No experiment approval implied.

**Gate P2-1:** Freeze typed relation vocabulary, independent annotation and adjudication protocol, two or more nontrivial task contracts, reference schema, candidate registry, policy ceilings, tie-break priorities, refusal behavior, and offline acceptance tests. Principal researcher explains each with examples and counterexamples to lead author.

**Gate P2-2:** Implement versioned policy-only planner and transform adapters using synthetic unit cases; preserve Paper 1 source and outputs. Every PR includes algorithm walkthrough, diff, invariant tests, failure injection report and explicit lead-author review.

**Gate P2-3:** Complete offline validity checks and attack simulation. Publish failures and unknown coverage, not only passes; independent security review.

**Gate P2-4:** Freeze evaluation protocol and explicit provider/held-out authorizations. Only then run prospective evaluations.

**Gate P2-5:** Interpret results including negative results and credible external validity limits; manuscript authored with all coauthors.

## 9. Open decisions for authors (do not treat defaults as final)

- Who independently authors and signs off policy/classification metadata, task contracts and new benchmark oracle?
- Can users supply explicit contract ID at first, and what measured evidence justifies adding autonomous task inference?
- Which diagnostic relations and disclosure components are mandatory for first prospective comparisons?
- What profile registry and predeclared tie-break rule is defensible?
- Which novel task families sufficiently depart from Paper 1?
- Which reference methods genuinely instantiate strong compliant fixed and manual task-aware baselines?
- What security review and provider/held-out governance process is required before study execution?

**Research integrity principle:** A passed local relation test is a necessary software result, not evidence of empirical RCA utility or privacy/anonymity.


## 10. Alignment with approved product mission — destination policies are upstream constraints

**Direction confirmed 2026-11-01:** Long-term DiagPriv combines AI data-movement/residency controls with task-aware minimization. See ../product/ADR_002_DESTINATION_POLICY_AND_MINIMIZATION.md. The scientific Paper 2 scope remains intentionally narrower: *policy-constrained task-aware diagnostic representation selection*, not claims of actual provider region enforcement.

Make the security policy include independently authored and versioned data classifications, approved purpose/actor, recipient/deployment/processing-region profile and content-release ceilings. A **trusted destination gate** takes priority over diagnostic accuracy. The planner sees approved policy descriptors only and may not turn a forbidden or unknown route into an allowed route, infer region from URLs, downgrade data sensitivity automatically, or authorize its own transfer.

For offline prospective research, use simulated destination profiles and independently specified policies to test authorization/refusal logic. That validates **policy-decision correctness under declared inputs**, not real provider routing, residency, storage location or legal compliance. Physical region assurance and controlled egress belong to separately assessed product integration.

Add proposed factorial challenge cases to the frozen protocol before coding: (a) same evidence/task, allowed vs denied destination; (b) allowed destination but forbidden diagnostic linkage; (c) unknown or expired route metadata; (d) identical security policy but different task contracts; (e) approved transformed disclosure vs disallowed original data only if an explicit policy specifies this classification; and (f) hidden oracle modifications that must not affect the plan. Compare fixed compliant baselines under the **same** destination and disclosure policy. Report refusal, feasible coverage and multi-axis exposure separately from RCA. Never count a blocked transfer as diagnostic failure without a separately defined metric.

**Novelty boundary:** Neither regional routing policy nor data minimization is new by itself. The candidate Paper 2 contribution remains verifiable typed diagnostic relation selection under hard, externally governed release constraints, accompanied by transparent abstention and empirical RCA/exposure analysis. We may reject that novelty claim if strong prior work or comparative results contradict it.

**Scientific governance:** This section changes the RFC proposal only. It does not unlock provider experiments, held-out data, Paper 1 artifacts or any production egress.
