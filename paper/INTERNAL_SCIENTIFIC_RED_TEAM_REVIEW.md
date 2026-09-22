# Internal scientific red-team review

Issue #49. Review basis: `main` at
`48da386d073cf5070d41ef4464344eda7504223d`.

## Independence disclosure

This is an **internal adversarial review performed by the project team/assistant** after invited collaborators had not yet returned their reviews. It must not be represented as an independent external, blinded, or collaborator review. A later review from a collaborator or outside reader should be preserved separately.

No provider call, RCA rerun, validation access, or held-out access was used for this review.

## 1. Contribution summary

DiagPriv studies how to transform operational troubleshooting evidence before it is released to an external LLM while attempting to preserve the relations needed for root-cause analysis. The current paper uses three controlled synthetic incident families to separate linkage-, representation-shape-, and temporal-relation dependencies, and evaluates transformed views along three distinct axes: structured RCA labels, cited-evidence support, and model-visible representation exposure. The strongest contribution is not a claim that one transform is best, but an experimental framework for making a task-relevant diagnostic relation explicit and checking what a privacy-oriented representation change preserves or destroys. The evidence is development-stage and supports a controlled-methods claim, not a general production or formal-privacy claim.

The manuscript communicates this intended contribution clearly overall. The strongest wording is in the Introduction, Problem Formulation, Privacy--Utility Analysis, and Limitations. A few central result phrases should still be tightened before preprint so that designed dependencies are not read as isolated causal effects on model behavior.

## 2. Strongest aspects

1. **The paper separates three outcomes that are often conflated.** RCA correctness, evidence support, and representation exposure are measured independently. This is methodologically useful and the manuscript is explicit that a correct label may be weakly evidenced and that low literal exposure is not a privacy guarantee.

2. **Incident 003 v3 is a materially stronger construction than the earlier temporal benchmark.** The target/twin design, matched non-temporal projection, role-neutralization work, safe control, and destructive temporal ablation substantially reduce simple shortcut explanations. The paper also discloses that v3 was created after an earlier version proved solvable from non-temporal cues.

3. **The privacy analysis is unusually careful about what is and is not measured.** Literal retention, equality/separation, cross-source linkage, frequency, shape, cardinality, absolute time, and relative temporal structure are kept separate. The analysis repeatedly refuses to equate these with anonymity, re-identification probability, differential privacy, compliance, or provider security.

4. **The v4 -> v5 evidence history is transparent.** Stage-1 v4 remains the historical primary result; Stage-1 v5 is labeled post-hoc secondary; Stages 2 and 3 use prospectively frozen v5. That is the correct provenance treatment.

5. **Negative and awkward observations are retained rather than optimized away.** Incident 002 transport failures remain missing in the primary view; the recovery is labeled sensitivity analysis; format-preserving seed 1005 remains a miss despite invariant preservation; Incident 003 has only four pairs and one call/case; no statistical or equivalence claim is made.

6. **Related-work positioning is now conservative.** The manuscript explicitly concedes prior task-aware anonymization, privacy-aware local RCA, evidence-grounded RCA, and citation-support evaluation. The surviving contribution is a scoped combination, not a priority claim.

## 3. Must fix before preprint

### M1. Update stale artifact/reproducibility wording after merged issue #35 work

The Methodology currently says that independent replay of provider observations "awaits the provenance-safe distribution work tracked separately in issue #35." The Limitations similarly says issue #35 "addresses safe distribution." That is now stale after the merged RFC/verifier work.

The paper should instead state the actual current boundary: Level-1 source/config/aggregate/hash reproducibility is available; a private exact-observation archive is designed but not provisioned/distributed; public observation-level release is unavailable. This is a factual synchronization fix, not a change in scientific results.

Affected areas:
- `paper/sections/methodology.tex`
- `paper/sections/limitations.tex`
- any final reproducibility statement added during #51.

### M2. Make the Incident 003 asymmetry explicit in the interpretation, not only in the table

The most informative pattern is not merely paired discrimination 3/4 -> 2/4 -> 0/4. The target mechanism is **4/4 under raw, relative-time, and ablation**, while the temporal twin moves **3/4 -> 2/4 -> 0/4**. Under ablation every case is labeled concurrency.

