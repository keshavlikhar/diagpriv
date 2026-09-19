# Incident 003 v3 Paired Provider Qualification Protocol

## Status and purpose

This document preregisters an offline-prepared, development-only provider
qualification for Incident 003 v3. No provider observation exists at this
checkpoint. The qualification asks whether GPT-5.6 Sol changes its mechanism
diagnosis appropriately when the queried subject changes over identical
underlying evidence.

This is a qualification with four underlying constructions, not an inferential
study. It cannot establish statistical significance, population accuracy,
external validity, held-out performance, or cross-model generality.

The raw Stage-1 observation is now executed and frozen under evidence-support-v4.
Its evidence-support-v5 rescore is post-hoc/secondary. The originally prepared
v11 relative-time config remains a historical preparation artifact; the
prospective Stage-2 evidence-v5 amendment is separately versioned in
`docs/INCIDENT_003_V3_STAGE2_EVIDENCE_V5_PROTOCOL.md`. At this historical v11
preparation checkpoint, Stage 2 and Stage 3 had not been executed. Stage 2 was
subsequently executed under v12/v5 (see
`docs/INCIDENT_003_V3_STAGE2_RELATIVE_RESULTS.md`). Stage 3 was subsequently
prepared under prospective v13/v5 and executed after separate authorization
(see `docs/INCIDENT_003_V3_STAGE3_EVIDENCE_V5_PROTOCOL.md` and
`docs/INCIDENT_003_V3_STAGE3_ABLATION_RESULTS.md`); it does not inherit this
historical v11/v4 evidence protocol.
Nothing in this historical v11 protocol is silently
reinterpreted as a v5 provider observation.

## Frozen benchmark and evaluation versions

- family: `incident_003_temporal_compensation_v3`;
- generator: `incident-003-generator-v3`;
- temporal protocol: `incident-003-temporal-protocol-v3`;
- role-neutral anchor allocation:
  `incident-003-v3-role-neutral-anchor-allocation-v1`;
- paired query protocol: `incident-003-v3-paired-query-v1`;
- evidence requirements: `incident-003-v3-evidence-requirements-v2`;
- semantic evaluator: `incident-003-v3-evidence-semantic-evaluator-v2`;
- taxonomy: `rca-taxonomy-v3`;
- prompt: `raw-rca-v3`;
- scorer: `raw-rca-scorer-v3`;
- evidence protocol: `evidence-support-v4`;
- manifest: `raw-rca-manifest-v11`.

The frozen prompt-template SHA-256 is
`a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`.

## Deterministic construction selection

For every integer seed from 1200 through 1399, compute
`SHA256("incident-003-v3-paired-qualification-v1|" + decimal_seed)`, sort by
the hexadecimal digest, and select the first four. No construction content is
inspected by this rule.

| Rank | Seed | Selection digest |
|---:|---:|---|
| 1 | 1319 | `01158f484f822ae5eebd6efeb12f038dfa5f8475b4d4dc48f6094e7f24f2c7d4` |
| 2 | 1299 | `01479aadecf2a505bab788b7fb410255257af0416094e2ade4bd7787c7a17de1` |
| 3 | 1387 | `0309d5c21954a9ea8b06358c1f4cccad9256f88daf0f0ede0444a729bd1b6966` |
| 4 | 1222 | `04b22773b02d9c607e3ec290259ac51250268ce373cde8a2ef9a47b336d5b447` |

Each construction yields two stable cases:

- `1319:target`, `1319:temporal_twin`;
- `1299:target`, `1299:temporal_twin`;
- `1387:target`, `1387:temporal_twin`;
- `1222:target`, `1222:temporal_twin`.

Manifest v11 persists `construction_seed`, `query_role`, and `case_id` so a
runner cannot collapse paired observations by seed.

## Paired oracle

Both roles use outcome `inconsistent_state`, trigger `timeout_or_deadline`,
action `compensation_or_rollback`, and component `workflow_orchestrator`.
Only the mechanism differs:

- target: `incorrect_concurrency_control`;
- temporal twin: `incorrect_state_transition`.

The two query cases share exactly equal structured evidence, log evidence,
timestamps, identifiers, row/list ordering, messages, aliases, and serialized
evidence. The model-facing question changes only the queried operation ID under
the same normalized template. Query-role metadata and oracle information are
not model-visible.

