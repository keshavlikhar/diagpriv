# Incident 003 v3 Stage-2 Evidence-v5 Prospective Preparation

Status: **offline preparation only; no Stage-2 or Stage-3 provider observation**.
This issue #33 amendment is based on synchronized main
`7910bb27644d2291f90d8859be3a591d006747ae`. Execution requires a separate,
explicit approval after review of the preparation PR.

## Historical boundary and question

Raw Stage 1 is frozen at SHA-256
`b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`:
8/8 valid, 7/8 exact RCA, 0/8 evidence-supported under primary v4. The sole
mechanism-label miss is `1222:temporal_twin`. Applying v5 to those raw responses
yielded 3/8 evidence-supported **post hoc**, not a replacement for primary v4.

Stage 2 will be the first *prospective* use of evidence-support-v5, on the
previously frozen `relative-time-v1` ModelViews. The descriptive directional
hypothesis remains `Raw paired discrimination ≈ Relative-time > temporal
ablation`. This is not an acceptance criterion. With four constructions/eight
cases, matching outcomes cannot establish equivalence, inferential statistical
significance, or a universal ordering of privacy methods. A contrary result is
reported, not repaired by changing the benchmark. Stage 3 is not prepared or
executed by this amendment.

## Frozen execution protocol

- Family: `incident_003_temporal_compensation_v3`; generator
  `incident-003-generator-v3`; temporal protocol
  `incident-003-temporal-protocol-v3`.
- Constructions in frozen order: `1319`, `1299`, `1387`, `1222`; both `target`
  and `temporal_twin` queries, exactly eight cases, development only.
- Condition: `relative-time-v1` only. The existing transformation configuration
  hash, independently recomputed from canonical configuration, is
  `cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660`.
  Temporal parser semantics: `relative-time-semantics-v1`.
- GPT-5.6 Sol, medium reasoning, temperature omitted, `max_output_tokens=4096`,
  exactly one call per case; no automatic retries or replacement calls.
- Prompt `raw-rca-v3`, frozen prompt-template SHA-256
  `a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139`;
  taxonomy `rca-taxonomy-v3`; RCA scorer `raw-rca-scorer-v3`.
- Evidence protocol `evidence-support-v5`; rubric
  `incident-003-v3-evidence-requirements-v3`; semantic evaluator
  `incident-003-v3-evidence-semantic-evaluator-v3`. Paired query
  `incident-003-v3-paired-query-v1`; role-neutral anchors
  `incident-003-v3-role-neutral-anchor-allocation-v1`.
- Prospective manifest `raw-rca-manifest-v12`. It carries the existing v11
  provider, model, temperature, token, prompt, input, transformation, and
  paired-identity provenance plus v5's resolved requirement-set hash and
  evaluator version. V9/v10/v11 loaders and their permitted evidence protocols
  remain unchanged. V11 is not broadened to admit v5.

The new config is
`experiments/incident_003_v3_relative_time_v1_paired_sol_development_v5.toml`.
Its file SHA-256 at this checkpoint is
`4ae80dec27510e275ff82099a101b993dc3f8fdf846b660322ab6454b00d2af5`.
This **experiment-config file hash** is distinct from both the canonical
**transformation-config hash** above and the per-case **model-input hashes**
below. The config hash is a preparation artifact checksum, not a field in
historical manifests.

The proposed ignored, append-only result path is
`results/incident_003_v3_relative_time_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl`.
It is not created during preparation; overwrite protection and `--execute`
remain mandatory for any later real run. The old, unexecuted v11 relative-time
config is retained for historical review but is not the prospective v5 command.

## Frozen case hashes

The model-input column is copied from the preexisting v11 qualification
preparation, checked byte-for-byte under current main, and **not** regenerated
as a new expectation. The v5 requirement hashes were calculated once from the
resolved candidate v5 rubric and explicitly pinned in the new TOML and
independent tests. A mismatch aborts before provider setup.