That is consistent with the intended temporal distinction becoming unavailable, but it is also evidence of a strong model/category prior toward `incorrect_concurrency_control` when the distinguishing temporal proof is removed. The paper currently reports these counts accurately, but the central narrative can be read as a generic loss of temporal-reasoning ability across both roles.

Before preprint, explicitly say that:
- the degradation is entirely on the twin side in these four constructions;
- ablation produces mechanism collapse toward concurrency, not random failure;
- this supports the benchmark's ambiguity/diagnostic-dependency story but does not identify a provider-level causal effect of "removing time";
- one call per case leaves stochastic/model-prior explanations unresolved.

This should be reflected consistently in the Results discussion and Conclusion; the Abstract may remain concise but should not imply a stronger causal interpretation.

### M3. Tighten the Incident 002 "shape" claim to match the actual intervention

Incident 002 is designed so that external-reference structure is the intended differentiator, and the raw/format-preserving versus opaque-condition results are directionally consistent with that design. However, the compared transformations do not vary **only** one feature called "shape." HMAC/tokenization/redaction also change length, character classes, separators, token vocabulary, frequency presentation, and potentially other surface cues relative to format-preserving pseudonyms.

Therefore the provider observations do not isolate a causal effect of shape alone. The manuscript mostly protects itself with "directionally consistent" language, but phrases such as "requires the shape" or "shape-dependent" can be read as an empirical sufficiency/causality claim.

Before preprint:
- describe Incident 002 as a **shape-sensitive designed family** or say shape is the **intended diagnostic differentiator**;
- preserve the statement that format-preserving retained the declared structural signature while opaque methods did not;
- keep explicit that preservation was not sufficient (seed 1005) and that the experiment is associational, not a shape-only causal ablation.

### M4. Make the Incident 002 primary-versus-recovery distinction equally visible at the headline table level

Table 3 uses the 18-valid-per-condition **transport-recovered sensitivity view** for Incident 002. The caption says so, and the prose preserves the primary coverage, but a scanning reader sees the balanced 18/18-style utility comparison before seeing how concentrated the original failures were (9 redaction, 1 tokenization).

Because the recovery calls occurred later and are explicitly sensitivity substitutions rather than the primary as-executed experiment, the final paper should make primary coverage impossible to miss. Reasonable fixes include:
- adding a "primary valid" column/companion row;
- adding a compact primary-coverage table adjacent to Table 3; or
- strengthening the caption/visual label so the displayed Incident 002 numbers cannot be mistaken for the primary experiment.

Do not replace the sensitivity view; preserve both views and their provenance.

## 4. Should fix before preprint

### S1. Rename "Identity-dependent Incident 001"

The actual intended dependency is same-request equality/linkage, while literal customer identity is explicitly discardable. "Identity-dependent" risks implying the opposite of the paper's point. "Linkage-dependent Incident 001" or "equality/linkage Incident 001" would be more precise.

### S2. State more explicitly that cross-family numbers are not directly comparable

Incident 001 uses GPT-5.6 Luna and a five-seed single-call protocol; Incidents 002/003 use GPT-5.6 Sol with different repetition/pairing structures. The manuscript does not statistically pool these results, but the narrative uses all three families to motivate one thesis. Add a short statement that the families demonstrate qualitatively different designed dependencies and their absolute accuracy levels should not be compared as a single benchmark ranking.

### S3. Bring the adaptive benchmark-design history slightly earlier

The Limitations correctly discloses that Incident 003 v3 was redesigned after an earlier version was solvable from non-temporal cues. This is important enough to mention briefly in Methodology or the Incident-003 family description as development-stage benchmark refinement. Doing so reduces the appearance that the limitation was buried late in the paper.

### S4. De-emphasize exact five-label RCA when discussing the intended Incident 002 dependency

Component accuracy behaves differently from trigger/mechanism accuracy, and component ownership is acknowledged as less stable. The shape hypothesis is mainly about trigger/mechanism recognition. Keep exact RCA, but ensure the scientific interpretation does not treat exact-five-label success as the only or most diagnostic endpoint for Incident 002.

### S5. Add one sentence explaining why v5 is a methodological repair rather than outcome optimization

