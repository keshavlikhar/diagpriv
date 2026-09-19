# RFC: paired, repeated, and multi-model statistical analysis

Status: proposed for issue #25; requires protocol freeze before prospective use.
No provider calls, new experiment execution, or validation/held-out inspection
were performed for this RFC. Existing pilots and frozen scores keep their
original descriptive interpretation.

## Population, estimands, and units

The target population is future synthetic constructions sampled under explicitly
versioned generators, nuisance distributions, and task definitions. It is not
production incidents. Families and models are prespecified fixed strata: three
families are insufficient to estimate a population of all incident families.

An observation key is `(family, generator_version, construction_seed, query_role,
condition, model_configuration, trial_index)`. Construction is the independent
sampling unit within a family. Target and temporal twin share one construction;
repeated calls, conditions, roles, and models from it stay in one cluster.
The same numeric seed in two generators is not automatically a matched incident.
Verify independence assumptions and nuisance-template balance before sampling.

Let Y_icmrt be a binary endpoint for construction i, condition c, model m,
role r, trial t, and A_icmrt indicate a valid parsed response. Use separately:

- exact five-dimensional RCA;
- each of outcome, trigger, subsequent action, mechanism, and component;
- evidence-supported under the prospectively frozen evidence protocol;
- exact RCA AND evidence-supported as an explicitly named joint endpoint.

Do not pool v2 exact-ID support with v3/v4/v5 semantic support as the same
measure. Registry entries must freeze the family-specific scorer/evidence
versions. PR #28's candidate evidence v5 needs its own approval; it does not
replace frozen v4 results through this plan.

Primary scientific estimand: within each prespecified family/model, the paired
risk difference in exact RCA between condition c and comparator b for the
jointly observed cases. Report the population of jointly valid cases explicitly;
this conditional estimand need not represent all scheduled calls.

With complete data, first compute
`d_i = mean_r(mean_t(Y_icmrt - Y_ibmrt))`, with equal role and trial weights,
then `Delta = mean_i(d_i)`. Positive Delta favors c. Repetitions estimate
within-construction response variability; they do not multiply the number of
independent constructions. Never select the best repetition.

Prespecify raw as a utility reference, temporal ablation as a negative control
where applicable, and any privacy-matched comparator using the exposure RFC.
The primary contrast family must name all tested models, incident families,
conditions, and endpoints before outcomes are seen.

## Paired roles and repeated calls

For Incident 003 v3 report target and twin exact/mechanism accuracy separately,
their equal-weight average, and the proportion of paired roles both correct on
the same trial index. Report the two mechanism labels together to distinguish
correct discrimination from giving the same answer to both questions. The
pair-level joint endpoint is secondary, clustered by construction.

Trial index matches scheduling blocks, not necessarily shared provider
randomness. Fix R before execution; proposed planning default is R=3. Randomize
condition/model call order within balanced construction blocks using an analysis
seed distinct from construction seeds; record time blocks and model versions.
Use a fresh context for each call. Do not carry one answer into another role.

Report all repetitions, construction-level means, within-construction
disagreement, and between-construction spread. Model comparisons use matched
constructions; model versions/configurations are fixed effects, not independent
replicates. A changed provider-returned version starts a separate stratum or
triggers the preregistered pause rule.

## Failures, missingness, and denominators

Keep the full planned grid and distinguish not attempted, transport failure,
rate limit, refusal, malformed/missing-field output, unknown category, and
valid diagnosis. Show planned, attempted, returned, parsed, and scoreable counts.
Provider/parser failures are infrastructure/response-validity outcomes; their
RCA label is missing, not an incorrect diagnosis.

For the conditional paired estimate, retain only trials with A_c=A_b=1. Within
each role average over those matched trials; include a construction in the
equal-role primary estimate only if every planned role has a matched trial.
Report excluded constructions, available trial counts, and marginal valid-case
rates, so this selection is visible. If none qualify, report not estimable.
Use the original weights in the full-data estimand for missingness bounds.

For every planned comparison, bound each missing Y in [0,1]. If Y_c is absent
and Y_b=y is observed, its difference is [-y,1-y]; if both are absent it is
[-1,1]. Average these lower/upper differences using the planned construction,
role, and trial weights. These are identification bounds, not confidence
intervals. Add sampling uncertainty to each bound in the cluster procedure.

Separately report operational yield: valid AND correct responses divided by
planned slots, and completion/parse rates. Label it as delivered diagnostic
yield, never as model accuracy with failures relabeled incorrect.

No automatic retries or replacement of valid/invalid outcomes. A separately
approved recovery creates a new provenance-linked sensitivity dataset. Present
original and recovery analyses side by side; original failures remain in the
primary ledger. Prespecify missingness sensitivity scenarios rather than assume
missing-at-random. Proposed review trigger: over 5% unscoreable planned slots in
any condition/model/family, or over 5 percentage points imbalance between paired
conditions; retain results but pause confirmatory interpretation.

## Uncertainty and tests