| Case ID | Existing relative-time model-input SHA-256 | Prospective v5 requirement-set SHA-256 |
|---|---|---|
| `1319:target` | `a5bd805e6f4db8cb22c6bcdf160f82446aaa4de9900b545db75aac458063c765` | `c68aa89d9b9414a520435eea7f0830a4f7ce8e1e0b56fd09d5feaa995381593d` |
| `1319:temporal_twin` | `1b83853f0f246341cfef515fbe870d703739492875bb5d11cae115461bf6c80f` | `745df9f32e9768c064a61dbce43d424dfbd62c544d62cd33c7d21c2f9cf775cd` |
| `1299:target` | `b7dc8a177cdaab04b7e1943de63337dd3ad8fbef3e62a06f8a6392388eb6a354` | `832a09456766ee9fbdb5796327be33375190435b8db18a63b8af85587c3d2ca5` |
| `1299:temporal_twin` | `bafb78e26c66d7e9e740c3e009f118222a7c5be6d33738e56814058bd3ca724c` | `9576f9e5271054daeb41dc6ef8e9654b4ec7a0630dbdcbacd89010b909874794` |
| `1387:target` | `976b254d1e471f073fe3265381f9de12c222055af542af7d21a9b507a24946f8` | `d5d6bee92d6db457153f8f97325ea295552b53330e8366f7fd7e0b692f415579` |
| `1387:temporal_twin` | `401a2e3e5689cb39c554c3babbc847c64e3cfdb66f8c29dbd712399c1e3ab5d6` | `189c2295b1b7eb69ad9d0c2b6f91cec864ff17b39f0466051a803fc31cdf5c09` |
| `1222:target` | `57134350497a57636869c19eb2938a491639d28f4f7481aa289fa6e9736193a7` | `6a6e4571351b6d726c65588e19f44bfd0d179ece291861b8071644a6c81c732b` |
| `1222:temporal_twin` | `5c90a29ed5d622b5912bda17f06f61ff997f0ef5bf35ef7e82a679167cff9bf2` | `e09c002225b8e1bc35098e56682a66c4f74ac72c6c9c6e2cc2edb3edd60484a3` |

## Prospective reporting contract

`summarize-stage2-v5` is independent of any unmerged paired-reporting PR. It
reports planned cases, attempted calls, valid responses, attempted and valid
coverage, and an observed denominator. Unattempted or provider/parser-invalid
cases are **unavailable**, never ordinary RCA errors. The primary RCA count and
all five dimension counts use valid observations as the observed denominator.
Target and temporal-twin exact/mechanism counts each report observed coverage
against four planned cases.

For each construction, a complete valid pair is classified as
`correct_mechanism_flip`, `both_concurrency`, `both_state_transition`,
`reversed_mechanism_flip`, or `one_or_both_other_valid_mechanism_labels`.
Incomplete/failed pairs are `unavailable`, with each role's exact status
(`unattempted`, provider error, rate limit, refusal, parse failure, or valid)
reported separately. Paired exact and paired mechanism counts use only complete
valid pairs; both observed and planned denominators are shown.

Evidence-v5 reporting includes evidence-supported count, average essential,
contrast, and supportive coverage, useful citation precision, invalid and
wrong-subject citation counts, and each case's selected paths and missing
essentials. Infrastructure reporting includes provider/parser/rate-limit/
refusal counts. Token totals and a snapshot-priced estimate appear if available;
the JSONL SHA-256 is reported after an artifact exists. Raw responses remain
inspectable via the existing `inspect` command.

For future approved execution only:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/incident_003_v3_relative_time_v1_paired_sol_development_v5.toml \
  --results results/incident_003_v3_relative_time_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl \
  --execute
```

Afterward, the paired report would use `summarize-stage2-v5 --config ...
--results ... --pricing experiments/pricing/openai_gpt_5_6_sol_2026-09-10.toml`.
Neither command was executed with provider access during this preparation.
