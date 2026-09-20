# Verified related-work review for issue #46

Internal research note, 2026-09-19. The manuscript cites the sources in
`references.bib`; this note records the comparison behind its deliberately
bounded positioning. It is not an exhaustive systematic review. “Not
evaluated” below means the inspected paper did not evaluate that axis; it is
not a claim that its method could never support it.

## Search and verification log

- Searched the ACL Anthology, ICLR/OpenReview, arXiv original-author records,
  EuroSys accepted-paper list, Microsoft Research publication pages, NIST CSRC,
  and RFC Editor for privacy-preserving LLM input, clinical de-identification,
  task-sensitive anonymization, operational RCA, temporal reasoning, and
  citation/evidence support. Secondary search results were discovery aids
  only, not authority for manuscript claims.
- Checked title, full author order, year, venue/status, and DOI where present
  against each linked primary record. The EuroSys paper's **published** title
  is *Automatic Root Cause Analysis via Large Language Models for Cloud
  Incidents*; an earlier author preprint was also circulated as *Empowering
  Practical Root Cause Analysis...*. The bibliography uses the former and
  does not conflate the two. Cloud-OpsBench is explicitly an arXiv preprint.
- Read beyond abstracts for the closest works: [EmojiPrompt PDF](https://aclanthology.org/2025.naacl-long.614.pdf),
  [RUPTA PDF](https://aclanthology.org/2025.acl-long.1404.pdf),
  [Tau-Eval PDF](https://aclanthology.org/2025.emnlp-demos.16.pdf),
  [adaptive anonymization PDF](https://aclanthology.org/2026.findings-acl.401.pdf),
  [RCAgent full text](https://arxiv.org/html/2310.16340v3), and
  [Cloud-OpsBench full text](https://arxiv.org/html/2603.00468v2).
  The matrix below reflects methods/evaluation sections, not an abstract's
  silence. A further pre-submission review should inspect later versions and
  newly published literature.

## Closest prior work

Each entry records area, actual method and evaluation, privacy mechanism,
utility outcome, overlap, difference, and implication for positioning.

1. **`lin2025emojiprompt` — pre-release cloud-LLM prompt privacy.**
   [NAACL paper](https://aclanthology.org/2025.naacl-long.614/).
   Generatively obfuscates prompt content before a cloud LLM; tests eight
   domain datasets including recommendation and classification and simulated
   inference attacks. Privacy mechanism: prompt obfuscation, including
   linguistic/non-linguistic symbols. Utility: downstream task performance.
   Overlap: transformation before external inference plus privacy/utility
   measurement. Difference: no controlled operational RCA family or explicit
   diagnostic-invariant audit in the studied tasks. **Implication:** do not
   claim pre-release transformation plus task utility is new.
2. **`loiseau2026adaptive` — task-conditioned anonymization.**
   [Findings paper](https://aclanthology.org/2026.findings-acl.401/).
   Optimizes anonymization instructions for privacy/utility objectives;
   evaluates five datasets. Privacy mechanism: automatically selected text
   anonymization instructions. Utility: downstream task objectives. Overlap:
   task-conditioned disclosure and privacy--utility comparison. Difference:
   DiagPriv's implementation compares fixed transforms and measures explicit
   operational diagnostic relations, not an automatic optimizer.
   **Implication:** drop any claim to originate task-aware anonymization;
   describe fixed-condition diagnostic evaluation instead.
3. **`loiseau2025taueval` — multi-task privacy/utility evaluation.**
   [EMNLP demo](https://aclanthology.org/2025.emnlp-demos.16/).
   Framework for evaluating text anonymizers across PII/authorship privacy
   objectives and eight downstream tasks. Privacy mechanism: evaluates
   multiple anonymizers rather than prescribing one. Utility: task-sensitive
   losses. Overlap: privacy and downstream utility are separate measured
   outcomes. Difference: no operational RCA or typed linkage/shape/temporal
   ModelView exposure vector. **Implication:** do not claim the first
   multi-metric or task-sensitive privacy evaluation.
4. **`yang2025robust` — utility-preserving text anonymization.**
   [ACL paper](https://aclanthology.org/2025.acl-long.1404/).
   LLM privacy evaluator, utility evaluator, and optimizer; tests
   re-identification-related measures and downstream occupation
   classification on biographies and personal text. Privacy mechanism:
   rewritten anonymized text. Utility: classification performance. Overlap:
   jointly evaluates privacy and downstream task success. Difference: not
   operational event diagnosis or explicit cross-source and temporal
   invariants. **Implication:** avoid broad “prior work only removes PII.”
5. **`singh2025redactor` — consistent clinical entity replacement.**
   [ACL Industry paper](https://aclanthology.org/2025.acl-industry.36/).
   Hybrid clinical de-identification over structured/unstructured EHR and
   audio; retrieval-based relexicalization keeps protected-entity substitutes
   consistent. Privacy mechanism: detection plus consistent substitution.
   Utility: clinical-data coherence/downstream applicability; the paper's
   principal reported evaluation is de-identification quality, not RCA.
   Overlap: consistency is explicitly preserved. Difference: no diagnostic
   causal labels or exposure vector for operational logs. **Implication:**
   never claim consistent pseudonym substitution was absent in prior work.
6. **`ponomarenko2026capid` — context-aware PII filtering.**
   [EACL SRW paper](https://aclanthology.org/2026.eacl-srw.23/).
   Locally fine-tuned small model detects/types PII and predicts contextual
   relevance before LLM QA. Privacy mechanism: selective PII filtering.
   Utility: QA under anonymization. Overlap: task relevance constrains what
   is hidden. Difference: does not use operational RCA invariants; DiagPriv
   does not implement CAPID-like learned filtering. **Implication:** avoid
   implying purpose-sensitive redaction starts with DiagPriv.
7. **`wang2024rcagent` — privacy-aware operational RCA.**
   [CIKM author full text](https://arxiv.org/html/2310.16340v3).
   Tool-augmented RCA agent on Alibaba Cloud jobs, scored for roots,
   solutions, evidence, and responsibilities. Privacy mechanism: an
   internally deployed model keeps production diagnostics off external APIs,
   rather than transforming them for release. Utility: RCA and human/automated
   assessment. Overlap: RCA, evidence, and explicit privacy concern.
   Difference: no external-model pre-release representation comparison.
   **Implication:** claim B (“operational RCA ignores privacy”) is too broad.
8. **`chen2024automatic` — RCACopilot.**
   [EuroSys accepted paper](https://2024.eurosys.org/accepted-papers.html)
   and [author preprint](https://arxiv.org/abs/2305.15778).
   Alert-specific handlers gather multi-source diagnostics; LLM predicts
   root-cause category and explanatory narrative on Microsoft incidents.
   Privacy mechanism: not a compared pre-release transform in this study.
   Utility: RCA category accuracy. Overlap: operational multi-source LLM
   diagnosis. Difference: DiagPriv varies evidence representation and
   measures residual exposure. **Implication:** LLM RCA is established.
9. **`xu2025openrca` — operational RCA benchmark.**
   [ICLR paper](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d29b8d53678015079e1d245c023e49d2-Abstract-Conference.html).
   335 enterprise failures and heterogeneous telemetry, with an RCA agent
   baseline. Privacy mechanism: no matched release transformation evaluated.
   Utility: root-cause localization. Overlap: LLM RCA benchmark.
   Difference: DiagPriv's three small synthetic families manipulate the
   representation/invariant, not live-system realism or scale.
   **Implication:** describe DiagPriv as a controlled complement, not a
   replacement for operational benchmarks.
10. **`wang2026cloudopsbench` — evidence-grounded operational RCA.**
    [arXiv v2](https://arxiv.org/html/2603.00468v2), preprint.
    Replays runtime-verified Kubernetes incident snapshots and evaluates RCA
    plus milestone-based evidence graphs. Privacy mechanism: no pre-release
    privacy transform is part of its reported comparison. Utility: RCA and
    investigation/evidence closure. Overlap: explicitly separates correct
    RCA from support; matched replay. Difference: DiagPriv measures
    transformed model-visible exposure and typed invariant loss.
    **Implication:** retract any assertion that separating answer and
    evidence is unique to DiagPriv.
11. **`gao2023citations` — cited-answer evaluation.**
    [ALCE](https://aclanthology.org/2023.emnlp-main.398/) evaluates
    correctness and citation quality in retrieval-based question answering.
    Privacy mechanism: not evaluated. Utility: answer correctness and
    verifiability. Overlap: cited passages must support a generated answer.
    Difference: DiagPriv's citations refer to incident evidence IDs and
    typed RCA requirements. **Implication:** support scoring is not a new
    evaluation dimension in itself.
12. **`zhang2024finegrained` — fine-grained citation support.**
    [INLG study](https://aclanthology.org/2024.inlg-main.35/) tests
    full/partial/no citation-support metrics against human judgment.
    Privacy mechanism: not evaluated. Utility: quality of attribution
    assessment, not operational RCA. Overlap: a citation is not automatically
    valid support. Difference: DiagPriv's semantic paths are hand-specified
    for incident mechanisms. **Implication:** position evidence support as an
    incident-specific adaptation of a broader grounding concern.
13. **`gardner2020contrast` — local decision-boundary controls.**
    [Findings paper](https://aclanthology.org/2020.findings-emnlp.117/)
    perturbs examples to inspect local model decision boundaries across NLP
    tasks. Privacy mechanism: not evaluated. Utility: robustness of task
    predictions under meaning-changing perturbations, not RCA. Overlap:
    controlled target/twin logic. Difference: Incident 003 varies a causal
    temporal relation in operational evidence. **Implication:** cite
    methodological ancestry; pairing itself is not unprecedented.
14. **`chu2024timebench` — LLM temporal reasoning.**
    [ACL paper](https://aclanthology.org/2024.acl-long.66/) evaluates
    multiple temporal-reasoning categories in LLMs. Privacy mechanism: not
    evaluated. Utility: temporal question performance, not cloud diagnosis.
    Overlap: motivates explicit temporal-relation testing. Difference:
    Incident 003 asks about a specific operational failure mechanism after a
    representation transform. **Implication:** do not frame the family as a
    general temporal-reasoning benchmark.

Other bibliography entries have narrower contextual roles:
[`berg2020impact`](https://aclanthology.org/2020.louhi-1.1/) and
[`bencheikhlarbi2023clinical`](https://aclanthology.org/2023.eacl-srw.11/)
establish downstream de-identification tradeoffs;
[`pasch2025balancing`](https://aclanthology.org/2025.privatenlp-main.3/)
tests masking/pseudonymization for personal LLM writing;
[`ahmed2023recommending`](https://www.microsoft.com/en-us/research/publication/recommending-root-cause-and-mitigation-steps-for-cloud-incidents-using-large-language-models/)
provides large-scale cloud incident recommendations. The
[NIST PII guide](https://csrc.nist.gov/pubs/sp/800/122/final),
[HMAC RFC](https://www.rfc-editor.org/info/rfc2104/), and
[NIST FPE recommendation](https://csrc.nist.gov/pubs/sp/800/38/g/upd1/final)
are definition/context sources, not evidence that DiagPriv's baselines give
anonymity or cryptographic FPE.

## Compact novelty matrix

“Pre-release” means transformation before an external inference service.
“Task structure” means explicitly preserving a downstream relation, not
merely preserving fluent text. “Exposure” means measured model-visible
residue, not an inferred privacy guarantee.

| Work | LLM/RCA | Pre-release privacy transform | Task-specific structure | Downstream RCA utility | Residual representation exposure | Paired causal control |
| --- | --- | --- | --- | --- | --- | --- |
| EmojiPrompt | no / LLM inference | yes | partial (task information) | not evaluated | partial (simulated attack, not vector) | not evaluated |
| Adaptive anonymization | no / LLM anonymization | partial (text release) | partial (task objectives) | not evaluated | partial (privacy metrics, not ModelView vector) | not evaluated |
| Tau-Eval | no / LLM text tasks | partial (evaluates anonymizers) | partial (task sensitivity) | not evaluated | partial (privacy metrics) | not evaluated |
| RedactOR | no / clinical LLM de-ID | partial (clinical release) | partial (consistent entities) | not evaluated | not evaluated | not evaluated |
| RCAgent | yes | no (local deployment) | partial (RCA evidence) | yes | not evaluated | not evaluated |
| RCACopilot | yes | not evaluated | partial (handler-collected signals) | yes | not evaluated | not evaluated |
| OpenRCA | yes | not evaluated | partial (telemetry relations) | yes | not evaluated | not evaluated |
| Cloud-OpsBench | yes | not evaluated | yes (evidence milestones) | yes | not evaluated | partial (matched replay, not a privacy ablation) |
| ALCE | no / LLM QA | not evaluated | partial (citation support) | not evaluated | not evaluated | not evaluated |
| DiagPriv (current) | yes | yes | yes (typed invariants) | yes | yes (literal/linkage/shape/time vector) | yes (selected synthetic family) |

The matrix is a characterization of inspected evaluations, not a proof of
absence across the field. In particular, task-aware anonymization and
evidence-grounded RCA each substantially overlap DiagPriv's framing.
No reviewed work was verified to evaluate the entire six-part DiagPriv
combination, but no priority claim follows from this finite search.

## Specific claim decisions

| Proposed statement | Verdict | Safe manuscript treatment |
| --- | --- | --- |
| A. “Prior LLM de-identification typically focuses on removing sensitive entities...” | **Too broad** | RedactOR preserves consistent substitutes; Yang, Tau-Eval, and adaptive anonymization measure downstream utility. Say only that our selected operational tasks require explicitly typed causal relations. |
| B. “Operational RCA generally evaluates performance without measuring residual exposure.” | **Partially supported; too broad as universal claim** | The inspected operational benchmarks report RCA/process metrics, while RCAgent explicitly addresses privacy via local hosting. State the exact comparison, not “RCA ignores privacy.” |
| C. “Matched temporal target/twin evaluates loss of one causal representation property.” | **Supported as a design description, not an outcome proof** | Explain what is held constant and that unexpected model success remains possible. Cite contrast sets and temporal reasoning context. |
| D. “The paper separately evaluates RCA labels, evidence support, and representation exposure.” | **Supported descriptive claim, not unique** | Keep as a statement of this implementation. Cloud-OpsBench and ALCE already separate answer from support; Tau-Eval has multiple privacy/utility outcomes. |

## Boundary and remaining risk

- `format-preserving-v1` is deterministic character-class-preserving
  pseudonymization, **not** NIST FF1/FF3 cryptographic FPE.
- HMAC removes literal identifiers but preserves deterministic linkage in its
  scope. Relative-time conversion can remain vulnerable to known anchors.
- The exposure vector is not re-identification probability, anonymity,
  differential privacy, compliance, or provider security.
- The current implementation does **not** select transformations
  automatically. Adaptive anonymization is prior work; any future planner
  claim needs a separate implementation and comparison.
- The closest novelty concern is the combination of task-sensitive
  anonymization (Loiseau/Yang), pre-cloud obfuscation (EmojiPrompt), and
  evidence-grounded RCA (Cloud-OpsBench/RCAgent). The manuscript therefore
  claims only a bounded, controlled operational-evidence measurement design.