## Matched conditions and provider settings

The three separately authorized stages are:

1. raw;
2. `relative-time-v1`;
3. `temporal-ablation-v1`.

Each stage contains eight observations and uses GPT-5.6 Sol, medium reasoning,
temperature omitted, one call per case, no automatic retries, `raw-rca-v3`,
`rca-taxonomy-v3`, `raw-rca-scorer-v3`, and `evidence-support-v4`. Only the
transformation differs.

Canonical transformation-configuration hashes are:

| Condition | SHA-256 |
|---|---|
| raw | `46fd3d729eb1ac237017c93fc5795004c012f16dcc382035217492a4f7c097c7` |
| `relative-time-v1` | `cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660` |
| `temporal-ablation-v1` | `fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b` |

## Frozen model-input hashes

| Seed | Query role | Case ID | Raw | Relative time | Temporal ablation |
|---:|---|---|---|---|---|
| 1319 | target | `1319:target` | `a8929b46726e39b9718c61e3d3f1f83ddf8ad464c5a0e02e1d58f529a26120ba` | `a5bd805e6f4db8cb22c6bcdf160f82446aaa4de9900b545db75aac458063c765` | `a14a79f2c923e8a674ca5f6e88c07434841eadec509a8f457d5bf2428963037e` |
| 1319 | temporal twin | `1319:temporal_twin` | `da4fecdb99bd4abcf1aa4eae885cb42193285809c340cf5a0da19bee0f1ebedc` | `1b83853f0f246341cfef515fbe870d703739492875bb5d11cae115461bf6c80f` | `ad9400cf344a34b91ed7a3f5c0125c9f1c2c9b59f5737db1f69fa5016b55b9ec` |
| 1299 | target | `1299:target` | `11ccc25e1e3bf652be68b9588b5b621b3b7daf605ac8d91f67761fd6ce419b0e` | `b7dc8a177cdaab04b7e1943de63337dd3ad8fbef3e62a06f8a6392388eb6a354` | `7d3bbafc8e003908f529259c9038e5e7e67c3c31ee6790c6a995d3b20ce1146b` |
| 1299 | temporal twin | `1299:temporal_twin` | `bae387d97e45c522f8c622c033219ed1aa84d4151b47520224c4d991df753c7b` | `bafb78e26c66d7e9e740c3e009f118222a7c5be6d33738e56814058bd3ca724c` | `7e8b263aff8e85d5bad358992001406bcdca87a9019370dff3b51d49552f2672` |
| 1387 | target | `1387:target` | `132a3f4c0fb7e6c3a4328cf72ef4bcbb9402ac92b0e69fa34c32b8a6caf3689f` | `976b254d1e471f073fe3265381f9de12c222055af542af7d21a9b507a24946f8` | `0a66accda0e5aaba981a743526914ae81f6d3f79d712e91fd5a3ea7b57a26f8c` |
| 1387 | temporal twin | `1387:temporal_twin` | `700e8a1741f74bb72a3613c72625c8b0e68b64ab2433c17a581161f3f12e7d63` | `401a2e3e5689cb39c554c3babbc847c64e3cfdb66f8c29dbd712399c1e3ab5d6` | `674aa91310a1b9185acf6e3c4276a69eb592d31320e7253d9420b2ae5f3dfcbb` |
| 1222 | target | `1222:target` | `d2013caefee68997ee260ee43c302064cb4de2ee4f8de1248459c294dffbd7b4` | `57134350497a57636869c19eb2938a491639d28f4f7481aa289fa6e9736193a7` | `854c91718478adfa302f187728dc4b5a356b5f366b25d7867e3aa3d770d45a4f` |
| 1222 | temporal twin | `1222:temporal_twin` | `1e9ede4cf15d07351d77c993eea5b1522aab819646e1abc28f2cb60abd84358d` | `5c90a29ed5d622b5912bda17f06f61ff997f0ef5bf35ef7e82a679167cff9bf2` | `49cb4c19fcac5eb9eaf388bb914d9abb6c7b77b3720973307fa7dc511f014c07` |

## Frozen evidence requirement hashes

