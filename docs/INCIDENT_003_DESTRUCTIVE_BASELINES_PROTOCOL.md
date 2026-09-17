# Incident 003 destructive temporal baselines protocol

Status: temporal-ablation observation complete and frozen; supporting conditions
paused pending benchmark-cue investigation.

## Scientific question

This matched development suite asks whether preserving diagnostic temporal
structure matters for LLM root-cause analysis. It keeps Incident 003 v2, the
eight frozen development seeds, the model, prompt, taxonomy, scorer, evidence
protocol, decoding settings, and one-call schedule fixed. Only the evidence
transformation changes.

The frozen references are not rerun:

| Condition | Exact RCA | Result SHA-256 |
|---|---:|---|
| Raw | 8/8 | `54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915` |
| `relative-time-v1` | 8/8 | `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb` |
| `temporal-ablation-v1` | 8/8 | `aebe64d289c9a0f1d201a8066e6678b0c386bcfaf07026eb73377bc475432922` |

The primary negative control is `temporal-ablation-v1`. Redaction, HMAC,
tokenization, and format-preserving pseudonymization are supporting historical
baselines whose existing behavior is applied without reinterpretation or
composition.

## Frozen hypothesis

The preregistered directional development-stage hypothesis is:

`Raw approximately equals Relative-time-v1 > Temporal-ablation-v1`

The supporting expected pattern is:

`Raw approximately equals Relative-time-v1 > Redaction / HMAC / Tokenization / Format-preserving`

No numeric success threshold is defined. Temporal ablation did not follow the
expected direction: it remained 8/8 exact despite unavailable temporal
semantics and was 0/8 evidence-supported. This is a frozen development finding,
not confirmatory inference. See
`docs/INCIDENT_003_TEMPORAL_ABLATION_FINDINGS.md`.

## Matched design

All five configured conditions use:

- family `incident_003_temporal_compensation_v2`;
- seeds `1019, 1020, 1021, 1022, 1023, 1025, 1026, 1028`;
- one call per seed;
- GPT-5.6 Sol with medium reasoning;
- omitted temperature;
- `raw-rca-v3`, `rca-taxonomy-v3`, and `raw-rca-scorer-v3`;
- `evidence-support-v4` for destructive observations;
- `incident-003-generator-v2` and `incident-003-temporal-protocol-v2`;
- manifest `raw-rca-manifest-v10`;
- a result path that must not already exist.

The transformations are never combined. Each starts from the same raw
`Incident.model_view()`.

## Exact condition semantics

### `temporal-ablation-v1`

The existing `incident-003-temporal-ablation-v1` implementation changes only
annotated timestamps. Every occurrence becomes the unique deterministic marker
`TA1::<source>::<evidence_id>::<field>`. The marker carries evidence-slot
identity but no original time. Temporal parsers reject it. Structured row order
is unchanged. Log rows are deterministically sorted by `(event_kind,
evidence_id)` to remove residual chronological event-sequence leakage.

It destroys calendar time, relative offsets, temporal equality, strict order,
duration, overlap, deadline crossing, and the causal sequence otherwise exposed
by chronological log order. It retains non-temporal identifiers, states,
results, messages, aliases, sources, linkage, evidence IDs, and cardinality.
It is a causal diagnostic ablation, not a privacy-optimal transformation.

### `redaction-v1`

Every annotated sensitive scalar is replaced by its historical path-generic
placeholder, such as `[REDACTED:workflow_attempts.deadline_at]`. All occurrences
at one path collapse to one value. No identity preservation is intended.
Timestamp strings are non-parseable; equality within a path can remain true
only through all-to-one collapse, while cross-path timestamp and identifier
relationships are not preserved. Non-sensitive operational evidence is
unchanged.

### `hmac-v1`

Every annotated sensitive scalar is replaced by the existing namespaced
`HMAC1_...` HMAC-SHA-256 pseudonym. Shared identifier annotations use
`shared:<classification>:<field>` namespaces; `remove_or_pseudonymize`
timestamps use path-specific namespaces. Identifier equality, inequality, and
intended cross-source linkage remain genuine. Timestamp tokens are not temporal
values: same-path equality may remain, but equality across timestamp fields,
order, duration, overlap, and deadline crossing are unavailable.