The current evidence section is already transparent. A concise sentence can make the logic even stronger: v5 was introduced to make semantic proof representation-invariant across structured/log modalities, while retaining complete-path and semantic-predicate requirements; it was not tuned to make Stage-1 targets pass (all four still fail the overlap essential under v5).

### S6. Keep "privacy" operationally tied to exposure reduction on the first page

The abstract says the exposure vector is not an anonymity score, which is good. Because the title contains "Privacy Transformations," reviewers from security/privacy venues may still expect an adversarial privacy metric or formal guarantee. A short first-page formulation such as "privacy-oriented transformations that reduce selected model-visible exposure" would further calibrate expectations without weakening the paper.

## 5. Optional improvements

- Show the four Incident-003 pair patterns in a compact table near Figure 3, not only the aggregate bar chart. With n=4, individual pair outcomes are scientifically more informative than a bar without uncertainty.
- Consider a small schematic showing which representation property each baseline preserves: literal, equality/linkage, shape, absolute time, relative time. This may make the thesis easier to grasp than prose alone.
- Add a one-sentence note that a human baseline would measure both task difficulty and whether the declared invariants are actually sufficient for a knowledgeable reader, but leave the experiment for follow-up unless #51 decides otherwise.
- Consider a future second-model-family replication rather than adding more calls from the same family if the goal is external validity.
- Keep the phrase "give the AI the problem without giving it the person" as motivation only; the current caveat does this correctly.

## 6. Claim-by-claim concerns

### Incident 001

**Supported as a development observation:** HMAC and tokenization obtained 5/5 exact RCA on the five selected development seeds while removing annotated direct literals; redaction and format-preserving obtained 4/5. The exposure analysis shows that deterministic pseudonyms preserve much—but not all—cross-source linkage.

**Safe interpretation:** preserving equality/linkage can retain useful diagnostic structure while changing literal identity in these selected cases.

**Do not infer:** HMAC/tokenization are generally superior, all relevant identifiers were hidden, or preserved equality is sufficient for RCA.

### Incident 002

**Supported:** raw had 15/18 trigger/mechanism correctness in the sensitivity view; format-preserving had 10/18; opaque baselines had 1--2/18. The declared structural invariants are preserved under format-preserving pseudonymization and removed by opaque representation changes.

**Concern:** multiple representation properties co-vary with the transform. This supports a shape-sensitive interpretation, not a clean causal estimate of shape alone.

**Important negative evidence:** format-preserving seed 1005 fails all three logical trials despite declared invariant preservation. This is valuable and should remain prominent because it prevents a sufficiency claim.

### Incident 003

**Supported:** the v3 construction audit establishes matched non-temporal projections and conflicting mechanism oracles; raw/relative preserve the defining time relations; ablation makes the temporal predicates unavailable. Observed paired mechanism discrimination is 3/4, 2/4, 0/4.

**Critical nuance:** the target is always classified as concurrency. The observed degradation is the loss of correct twin state-transition diagnoses. This is consistent with temporal evidence being needed to distinguish the twin from a concurrency prior, not proof of a general temporal-reasoning effect.

### Privacy exposure

**Supported:** exact measured representation properties of selected synthetic ModelViews.

**Well bounded:** the manuscript explicitly rejects interpretation as re-identification probability, membership inference, compliance, DP, k-anonymity, or legal de-identification.

**Residual concern:** annotation coverage defines much of the measurement surface; unannotated messages/IDs/context can remain. The paper states this and should keep it visible.

### Evidence support

**Supported:** v4 is historically correct for Stage 1; v5 is a post-hoc representation-invariant secondary analysis; Stage 2/3 freeze v5 prospectively.

**Strength:** v5 does not simply reward the existing responses. All targets remain unsupported because they omit a complete overlap proof, which argues against simple metric shopping.

## 7. Incident 003 review

The target/twin design is the strongest internal-validity component of the paper. The same evidence, subject-specific questions, role-neutral anchor allocation, 200-construction projection audit, and structural-isomorphism check under ablation are much stronger than comparing unrelated incidents.

