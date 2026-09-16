# Incident 003 `relative-time-v1` development findings

## Frozen status

This document freezes the completed matched development comparison between raw
Incident 003 v2 evidence and `relative-time-v1`. The transformed condition was
executed exactly once after PR #14 merged. Neither raw nor relative time may be
rerun under these experiment identifiers, and neither JSONL may be edited.

| Item | Frozen value |
|---|---|
| Merged implementation commit | `2674866c494ec893cf6d48a9e35110fb727d9ff1` |
| Relative-time result | `results/incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl` |
| Relative-time result SHA-256 | `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb` |
| Raw baseline SHA-256 | `54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915` |
| Transformation-configuration SHA-256 | `cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660` |
| Prompt-template SHA-256 | `a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139` |

Both result files are ignored, local, append-only research artifacts. Hashes,
not JSONL contents, are committed for collaboration-safe verification.

## Frozen protocol

- model: `gpt-5.6-sol`;
- reasoning effort: `medium`;
- temperature: omitted;
- calls per seed: one;
- seeds: 1019, 1020, 1021, 1022, 1023, 1025, 1026, and 1028;
- manifest: `raw-rca-manifest-v10`;
- generator: `incident-003-generator-v2`;
- incident protocol: `incident-003-temporal-protocol-v2`;
- transformation: `relative-time-v1`;
- temporal semantics: `relative-time-semantics-v1`;
- taxonomy: `rca-taxonomy-v3`;
- prompt: `raw-rca-v3`;
- scorer: `raw-rca-scorer-v3`;
- evidence protocol: `evidence-support-v3`.

Validation and held-out seed lists were empty. No destructive temporal privacy
condition was run as part of this experiment.

## Primary matched result

| Metric | Raw | Relative time |
|---|---:|---:|
| Valid responses | 8/8 | 8/8 |
| Exact five-dimensional RCA | 8/8 | 8/8 |
| Observed outcome | 8/8 | 8/8 |
| Trigger | 8/8 | 8/8 |
| Subsequent action | 8/8 | 8/8 |
| Failure mechanism | 8/8 | 8/8 |
| Affected component | 8/8 | 8/8 |
| Evidence-supported | 0/8 | 1/8 |
| `overall_correct_v3` | 0/8 | 1/8 |

The exact-RCA matched contingency is:

| Raw | Relative time | Count |
|---|---|---:|
| correct | correct | 8 |
| correct | incorrect | 0 |
| incorrect | correct | 0 |
| incorrect | incorrect | 0 |

Every relative-time response selected the five-label tuple:

```text
inconsistent_state
timeout_or_deadline
compensation_or_rollback
incorrect_concurrency_control
workflow_orchestrator
```

No response selected `incorrect_state_transition`.

The supported research statement is deliberately narrow:

> On these eight fresh matched Incident 003 development cases with GPT-5.6 Sol, replacing absolute timestamps with exact incident-relative millisecond offsets preserved all five RCA dimensions.

This result does not establish statistical significance, validation or
held-out performance, behavior of other model families, preservation for all
operational incidents, anonymity, zero re-identification risk, or superiority
over destructive transformations. The destructive matched model conditions
have not yet run under the v3 protocol.

## Evidence comparison

| Metric | Raw | Relative time |
|---|---:|---:|
| Essential coverage | 19/48 = 0.395833 | 23/48 = 0.479167 |
| Contrast coverage | 0/16 | 0/16 |
| Supportive coverage | 2/40 = 0.050000 | 3/40 = 0.075000 |
| Useful citation precision | 0.837500 | 34/40 = 0.850000 |
| Invalid citations | 0 | 0 |
| Wrong-subject citations | 0 | 0 |
| Redundant citations | 0 | 0 |
| Evidence-supported | 0/8 | 1/8 |
| `overall_correct_v3` | 0/8 | 1/8 |

Relative-time secondary compatibility evidence precision was 0.8500, recall
was 0.4792, and F1 was 0.5830. These development differences are not evidence
of statistical significance. Citation completeness remains substantially
weaker than RCA-label accuracy: seven correct five-label diagnoses still did
not cite a complete preregistered essential path.

## Per-seed result