The key remains external in `DIAGPRIV_HMAC_KEY_HEX`. The fixed non-secret key
ID is `hmac-v1-synthetic-experiment-key-001`; the frozen non-secret SHA-256
fingerprint is
`fd04c65f6329f9e8c42b392ea8b9253a6c88da58e6f3858a322228bee907997d`.
Neither the key nor a reversible mapping is persisted.

The 200-instance property audit uses the repository's non-secret public audit
key only to verify key-independent equality/linkage behavior. The frozen eight
provider-input hashes were reconstructed with the authorized external key and
must continue to match the fingerprint above. The public audit key is not used
for the proposed provider observations.

### `tokenization-v1`

Every annotated sensitive scalar uses the existing ephemeral, incident-local,
two-pass deterministic token map. Namespaces follow the same annotation policy
as HMAC. Candidate values are ordered by the frozen SHA-256 assignment rule and
receive one-based ordinal tokens. Identifiers preserve equality, inequality,
and intended cross-source linkage. Timestamp tokens remain path-scoped opaque
identifiers and are not interpreted as temporal values. Mapping tables are not
model-visible or persisted. Reproducibility applies to the same complete
ModelView/candidate population, not arbitrary independent batches.

### `format-preserving-v1`

Every annotated sensitive string uses the existing deterministic
character-class-pattern pseudonymization with collision handling. Identifier
linkage remains preserved under annotation-derived namespaces. For timestamps,
the method retains length, separator positions, and ASCII character-class
shape, but it also pseudonymizes alphabetic positions such as `T` and `Z`.
The resulting strings are not valid RFC3339 timestamps and are not assigned
temporal semantics. This baseline is not cryptographic format-preserving
encryption and is not redefined as a temporal-semantic transform.

## Temporal semantics and evidence protocol versioning

Raw retains `temporal-semantics-v1`; `relative-time-v1` retains
`relative-time-semantics-v1`. Every condition in this suite records
`temporal-semantics-unavailable-v1`. No lexical ordering of placeholders,
digests, ordinal tokens, or shape-preserving strings is treated as time.

The normative rubric is reused unchanged. Evidence IDs, subject bindings,
acceptable citation paths, predicate IDs and parameters, and requirement-set
hashes remain valid because every condition retains the evidence rows. No
condition-specific easier requirement is introduced.

The identifiers are deliberately separated:

- historical `evidence-support-v3` retains the citation-path behavior used by
  the frozen raw and relative-time provider observations;
- `evidence-support-v4` requires
  `citation_requirements_satisfied AND semantic_predicate_satisfied`;
- `raw-rca-scorer-v3` remains the unchanged five-label RCA scorer.

V4's family-neutral layer handles citation validity, subject binding, path
selection, requirement classes, alternatives, redundancy, and coverage. The
versioned `incident-003-v2-evidence-semantic-evaluator-v1` evaluates each
rubric `relationship_id` from the transformed ModelView under the explicit
temporal-semantics version. The evaluator version is provenance independent of
the unchanged requirement-set SHA-256.

Raw uses `temporal-semantics-v1`, relative time uses
`relative-time-semantics-v1`, and every destructive condition uses
`temporal-semantics-unavailable-v1`. Under unavailable semantics, temporal
predicates deterministically return unsatisfied. Row order, log order, evidence
ID order, token ordinals, lexical string order, and redaction-placeholder
equality cannot substitute for time. Non-temporal predicates still evaluate
from model-visible values; if a transformation destroys the required linkage,
as redaction does here, that relationship also remains unsatisfied.

The normative rubric contents did not change, so every preregistered
`evidence_requirement_set_sha256` remains unchanged. Semantic-evaluator mode is
separate condition provenance recorded by the frozen
`temporal_semantics_version` in each manifest-v10 transformation configuration.

## Frozen-response evidence-support-v4 baseline