The normative requirement set is condition-independent. Transformation changes
semantic satisfiability, not the requirement serialization.

| Case ID | Requirement-set SHA-256 |
|---|---|
| `1319:target` | `f38551a3a69f202d5d2ea20ade9ea8d313ec59ee5326569ddc5c8fd46e57a960` |
| `1319:temporal_twin` | `31a642035762394c6c6450c0f723377e98ece0ea3084fa90489a01ef5774cbbb` |
| `1299:target` | `af6869c94977daab9b2c3d9ec0a2880dbf110618278395bc64bb73c2a453db28` |
| `1299:temporal_twin` | `6dec6ed05bb8e8b295e143471938df86a795b7d0e60ba30e7de0c02a541daf0f` |
| `1387:target` | `8c55c686b0ac4f8423c1f036051e1f14aa419ee49ce9294b346b9b66d6573d73` |
| `1387:temporal_twin` | `1ae5e991546be665f6c1464697f40f6b69a22d6ea6cd4dd62f8c80394a41a60d` |
| `1222:target` | `73fad2b17cb64b29b6c2968c9b1caeabf3c70a7b0fe51ffbcfbbd0005f896a2f` |
| `1222:temporal_twin` | `ed8fa74336f55f4e22935828341c922a1a0934b299cf6dbdfbaae0578009ab63` |

With deterministic complete oracle citations, all four raw and all four
relative-time cases per role satisfy every essential, contrast, and supportive
requirement. Under temporal ablation, target cases retain only
`queried_identity_linkage` and `inconsistent_terminal_workflow_effect_state`;
the four temporal essentials are missing. Twin cases retain the same two
non-temporal essentials; their three temporal essentials are missing. Contrast
and supportive temporal requirements are also unsatisfied. Thus all eight
ablated cases are evidence-unsupported without weakening the rubric.

For all four selected constructions, the ablated target and twin inputs are
isomorphic after identifier normalization while their mechanism oracles
conflict. This is an offline identifiability property, not a claim about future
model behavior.

## Manifest v11 provenance

Manifest v10 cannot unambiguously represent two observations with the same
seed and different query roles. Append-only v11 retains all v10 provenance and
adds construction seed, query role, stable case ID, paired-query protocol,
anchor-allocation version, evidence-requirement version, and semantic-evaluator
version. Historical manifests are neither rewritten nor reinterpreted.

## Preregistered metrics

For each condition, report valid responses and exact five-dimensional RCA out
of eight, all five dimension accuracies, target mechanism accuracy out of four,
and twin mechanism accuracy out of four. Evidence reporting remains separate:
essential, contrast, and supportive coverage; useful citation precision;
invalid, wrong-subject, and redundant citations; `evidence_supported`; and
`overall_correct_v3`.

For each construction, `paired_mechanism_correct` requires target concurrency
and twin state transition. `paired_exact_rca_correct` requires both cases to be
exact RCA. Pair patterns are classified as correct flip, both concurrency,
both state transition, reversed, or one/both other.

The frozen directional expectation is:

`Raw paired discrimination ≈ Relative-time paired discrimination > Temporal-ablation paired discrimination`

No numeric pass/fail threshold is defined.

## Staged execution and failure policy

Stage 1 is raw (eight calls), followed by mandatory review. Stage 2 is relative
time (eight calls) only after separate authorization and review. Stage 3 is
temporal ablation (eight calls) only after another authorization. Commands do
not chain conditions. Wrong answers, malformed responses, refusals, rate
limits, and provider errors are preserved and are not automatically retried.

Result paths are unique, Git-ignored, and required to be absent before provider
initialization. Hash or protocol mismatch fails closed. Validation seeds
2000–2999 and held-out seeds 20000–20999 are forbidden.

## Interpretation limits

A correct role-sensitive mechanism flip under raw or relative time is
consistent with subject-specific temporal reasoning. Failure to distinguish an
ablated pair is consistent with removed temporal information being necessary
for the benchmark distinction. Apparent ablated success does not establish
recovery of hidden time; literal identifiers, chance, provider variability,
unsupported reasoning, and residual cues must be considered. Evidence-
support-v4 remains the guard against attributing unsupported temporal
reasoning.
