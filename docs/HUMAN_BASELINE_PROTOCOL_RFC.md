# RFC: human RCA baseline and inter-rater review

Status: proposal for issue #26. No recruitment, participant contact, study,
provider call, or validation/held-out inspection is authorized or performed by
this RFC. Proposed thresholds and reviewer instructions require team review.

## Study question and unit

Can independent reviewers identify the five RCA dimensions and cite a sufficient
visible causal explanation on synthetic development evidence? Where do reviewers
agree with each other, where do they agree with a frozen oracle, and where is
the item or taxonomy ambiguous? Human consensus and oracle accuracy are separate
outcomes; neither establishes that a benchmark represents production work.

One review unit is a single ModelView/question under one condition and one
frozen taxonomy/evidence protocol. A construction may supply paired target and
temporal-twin questions, but those are correlated units. Maintain construction
IDs in the local assignment ledger, not reviewer-visible hidden-role labels.

Use only development cases. Validation/held-out data and retired seeds are
excluded from recruitment materials, training, pilot, and adjudication. Describe
the pilot as development calibration; do not present reviewed cases later as
fresh evidence of generalization.

## Reviewers, eligibility, and assignment

Propose six reviewers with at least one year of hands-on distributed-system,
backend, observability, or incident-response work, or equivalent documented
graduate training and practice. Record experience bands rather than employer
identity. Record prior exposure to DiagPriv; benchmark authors and people who
have read the item oracles cannot be blinded primary raters. They may serve as
disclosed method advisers after independent ratings are locked.

Each item receives three independent ratings. Assign with a recorded random seed,
balanced across reviewer experience and family. A reviewer sees at most one
question/condition from a construction, including across sessions, so seeing a
twin or raw version cannot reveal another version's answer. Target/twin items
go to disjoint reviewer sets. Do not allow reviewers to choose easy cases or
exclude cases after seeing answers.

## Reviewer packet and blinding

Expose only the ModelView and the appropriate frozen taxonomy handbook. Remove
experiment paths, seed, family/hidden-role names, oracle, annotations, invariants,
expected evidence, scorer-selected paths, prior provider answers, and results.
Use a random study item ID in the wrapper and retain original evidence IDs
inside the view for citation. Preserve view bytes and record the input hash
locally; do not silently sanitize the research evidence itself.

Every reviewer of the same item gets identical definitions. For existing v2
items use the frozen v2 prompt taxonomy; for v3 items use the frozen v3 prompt
definitions and precedence rules. Training includes general use of the answer
form and a separately authored non-study synthetic example, with a frozen
script. Do not give extra family-specific causal hints. A richer future human
handbook requires versioning and disclosure when comparing humans with models.

Reviewers are blind to expected labels, model performance, hypotheses about
method rankings, and assignment role. They cannot be fully blind to visible
masking (tokens or relative timestamps); record this limitation and do not claim
double-blinding. Assignment and analysis staff remain separate where feasible.

## Procedure and tooling

Allow 20 minutes per item as a proposed pilot limit, with visible timer and a
time-limit flag on submission. Record actual time and any unfinished fields;
do not silently extend difficult cases. The tool permits local search, sorting,
calculator use, and an offline timeline scratchpad. It must preserve original
evidence and cite original IDs, log tool usage at the action/category level,
and make no external requests. No LLM, web search, shared notes, repository
access, or communication with other raters during independent review.

Provide accessibility accommodations and planned breaks without tying pay to
speed or correctness. Record changed time/tool accommodations for interpretation.
Reviewers may stop or abstain; missingness and abstention must remain visible.
Recruitment, consent, compensation rate, retention period, participant access,
and applicable institutional ethics review must be resolved before recruitment.
Use synthetic cases only, minimize participant identifiers, store the contact
mapping separately, and publish aggregate reviewer characteristics. Do not
promise a study is exempt from review on the basis of synthetic evidence alone.

## Reviewer instructions (proposed verbatim packet text)

> Diagnose the operation named by the troubleshooting question using only the
> supplied evidence. Select one label for each RCA dimension, or mark that
> dimension "insufficient evidence" or "ambiguous between listed alternatives."
> Distinguish the trigger, subsequent action, mechanism, and component owning
> the failure. Use the supplied taxonomy rules. Do not assume an unshown event
> occurred. For each causal claim, cite every visible record needed to establish
> it and describe the relation they establish. Mention contradictions and missing
> information. A plausible story without cited support is not sufficient.
> Submit your own answer before discussing the item with anyone else.

## Answer form and citation procedure

Proposed fields:

```text
study_item_id; handbook_version; start_time; end_time; time_limit_reached
observed_outcome: label | insufficient | ambiguous
trigger: label | insufficient | ambiguous
subsequent_action: label | insufficient | ambiguous
failure_mechanism: label | insufficient | ambiguous
affected_component: label | insufficient | ambiguous
alternatives_by_dimension: [label, cited rationale]
causal_claims: [{claim, evidence_ids[], relation, subject_binding}]
contradictions: [{claim, evidence_ids[]}]
missing_information: free text
evidence_sufficiency: sufficient | insufficient | ambiguous
confidence: 0..100 (secondary self-report)
tool_categories_used[]; optional accessibility/deviation flag
```

This is a study form, not a change to the model response schema. The local
scoring adapter must explicitly map valid labels and the union of cited IDs to
the existing scorer; abstention is reported separately and never coerced into
a canonical label. Preserve per-claim citation structure for human analysis.