The following is an **offline evidence-support-v4 rescoring of frozen
responses**. No provider was rerun and neither ignored JSONL was modified. The
original evidence IDs were evaluated against the regenerated frozen raw or
relative-time ModelView, the unchanged rubric, and the appropriate temporal
semantics. A verification pass also reproduced every recorded historical v3
evidence field from the historical v3 scoring path.

| Condition / interpretation | Essential coverage | Contrast coverage | Supportive coverage | Useful precision | Invalid count / rate | Wrong-subject count | Redundant count / rate | Evidence-supported | Overall correct |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Raw, original historical v3 | 0.395833 | 0.000000 | 0.050000 | 0.837500 | 0 / 0.000000 | 0 | 0 / 0.000000 | 0/8 | 0/8 |
| Raw, offline v4 rescore | 0.395833 | 0.000000 | 0.050000 | 0.837500 | 0 / 0.000000 | 0 | 0 / 0.000000 | 0/8 | 0/8 |
| Relative-time, original historical v3 | 0.479167 | 0.000000 | 0.075000 | 0.850000 | 0 / 0.000000 | 0 | 0 / 0.000000 | 1/8 | 1/8 |
| Relative-time, offline v4 rescore | 0.479167 | 0.000000 | 0.075000 | 0.850000 | 0 / 0.000000 | 0 | 0 / 0.000000 | 1/8 | 1/8 |

The v4 numbers happen to equal the historical v3 numbers because every cited
path selected by these stored responses also satisfies its semantic predicate
in the corresponding raw or relative-time representation. This equality does
not reinterpret the original observations as v4 observations. Future
destructive-condition manifests will record v4 natively.

## 200-instance offline invariant audit

The audit covers only development constructions 1000--1199. It evaluates 200
instances per condition. Across 24,016 annotated timestamp occurrences per
condition, zero transformed timestamps were accepted by the raw temporal
parser. Temporal ablation passed its existing causal-ablation audit in 200/200
instances.

Legend: `G` genuine preservation, `B` broken, `D` degenerate collapse, `E`
expected non-preservation.

| Property | Temporal ablation | Redaction | HMAC | Tokenization | Format-preserving |
|---|:---:|:---:|:---:|:---:|:---:|
| Deterministic | G | G | G | G | G |
| Timestamp literal secrecy | G | G | G | G | G |
| Timestamp parseability | E | E | E | E | E |
| Timestamp equality | E | D | E | E | E |
| Strict ordering | E | E | E | E | E |
| Duration | E | E | E | E | E |
| Positive overlap | E | E | E | E | E |
| Deadline crossing | E | E | E | E | E |
| Essential temporal invariants | E | E | E | E | E |
| Healthy-control temporal invariants | E | E | E | E | E |
| Legitimate-compensation temporal invariants | E | E | E | E | E |
| Exact non-temporal ModelView literals | G | E | E | E | E |
| Non-sensitive operational evidence | G | G | G | G | G |
| Evidence IDs | G | G | G | G | G |
| Row cardinality | G | G | G | G | G |
| Structured row order | G | G | G | G | G |
| Log row order | E | G | G | G | G |
| Source structure | G | G | G | G | G |
| Cross-source identifier linkage | G | E | G | G | G |
| Identifier distinctness | G | D | G | G | G |

`E` is not a software failure when it matches the stated destructive design.
For HMAC, tokenization, and format-preserving pseudonymization, timestamp
equality is `E` because path-scoped timestamp namespaces do not preserve
cross-field equality, even though equality within the same path remains
deterministic. For redaction, equality/distinctness are `D` because generic
placeholders create all-to-one collapse. “Exact non-temporal ModelView
literals” is `E` for the four privacy baselines because they intentionally
replace annotated non-temporal identifiers; their non-sensitive operational
fields remain unchanged.

## 200-instance semantic evidence audit

A deterministic complete citation set was scored against each transformed
ModelView for every development construction from 1000 through 1199. Each cell
is `satisfied / 200`; it reports what the transformed evidence can actually
prove, not model performance.

