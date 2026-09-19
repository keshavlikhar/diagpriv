# Incident 003 v3 Stage-3 prospective evidence-v5 preparation

Status: **offline preparation only**. Issue #38 starts from synchronized
`main` commit `74949bc3ccf54205c0177f728a0c4a31278291ee` after the Stage-2
results PR. Stage 3 has no provider observation or result JSONL. Execution
requires separate, explicit authorization after review of this preparation.

## Scientific question and frozen boundary

The descriptive development hypothesis remains:

`Raw paired discrimination ≈ Relative-time paired discrimination > Temporal-ablation paired discrimination`

This is not an acceptance test. An eventual contradiction must be retained and
reported, not repaired by editing the benchmark or scorer. Only four
constructions/eight paired cases are involved; no inferential statistical,
equivalence, or general privacy-method ordering claim follows.

Raw Stage 1 is frozen at JSONL SHA-256
`b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`:
8/8 valid, 7/8 exact RCA, 3/4 paired mechanisms and paired exact. Its primary
evidence protocol is **v4** (0/8 supported); its 3/8 v5 rescore is explicitly
post-hoc and secondary. Relative-time Stage 2 is frozen at JSONL SHA-256
`f020511aeb497eab8c4ca5da4487ed87e20c6fe5e8b37a56613eb521297536e4`:
8/8 valid, 6/8 exact RCA, 2/4 paired mechanisms and paired exact, 4/8
evidence-supported under **prospective v5**. Neither artifact is modified or
rerun here. Stage 2 versus eventual Stage 3 is the clean prospective
same-evidence-protocol comparison; Stage-1 v5 remains post-hoc.

## Frozen Stage-3 protocol

- Family `incident_003_temporal_compensation_v3`; generator
  `incident-003-generator-v3`; incident protocol
  `incident-003-temporal-protocol-v3`.
- Four constructions in order: `1319`, `1299`, `1387`, `1222`; both `target`
  and `temporal_twin` query roles, exactly eight development cases, one call
  per case. Paired query `incident-003-v3-paired-query-v1`; anchor allocation
  `incident-003-v3-role-neutral-anchor-allocation-v1`.
- Condition `temporal-ablation-v1`; transformation
  `incident-003-temporal-ablation-v1`; parser semantics
  `temporal-semantics-unavailable-v1`; canonical transformation-configuration
  SHA-256
  `fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b`.
  The exact canonical settings are `anchor_rule=not-applicable`,
  `precision=not-applicable`,
  `representation=unique-deterministic-nontemporal-marker`,
  `annotation_classification=operational_timestamp`, and
  `scope_policy=annotated-timestamps-plus-deterministic-log-reordering`.
- Prompt `raw-rca-v3`, prompt-template SHA-256
  `a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`;
  taxonomy `rca-taxonomy-v3`; RCA scorer `raw-rca-scorer-v3`.
- Evidence protocol `evidence-support-v5`; requirement constructor
  `incident-003-v3-evidence-requirements-v3`; semantic evaluator
  `incident-003-v3-evidence-semantic-evaluator-v3`. The existing v5 semantics
  are unchanged.
- Provider OpenAI Responses, requested model `gpt-5.6-sol`, medium reasoning,
  temperature omitted, `max_output_tokens=4096`, no retries or replacements.
- Prospective manifest `raw-rca-manifest-v13` is restricted to this Stage-3
  condition, frozen cases, all listed settings, exact transformation hash, and
  both per-case hashes. Historical v9/v10/v11/v12 validation and loading
  semantics are not broadened. In particular, v11 remains the historical
  evidence-v4 ablation preparation and v12 remains Stage 2 only.

The new config is
`experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development_v5.toml`.
Its file SHA-256 is
`4f700ea93821447d5972df317b16e1a1339989e601acb2325196d2a9477268c4`.
This **experiment-config file hash** is distinct from the canonical
**transformation-config hash**, each **rendered model-input hash**, and each
**resolved v5 requirement-set hash**. The latter two must match for every
case before provider initialization.

## Frozen per-case hashes

The input column is copied from the historical v11 paired qualification
freeze, then independently checked byte-for-byte under current main. No
expected input hash was regenerated after a mismatch. The v5 requirement
column was calculated once from the existing generic rubric resolved against
each selected incident and explicitly pinned in the new config and independent
tests. These rubric hashes equal Stage 2's because the requirement set is
transformation-independent; semantic satisfaction is not.