The destructive ablation is a fair **causal-information availability control** for the benchmark: it removes timestamp semantics and chronological log order rather than replacing time with a subtly different ordering. It is not an optimal privacy transformation and should not be presented as one.

The remaining scientific limitations are:
- only four provider-observed pairs;
- one call per role/condition;
- same model family;
- v3 benchmark design followed observation of a shortcut in an earlier version;
- possible model prior toward concurrency after temporal evidence is removed.

None of these invalidates the construction. They limit the conclusion to a development-stage directional observation.

## 8. Privacy-methodology review

The vector-not-score approach is justified. A single scalar would hide important differences: redaction collapses entities; HMAC/tokenization retain linkage/frequency; format-preserving retains character-class structure; relative time removes absolute timestamp literals while preserving exact measured gaps; temporal ablation removes time evaluability.

The paper is appropriately explicit about residual leakage:
- HMAC/tokenization retain deterministic linkage/frequency;
- format-preserving leaks length/separators/character classes;
- relative-time is anchor-reconstructable;
- I001/I002 scalar transforms leave unannotated timestamps intact;
- I003 temporal transforms leave non-temporal operational IDs intact.

The main boundary is that this is **representation exposure**, not adversarial privacy. That limitation is honestly stated and should remain central in title/abstract/limitations framing.

## 9. Evidence-v4/v5 review

The historical treatment is scientifically defensible:
- v4 remains the Stage-1 primary rule and score (0/8);
- v5 was developed after forensic inspection and is explicitly post-hoc on Stage 1 (3/8);
- Stages 2 and 3 prospectively froze v5 before provider calls (4/8 and 0/8);
- Stage-1 v5 is not used as if it were a prospective baseline.

The best evidence against simple score-shopping is that v5 still rejects all four target responses for incomplete overlap proof and rejects 1299 twin for missing essential events. Add this rationale explicitly to reduce reviewer suspicion.

Do not compare raw-v4 0/8 numerically to Stage2/Stage3 v5 as if they were the same measurement protocol. The current paper mostly avoids that error.

## 10. Novelty and related-work review

The current positioning is appropriately narrowed. The literature review already establishes:
- pre-release prompt/privacy transforms are prior work;
- task-aware anonymization/privacy-utility optimization are prior work;
- consistent pseudonym replacement is prior work;
- LLM operational RCA is prior work;
- privacy-aware RCA via local deployment exists;
- evidence-grounded RCA and citation support evaluation are prior work.

The manuscript's defensible contribution is the **joint controlled evaluation design**: transformed operational evidence + explicit diagnostic invariants + structured RCA + evidence support + representation-exposure vector + matched linkage/shape/time families.

The finite search does not prove priority. The manuscript correctly avoids "first/only/unique" claims. Keep that posture.

## 11. Top rejection risks

1. **External validity / evidence scale.** Three synthetic families, very small selected development sets, one model family, no matched final held-out privacy evaluation, no human baseline, and no production incidents make this primarily a controlled methods paper.

2. **Adaptive benchmark-development history and no independent validation.** Incident 003 v3 was created after a prior version exposed a shortcut. The redesign is scientifically reasonable and disclosed, but without a subsequent untouched held-out phase a skeptical reviewer may view the evidence as development-tuned.

3. **Privacy strength versus title/domain expectations.** The paper measures residual representation exposure, not adversarial re-identification or a formal privacy guarantee. A security/privacy reviewer may regard "privacy transformation" as stronger than the evaluated threat model unless the operational definition remains explicit throughout.

A secondary risk is model-response variability: four Incident-003 pairs with one call per case and concentrated Incident-002 transport failures mean provider stochasticity is not characterized.

## 12. Final internal recommendation

**Ready for a development-stage preprint after minor-to-moderate revisions.**

I found **no blocking research-design issue** for a transparently labeled controlled development study. The paper should not be presented as final evidence that DiagPriv generalizes to production incidents or provides formal privacy. The four must-fix items above are primarily interpretation/provenance/presentation corrections, not requests to rerun experiments.

For a stronger archival/conference version, the most valuable next evidence would be a preregistered untouched held-out phase and/or blinded human difficulty baseline, followed by cross-model or more realistic incident replication. Those are strengthening steps, not prerequisites for releasing an honest preprint.