| Seed | Template | Raw exact | Relative exact | Relative essential coverage | Relative evidence-supported | Relative overall |
|---:|---|---:|---:|---:|---:|---:|
| 1019 | `tight_overlap` | yes | yes | 2/6 | no | no |
| 1020 | `delayed_compensation` | yes | yes | 3/6 | no | no |
| 1021 | `tight_overlap` | yes | yes | 3/6 | no | no |
| 1022 | `delayed_compensation` | yes | yes | 6/6 | yes | yes |
| 1023 | `wide_overlap` | yes | yes | 2/6 | no | no |
| 1025 | `short_overlap` | yes | yes | 2/6 | no | no |
| 1026 | `wide_overlap` | yes | yes | 3/6 | no | no |
| 1028 | `short_overlap` | yes | yes | 2/6 | no | no |

Seed 1021 retained genuine equality between execution completion and
compensation completion. Compensation started 6,000 ms before that shared
completion instant, so positive overlap remained. A late active effect and a
compensated workflow remained visible. The model correctly diagnosed the
causal chain despite the equal completion timestamps.

## Privacy interpretation

`relative-time-v1` removes calendar date, wall-clock time, timezone, epoch, and
RFC3339 representation. It intentionally preserves exact relative millisecond
offsets, ordering, equality, duration, gaps, overlap, deadline crossings, and
the incident-local temporal span.

> If an observer independently knows the absolute time of one transformed event, exact relative offsets can permit reconstruction of the absolute times of other events in the same transformed incident.

This is absolute-time removal, not complete temporal anonymization, proof of
anonymity, or proof of zero re-identification risk.

## Usage and cost

| Metric | Relative time |
|---|---:|
| Input tokens | 83,403 |
| Output tokens | 3,095 |
| Reasoning tokens | 1,522 |
| Total tokens | 86,498 |
| Estimated cost | $0.478891 |

For descriptive context, raw used 95,669 total tokens and cost an estimated
$0.520711. Relative time used 9,171 fewer total tokens, approximately 9.6%
fewer. Eight cases do not establish a general efficiency result.

## Frozen input and rubric provenance

All eight result records used manifest v10 and persisted the reviewed
transformation version, temporal semantics, shared-anchor rule, millisecond
precision, representation, annotation classification, scope policy, and
configuration hash. Every model-input and evidence-rubric hash matched its
preregistered value.

| Seed | Transformed model-input SHA-256 | Evidence-rubric SHA-256 |
|---:|---|---|
| 1019 | `606420ee8a2832b5e2ceee584ceb0c5133dec90785632d7ee1e28a8c32d23cda` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| 1020 | `ffff6212ea681333d391b0271635c91222c15b05d0f45daeb26b9e76f3939523` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| 1021 | `b70bf4170fc96755b1ad2e97e80f3c307edbdf0fbdbce61d4ec91336e4f0a8c0` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| 1022 | `782134836be932b1510abadd833a58437d56afaa5b56df715e6576e99012e90b` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| 1023 | `c9df2c0f54c9b99747f846d3414df86a7864570046b5ca258a89a0cce5fdfd9e` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| 1025 | `603990c45c51cfa4f28fb522404f73c9e0422a4436ab6d6a9d12fb74dc112723` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| 1026 | `4a62763f53e76517d7f4c30ce0861c3df081ad177250f05ff30681fc3a2ee40b` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| 1028 | `03426719e9173d5a562713673a602b588fb49f38e42f1b56c868f36ed51bbf6d` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |

## Next development comparison

The next documentation-stage goal is to test whether preserving temporal
diagnostic structure matters. Candidate matched conditions are:

- `temporal-ablation-v1`;
- `redaction-v1`;
- `hmac-v1`;
- `tokenization-v1`;
- `format-preserving-v1`.

`temporal-ablation-v1` is the strongest direct negative-control candidate
because it deliberately removes temporal semantics while leaving non-temporal
evidence intact. Any future run must use the same eight seeds and frozen
GPT-5.6 Sol/v3 protocol, receive separate review, and use new append-only
artifacts. No provider inputs or hashes for these future conditions are
preregistered by this documentation checkpoint, and none has been executed.