| Essential requirement | Temporal ablation | Redaction | HMAC | Tokenization | Format-preserving |
|---|---:|---:|---:|---:|---:|
| Target identity linkage | 200 | 0 | 200 | 200 | 200 |
| Deadline before original completion | 0 | 0 | 0 | 0 | 0 |
| Compensation after deadline | 0 | 0 | 0 | 0 | 0 |
| Execution/compensation overlap | 0 | 0 | 0 | 0 | 0 |
| Late successful original effect | 0 | 0 | 0 | 0 | 0 |
| Inconsistent terminal workflow/effect state | 200 | 0 | 200 | 200 | 200 |

All 4,000 destructive temporal checks (four temporal requirements, five
conditions, 200 instances) were unsatisfied. Temporal ablation, HMAC,
tokenization, and format-preserving pseudonymization still proved identity and
the non-temporal terminal-state combination. Redaction proved neither because
its path-specific all-to-one placeholders do not establish genuine cross-source
subject linkage.

## Provenance scheme

Manifest v10 is sufficient; no new schema is introduced. Each future record
contains the canonical seven-field transformation configuration and SHA-256,
the exact rendered `model_input_sha256`, the unchanged
`evidence_requirement_set_sha256`, prompt-template SHA-256, generator/protocol
versions, taxonomy/prompt/scorer/evidence versions, and—only for HMAC—the
non-secret key ID and fingerprint. Historical result JSONLs are not retrofitted.

Canonical configuration SHA-256 values:

| Condition | Transformation-configuration SHA-256 |
|---|---|
| `temporal-ablation-v1` | `fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b` |
| `redaction-v1` | `9d9c69f2e22c85aec58a3e277f5777f6199f66bdfbfcc69b374a370691273953` |
| `hmac-v1` | `0cb1e115411093a775c1f5291f2a766a0c232d0b7c3cec08626f571e1c6c6a14` |
| `tokenization-v1` | `d33bb3ef1e6b18f8f443e6296d35386766c37a1c0b36513b0fc4863599e26a18` |
| `format-preserving-v1` | `797ea7b1b5d7085697d0dd59987bb50853c19a45cc50c8832a01a49001958ff1` |

## Frozen input and rubric hashes