For the planned large-construction study, bootstrap entire construction clusters
within each family, retaining every condition/model/role/trial and its
missingness mask. Proposed default: 10,000 draws, a frozen analysis RNG seed,
and percentile 95% intervals for paired risk differences and bounded continuous
evidence metrics. Recompute the conditional estimator inside each draw.
If resamples frequently have no eligible clusters or zero variance, flag the
interval as unreliable rather than interpreting a degenerate interval as proof.
Freeze fallback handling and assess interval coverage in synthetic analysis
simulations before using this for confirmation.

Resample each family's clusters independently for an equal-family macro
average; report family-specific results alongside it. A macro average describes
these fixed families. Do not bootstrap three family labels and claim broad
cross-family generalization. Model comparisons reuse identical sampled clusters
to retain paired dependence.

For the special case of one binary endpoint per independent construction and
one call/role, report the discordance table (both correct, c-only, b-only,
neither) and an exact conditional binomial test on discordant pairs. With zero
discordance report no observed difference and no evidence of equivalence. The
ordinary [McNemar test](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/mcnemar.test.html)
addresses paired categorical symmetry; treating repeated calls or twins as
independent rows would violate this plan. R's documented routine uses a
chi-squared approximation; the proposed exact sparse-table variant instead
tests c-only among discordances with probability 1/2.

For clustered primary mean-difference tests, propose a construction-level
studentized mean statistic with a t reference (df = eligible clusters - 1),
subject to pre-freeze null calibration simulations. No confirmatory claims if
calibration fails or sampling assumptions are indefensible. A mixed-effects
logistic model with construction intercepts and fixed family/model/condition
terms can be a sensitivity analysis, with convergence diagnostics and marginal
risk differences. It is not a substitute for independent sample size.

## Multiplicity and interpretation

Freeze one primary endpoint (exact RCA), comparator set, family set, and model
set. Apply Holm adjustment at family-wise alpha=0.05 across their entire planned
primary contrast family. Missing/unestimable tests remain in the declared
family with no rejection, not removed to reduce multiplicity. The
[R statistics documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html)
describes Holm's family-wise control; that method does not correct invalid
underlying tests or post-hoc endpoint selection.

Report unadjusted effect intervals as estimation intervals, clearly labeled;
they do not inherit family-wise coverage from adjusted p-values. If simultaneous
intervals are required, freeze a Bonferroni confidence level or a calibrated
joint cluster procedure. Per-dimension, evidence, pair-discrimination, and
model-interaction results are descriptive secondary analyses unless separately
included in a preregistered confirmatory family. Do not use non-significance to
claim equality. A non-inferiority margin needs substantive justification and
its own prespecified one-sided analysis, not a margin chosen after results.

## Sample-size rationale

The current 4-, 5-, 8-, and 10-case pilots do not supply inferential sample sizes.
Several template-selected seeds and repeated calls cannot establish a new
independent incident population. Do not estimate power from their apparent
perfect accuracy alone.

For a single binary pair, let q be discordance probability and delta the risk
difference. `Var(Y_c-Y_b) = q - delta^2`. A planning approximation for a two-sided
95% interval half-width h is `n >= 1.96^2 * q / h^2` near delta=0.

| Assumed q (planning only) | n for h=0.10 | n for h=0.05 |
|---:|---:|---:|
| 0.10 | 39 | 154 |
| 0.25 | 97 | 385 |
| 0.50 | 193 | 769 |
| 1.00 (worst variance bound) | 385 | 1537 |

These are independent constructions, not calls; normal approximations can be
poor when discordances are sparse. With a 0.10 target effect, q=0.50, alpha=0.05,
and 80% power, the rough formula `(1.96+0.84)^2*q/0.10^2` gives 392 constructions
before multiplicity, attrition, or dependence adjustments.

Propose 200 independent constructions per family as a planning floor for a
broad descriptive study, not a guaranteed powered confirmatory design. Set the
final N using simulations spanning q, template clustering, role correlation,
call variability, missingness, effect sizes, and the actual multiplicity family.
Repeated calls should never be used to claim N constructions when there are
only N/R. If the generator cannot produce the required independent diversity,
revise the research design rather than inflate call count.

Call budget is `sum_f N_f * roles_f * conditions_f * models_f * R_f`; approve it
separately. Broader seed allocation requires a new protocol because existing
registries intentionally restrict eligibility. No new seeds are selected here.

## Planned outputs and graduation gate

Produce: a full attempt/parse/failure flow table; family/model/condition outcome
tables with denominators; paired difference forest plots; target/twin confusion
and joint-correctness tables; repeat variability plots; exposure-versus-utility
plots inside declared envelopes; and missingness-bound/recovery sensitivity
tables. Record generator, prompt, scorer, evidence, transformation, provider,
and analysis versions plus all deviations.

Proposed development-to-validation gate: reproducible offline software and
artifact checks; no unresolved label/position shortcut; human baseline pilot
adjudication complete; frozen exposure metrics; calibrated analysis simulations;
approved N/R/model/seed allocation and failure thresholds; protocol freeze before
any validation construction. Prior observed cases are development history, not
fresh validation. Final held-out use requires its own later authorization.

Team decisions remain: the practically meaningful effect or margin; final
family/model/condition set and weights; scoring/evidence versions; acceptable
failure imbalance; primary test calibration; interval type; multiplicity family;
sample size/cost; and reviewer agreement/ambiguity thresholds. This RFC supplies
defaults to review, not approved experiment settings.