The form validates that IDs exist but does not reveal expected IDs, score, role,
or whether the answer is correct. A cross-record claim must bind the records to
the questioned operation. An overlap claim needs both start/end endpoints for
both intervals; ordering needs the relevant events and direction. Permit either
structured rows or lifecycle logs when the visible facts support the claim.
Human adjudication of an alternative proof is recorded separately from the
frozen scorer outcome; it cannot silently expand that scorer's acceptable paths.

## Agreement and accuracy reporting

Calculate all agreement from locked independent ratings before adjudication.
Report counts of missing submissions, time limits, insufficient/ambiguous
answers, and valid labels by dimension, family, condition, and experience band.

For three complete raters on item i and category counts n_ik, item pair
agreement is `P_i = sum_k n_ik(n_ik-1)/(3*2)`. Macro-average P_i over items,
then cluster uncertainty by construction so twins remain paired. Treat
"insufficient" and "ambiguous" as explicit categories; alternative-label sets
are additional descriptive data, not multiple votes. Missing submissions are
not abstentions. Report agreement on complete triplets with its denominator and
available-pair agreement as a missingness sensitivity analysis.

Propose nominal Fleiss kappa for three-rater complete triplets:
`kappa = (mean(P_i)-sum_k p_k^2)/(1-sum_k p_k^2)` with pooled category proportions
p_k. Report observed agreement alongside it; prevalence can make kappa unstable
or undefined. If the denominator is zero, say undefined rather than perfect.
The [irr package reference](https://cran.r-project.org/web/packages/irr/irr.pdf)
documents the multi-rater nominal Fleiss coefficient; its default missing-data
handling must not silently replace the explicit denominators above.
For pilot-size data, agreement estimates are descriptive; do not use a narrow
asymptotic interval or threshold as a significance claim. Later uncertainty
should resample construction clusters, retaining all their raters and roles.

For supporting evidence, report pairwise ID-set Jaccard, invalid-ID rate,
subject-binding agreement, and semantic agreement on the submitted claims.
Two empty citation sets yield undefined Jaccard, not a perfect supported answer.
Different valid proofs can have low ID overlap, so Jaccard is not evidence
sufficiency. Freeze a separate human claim-coding guide before scoring the pilot.

Report individual exact/per-dimension oracle accuracy and frozen evidence
support separately from inter-rater agreement and adjudicated sufficiency.
Do not compute primary accuracy from a consensus answer: it conceals independent
disagreement and gives humans an extra adjudication advantage over model calls.

## Adjudication and ambiguous items

Lock and hash independent forms, assignments, and all input versions first.
Two adjudicators review anonymized rationales and evidence without model
outputs. First assess whether each explanation follows from the visible facts;
only then compare with the frozen oracle and requirement set. Preserve original
answers, decision rationale, dissent, and the version of every guide used.
Disagreement between adjudicators goes to a third reviewer; unresolved cases
remain unresolved rather than forced into an oracle label.

Prespecified flagging triggers: no 2-of-3 agreement in any dimension; at least
two insufficient/ambiguous responses; or one reviewer identifying a concrete
missing premise, contradicted oracle, or incompatible-but-supported explanation.
Flagging is a request for adjudication, not automatic exclusion.

Declare an item **ambiguous** only when adjudicators can exhibit at least two
incompatible canonical answers supported by the same visible facts under the
same handbook, with no applicable precedence rule resolving them. Declare it
**insufficient** when a required discriminating fact is absent/unavailable and
the submitted counterexample explains why the remaining evidence cannot decide.
Incorrect participant reasoning or mere disagreement is not sufficient for
either declaration. Record **taxonomy ambiguity**, **evidence insufficiency**,
**reviewer error**, **scorer path mismatch**, and **unresolved** separately.

Do not delete flagged cases from the primary report or revise completed
observations. Any benchmark/scorer repair requires a new version and separate
review; the human finding becomes prospective design evidence only.

## Development pilot and acceptance

Propose six development constructions per family (18 total). Family 003 supplies
both roles, giving 24 raw query items. Three ratings per item gives 72 ratings;
six reviewers receive 12 each (about four hours at the maximum time, plus
training/breaks). This is a feasibility pilot, not a powered human/model contest.
Select constructions using a content-independent, recorded rule from an approved
development-only pool; freeze the list before reviewing answers. No seed list
or generated cases is created in this RFC.

Pilot raw evidence first to assess sufficiency. A later matched privacy study
requires additional reviewers or disjoint assignments that preserve the
one-construction-per-reviewer rule, plus a separate sample-size/condition plan.
Do not show a reviewer raw first and masked later and interpret the difference
as independent diagnostic utility.

Proposed progression criteria: complete traceable packets and three independent
ratings per item; no oracle leakage or external-tool use; at least 90% submission
completion; every ambiguity flag adjudicated or explicitly unresolved; and a
documented decision on timing, handbook clarity, and reviewer eligibility.
Low agreement triggers protocol review, not oracle relabeling. Freeze numerical
agreement targets only after feasibility review and before the subsequent study.

Review dependencies: [statistical plan](STATISTICAL_ANALYSIS_PLAN_RFC.md),
[experiment protocol](EXPERIMENT_PROTOCOL.md), and
[RCA v3 methodology](RCA_V3_METHODOLOGY.md). Reviewer count, selection rule,
compensation, ethics/consent, retention, timing, coding guide, and graduation
thresholds remain explicit team decisions.