| Condition | Seed | Model-input SHA-256 | Evidence-rubric SHA-256 |
|---|---:|---|---|
| Temporal ablation | 1019 | `c85caa268a24d8cb4a05b5b65481977e6c413a0e996651827fcf0c0095397295` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| Temporal ablation | 1020 | `b7b91347dd678820291c4808d21b11a4ad732a32649a05a2816749c65a1bfad6` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| Temporal ablation | 1021 | `ee9a514d83aa7584ef2d0f1ef20777d1812d6d2bf977613ef30ec340d50a6c45` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| Temporal ablation | 1022 | `95f080a2509263ff19d58dcb1f14de85c25023f7d4d983b7f9f6287d209dab85` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| Temporal ablation | 1023 | `34a6b1f45cc828b28c88146bad0fcb1dd73c00948db15bd0337955119a6d2893` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| Temporal ablation | 1025 | `2bdf67ad72964bcfe0e3eec614b27a5bb18ec9daaf9f3355cb0be33d79e4ae80` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| Temporal ablation | 1026 | `7a62d3175dca0e0691ec75325707ccd970e1208e42170ae412b2b09b171c91de` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| Temporal ablation | 1028 | `30c5ea91e4dae07982f1108896687864418df96e722214fd23057a9b45963e37` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |
| Redaction | 1019 | `671fb8b1fbafe6cb744656b7227f768e721eb9b0ed9ce03f32addbc6ea7c58f1` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| Redaction | 1020 | `6af71bd2df6eaec1601c428bbae942b0b6219634a9d78df9f73f54bf33fc62d8` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| Redaction | 1021 | `91dd18dc9a4b57b2c88ec35b5b4fcb998457ce4ec7347e1aa44c5642f19c7617` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| Redaction | 1022 | `cc2eed8243b2b68fc77ee820b5ebc7b6c6be3d1fadcbf8d03b6808b1f8fce2be` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| Redaction | 1023 | `346a71097892fcea5b1121a23e90d1caf024c47e093d65d427d219c51860cbc9` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| Redaction | 1025 | `be6c5349b3496aca6fbbb381cb12d05cb13f97726d9163caf8d59c615bce93df` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| Redaction | 1026 | `b5f918fb58c349cf78e0eddbc60ec6362d5a6494e28260d930d58f18c97daf09` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| Redaction | 1028 | `1d8c8cb3cf7b9512899443b907f8b3bc909b755489c0b023a514c4ba20726b82` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |
| HMAC | 1019 | `f284bc09c9c16a76a7335a2b58f1ff50c3f5e6005c72a9f51e8f4f452e2ea9c2` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| HMAC | 1020 | `46f19ee9526441a4e161123199f7e04b0ec82cbc65800ead955e8a9365196f5a` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| HMAC | 1021 | `12319fd0a6c7f1c53bb195a64aac8b3a009f0fc2c624bcbec6f56f5505969e6e` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| HMAC | 1022 | `4c832d9acbfd17b493f2f34b0eae994d0e6d0fb0721585a7a079ad862a684dea` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| HMAC | 1023 | `efe59424a0305c1b2116b13d92f2e60112912bb95d6ba76aeb0ec611ddae82e1` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| HMAC | 1025 | `e311f5194a6b75d4a3a071430b4600de71cba2a3e6736ac17fa5b331da3c3bbb` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| HMAC | 1026 | `558fca710b887c9022d69e06fc13c68ec2af42489f78c3c17b01d587ce1c77c0` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| HMAC | 1028 | `7424cccea51b176ac01d5627d7600f27e442f16d6b0eeec1be190bcd7f95f49f` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |
| Tokenization | 1019 | `d1239f3b9022850b91b78f40fe1c13f42f8ef56b7e5c6b6aae6b77a627a7a0b2` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| Tokenization | 1020 | `7eae517fd150388391df00694c94493f1286530f3d234d1a74b57eb9402a09b4` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| Tokenization | 1021 | `8f4de8bddf7782a792a27152578544e0b5eedd1af758792f84d48609e6e83d11` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| Tokenization | 1022 | `fcbb06fd82fa02d6a411f366645f37752d92ae1309c3da9f2fbb59a9a6139877` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| Tokenization | 1023 | `fc26567590f66d091b4a8d17a5e88fae7cc439038b398f35bda64bbe279d2775` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| Tokenization | 1025 | `85fd8c57c38c27c8843b0ef33e4463b618c410d1df7dfe59492467ec89e0e7ce` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| Tokenization | 1026 | `e5930170fbe81fed18488251a1f2568962ad12da244721541726c1cfbd6670f4` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| Tokenization | 1028 | `460e4d304e4320ae405aafcc9f37167941353755eaa85d67f1b06b1c364b1034` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |
| Format-preserving | 1019 | `ee216bab4247da08d6c3a2b9190f0becb2a997889771cda91701bbd12d80e84b` | `c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db` |
| Format-preserving | 1020 | `42f2097442e946fd64ff73a819042434672adbac1af8bedf048f4fca5c35e626` | `d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377` |
| Format-preserving | 1021 | `b957a726110eb08eb3e7e24d4f64960b3b7853604105ee7065a3ea6f1bae9b0e` | `e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac` |
| Format-preserving | 1022 | `95b89d7f21119728c6c00ebba617e27598c5963c2b693839a98b470978d7187f` | `f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64` |
| Format-preserving | 1023 | `f6b57fcdd35bfba04e823542cd05fd97a6386f07baef0025f6bce86a418c410f` | `5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60` |
| Format-preserving | 1025 | `b9e1e1112122f2082813943e4cbaf4cc6d7562e8494661bbe685778041ea8a58` | `03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5` |
| Format-preserving | 1026 | `68fe6760dd96d10180dc65f6affdc27e368faf60777273d7a63bffbb3901e9bd` | `d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b` |
| Format-preserving | 1028 | `5bf48c122433843e6143d81c5bffb14d5011454ea5f6eb81a51d71e6f90caee9` | `2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26` |