| Case ID | Frozen ablated model-input SHA-256 | Prospective v5 requirement-set SHA-256 |
|---|---|---|
| `1319:target` | `a14a79f2c923e8a674ca5f6e88c07434841eadec509a8f457d5bf2428963037e` | `c68aa89d9b9414a520435eea7f0830a4f7ce8e1e0b56fd09d5feaa995381593d` |
| `1319:temporal_twin` | `ad9400cf344a34b91ed7a3f5c0125c9f1c2c9b59f5737db1f69fa5016b55b9ec` | `745df9f32e9768c064a61dbce43d424dfbd62c544d62cd33c7d21c2f9cf775cd` |
| `1299:target` | `7d3bbafc8e003908f529259c9038e5e7e67c3c31ee6790c6a995d3b20ce1146b` | `832a09456766ee9fbdb5796327be33375190435b8db18a63b8af85587c3d2ca5` |
| `1299:temporal_twin` | `7e8b263aff8e85d5bad358992001406bcdca87a9019370dff3b51d49552f2672` | `9576f9e5271054daeb41dc6ef8e9654b4ec7a0630dbdcbacd89010b909874794` |
| `1387:target` | `0a66accda0e5aaba981a743526914ae81f6d3f79d712e91fd5a3ea7b57a26f8c` | `d5d6bee92d6db457153f8f97325ea295552b53330e8366f7fd7e0b692f415579` |
| `1387:temporal_twin` | `674aa91310a1b9185acf6e3c4276a69eb592d31320e7253d9420b2ae5f3dfcbb` | `189c2295b1b7eb69ad9d0c2b6f91cec864ff17b39f0466051a803fc31cdf5c09` |
| `1222:target` | `854c91718478adfa302f187728dc4b5a356b5f366b25d7867e3aa3d770d45a4f` | `6a6e4571351b6d726c65588e19f44bfd0d179ece291861b8071644a6c81c732b` |
| `1222:temporal_twin` | `49cb4c19fcac5eb9eaf388bb914d9abb6c7b77b3720973307fa7dc511f014c07` | `e09c002225b8e1bc35098e56682a66c4f74ac72c6c9c6e2cc2edb3edd60484a3` |

## Selected-case offline construction audit

For all four pairs, the existing leakage audit reports equal underlying and
serialized evidence, normalized question equality, canonical ablated
queried-subject isomorphism after identifier normalization, and conflicting
target-versus-twin mechanism oracles: **4/4** each. This is a construction
property, not a model result.

For each of the eight ablated ModelViews, the v5 evaluator explicitly uses
`temporal-semantics-unavailable-v1`. Even citing every visible evidence ID
cannot satisfy the target temporal essentials
`deadline_before_original_completion`, `compensation_after_deadline`,
`execution_compensation_overlap`, or `late_successful_original_effect`; for
twins, it cannot satisfy
`successful_execution_and_active_effect_before_deadline`,
`compensation_after_committed_success`, or
`serialized_execution_before_compensation`. Wrong-role and safe-control-only
citations do not substitute for those essentials in any selected case.
This audit does **not** impose a future `evidence_supported=false` acceptance
criterion. Actual model citations and the frozen scorer decide each future
score; unexpected success is a finding to investigate, not a reason to change
the benchmark after observation.

## Prospective report and result protection

The distinct `incident-003-v3-stage3-evidence-v5-report-v1` report records
planned/attempted/unattempted/valid coverage; exact and five RCA dimensions;
target and twin observed denominators against four planned each; paired exact
and mechanism correctness over complete valid pairs; and one frozen pair
pattern per construction. An incomplete or invalid pair is `unavailable` with
per-role status, never an ordinary wrong mechanism. Other exclusive patterns
are `correct_mechanism_flip`, `both_concurrency`, `both_state_transition`,
`reversed_mechanism_flip`, and
`one_or_both_other_valid_mechanism_labels`.

The report separately records v5 supported count, essential/contrast/
supportive coverage, useful citation precision, invalid and wrong-subject
citation counts, selected paths and missing essentials by valid case;
provider/parser/refusal/rate-limit failures; token totals, priced estimate
when available, and exact result SHA-256 after an artifact exists.

The proposed result path is
`results/incident_003_v3_temporal_ablation_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl`.
It is Git-ignored and untracked, absent during preparation, and must not be
created as a placeholder. The CLI requires `--execute`, checks the absent path
before provider setup, and dry-run verifies eight input/rubric hashes without
creating a JSONL. No provider call was made for this preparation.

For a separately approved future execution only:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development_v5.toml \
  --results results/incident_003_v3_temporal_ablation_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl \
  --execute
```

After that future run, the paired report would use `summarize-stage3-v5` with
the same config/result path and
`experiments/pricing/openai_gpt_5_6_sol_2026-09-10.toml`. Neither command was
executed with provider access during preparation.