## Config and result-path status

| Condition | Config | Append-only result path | Calls | Status |
|---|---|---|---:|---|
| Temporal ablation | `experiments/incident_003_v2_temporal_ablation_v1_sol_development.toml` | `results/incident_003_v2_temporal_ablation_v1_sol_development_gpt_5_6_sol_medium.jsonl` | 8 | Complete and frozen |
| Redaction | `experiments/incident_003_v2_redaction_v1_sol_development.toml` | `results/incident_003_v2_redaction_v1_sol_development_gpt_5_6_sol_medium.jsonl` | 8 | **PAUSED — pending benchmark-cue investigation** |
| HMAC | `experiments/incident_003_v2_hmac_v1_sol_development.toml` | `results/incident_003_v2_hmac_v1_sol_development_gpt_5_6_sol_medium.jsonl` | 8 | **PAUSED — pending benchmark-cue investigation** |
| Tokenization | `experiments/incident_003_v2_tokenization_v1_sol_development.toml` | `results/incident_003_v2_tokenization_v1_sol_development_gpt_5_6_sol_medium.jsonl` | 8 | **PAUSED — pending benchmark-cue investigation** |
| Format-preserving | `experiments/incident_003_v2_format_preserving_v1_sol_development.toml` | `results/incident_003_v2_format_preserving_v1_sol_development_gpt_5_6_sol_medium.jsonl` | 8 | **PAUSED — pending benchmark-cue investigation** |

The suite originally preregistered 40 calls. Eight temporal-ablation calls are
complete. The remaining 32 are not authorized. Frozen configs, paths, hashes,
and the original analysis plan remain recorded; no config is edited in response
to the result.

The staged decision was:

1. execute `temporal-ablation-v1` first (8 calls);
2. stop and analyze that decisive causal negative control;
3. execute the four supporting baselines (32 calls) only after review.

Temporal ablation remained 8/8 exact. The offline cue audit found perfect
non-temporal separability, so step 3 is paused. No remaining command should be
run until the benchmark-cue investigation receives separate review.

## Preregistered analysis

The primary metric is exact five-dimensional RCA. Secondary metrics are each
causal dimension: outcome, trigger, action, mechanism, and component. Evidence
metrics remain separate: essential, contrast, and supportive coverage; useful
citation precision; `evidence_supported`; and overall correctness under
RCA-v3 plus the explicitly reported evidence protocol.

The primary descriptive table is paired by seed across raw, relative time,
temporal ablation, redaction, HMAC, tokenization, and format-preserving. Raw and
relative-time observations are reused from their frozen artifacts, not pooled
with reruns. Their matched evidence comparison uses the documented offline v4
rescoring, while destructive observations produce v4 scores natively.

Interpretation is qualitative and preregistered:

- If raw and relative time remain correct while temporal ablation degrades,
  the observation is consistent with temporal structure contributing to RCA.
- If the destructive string substitutions also degrade, that is consistent
  with loss of temporal semantics harming RCA.
- If temporal ablation remains correct, Incident 003 may be solvable using
  non-temporal cues; causal isolation must be reconsidered before stronger
  claims.
- Unexpected success or condition differences remain findings. The benchmark
  is not rewritten after observing them.

## Limitations

This is a synthetic eight-seed development experiment with one model and one
call per seed. Temporal ablation intentionally changes log order as well as
timestamps, while the four privacy baselines change sensitive identifiers in
addition to timestamps. They therefore support the primary causal contrast and
secondary descriptive contrasts, not a claim that every destructive condition
isolates exactly the same mechanism. Evidence-support-v4 requires both frozen
citation-path coverage and semantic satisfaction under the condition's explicit
temporal semantics; opaque transformed timestamps cannot satisfy a temporal
requirement. Historical evidence-support-v3 remains citation-path-only and is
not relabeled.
No validation, held-out, human, multi-model, or repeated-trial inference is
authorized by this preparation. The observed temporal-ablation success confirms
that the causal-isolation limitation is active rather than hypothetical.
