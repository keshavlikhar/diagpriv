# Incident 002 Final Development Findings

## Frozen scope

Incident 002 is a synthetic development benchmark. The comparison uses six
frozen development seeds (1000, 1001, 1003, 1004, 1005, and 1017), five
evidence conditions, GPT-5.6 Sol with medium reasoning and omitted temperature,
and three logical trials per seed-condition. No validation or held-out instance
is part of this analysis.

The trial-1 observations, repeated-trial observations, and transport-recovery
observations are immutable. The recovery records are later sensitivity-analysis
substitutions for ten specified transport failures only. They do not rewrite,
replace, or add trials to the primary as-executed analysis.

## Primary as-executed result

The primary result preserves the ten original transport failures as missing
model responses. Missing responses are not scored as incorrect diagnoses.

| Condition | Valid /18 | Trigger correct | Failure mechanism correct | Exact RCA | Overall correct |
|---|---:|---:|---:|---:|---:|
| Raw | 18 | 15 | 15 | 9 | 9 |
| Redaction-v1 | 9 | 2 | 2 | 0 | 0 |
| HMAC-v1 | 18 | 1 | 1 | 1 | 1 |
| Tokenization-v1 | 17 | 2 | 2 | 0 | 0 |
| Format-preserving-v1 | 18 | 10 | 10 | 4 | 4 |

Nine missing responses were in redaction-v1 and one was in tokenization-v1.
There were no parser, rate-limit, or refusal failures. This primary view remains
separately preserved regardless of the recovery outcome.

## Transport-recovered sensitivity result

The prespecified sensitivity join substitutes one valid recovery response into
each eligible missing logical cell while retaining both physical records and
their provenance. It contains 18 valid observations per condition.

| Condition | Valid | Trigger | Failure mechanism | Exact RCA | Component |
|---|---:|---:|---:|---:|---:|
| Raw | 18/18 | 15/18 | 15/18 | 9/18 | 12/18 |
| Redaction-v1 | 18/18 | 2/18 | 2/18 | 0/18 | 10/18 |
| HMAC-v1 | 18/18 | 1/18 | 1/18 | 1/18 | 13/18 |
| Tokenization-v1 | 18/18 | 2/18 | 2/18 | 0/18 | 13/18 |
| Format-preserving-v1 | 18/18 | 10/18 | 10/18 | 4/18 | 10/18 |

Evidence-overlap means in the sensitivity view are:

| Condition | Precision | Recall | F1 |
|---|---:|---:|---:|
| Raw | 0.774074 | 0.291667 | 0.415177 |
| Redaction-v1 | 0.761111 | 0.465278 | 0.574407 |
| HMAC-v1 | 0.799074 | 0.465278 | 0.582153 |
| Tokenization-v1 | 0.811111 | 0.472222 | 0.593518 |
| Format-preserving-v1 | 0.744444 | 0.347222 | 0.459755 |

Evidence-overlap metrics did not track causal correctness: conditions with very
low trigger and failure-mechanism accuracy sometimes had higher evidence F1
than raw. Component localization also remained unstable and is reported
separately from the primary diagnostic dimensions.

## Transport-recovery outcome

All 10 authorized attempt-1 recovery requests produced valid responses. None
selected the correct trigger, failure mechanism, or exact five-label RCA; 7/10
selected the oracle component. There were no recovery provider, parser,
rate-limit, or refusal failures and no second recovery attempts. The recovery
artifact SHA-256 is
`87902fa3217aaca020cb2cd2df14effc19c8c97a6f823031ed171a6f0ef4747e`.

## Frozen scientific interpretation

Incident 002 provides repeated development-stage directional support for the
diagnostic-invariant hypothesis. Raw evidence achieved the highest
trigger/failure-mechanism accuracy, followed by format/constraint-preserving
pseudonymization. Redaction, deterministic tokenization, and HMAC performed
substantially worse on these dimensions when identifier structure was removed.
The result does not establish Raw ≈ Format-preserving, statistical
significance, general LLM behavior, or a universal privacy-method ranking.

These are associations in a small synthetic development experiment, not causal
estimates. Only six development seeds and three logical trials per
seed-condition were analyzed. The later recovery responses are
sensitivity-analysis substitutions, not revisions to the primary experiment.

Format-preserving seed 1005 missed the oracle trigger and failure mechanism in
all three logical trials even though the transformation preserved every
applicable declared structural invariant. Preservation of the declared
invariants is therefore not demonstrated to be sufficient for reliable model
use. This finding does not justify changing the frozen benchmark, oracle,
invariants, transformations, prompt, taxonomy, or scorer.

## Immutable local artifact ledger

All paths below are Git-ignored local JSONLs. The hashes identify the immutable
observations; the files are not repository artifacts.

| Role | Condition | Local artifact | SHA-256 |
|---|---|---|---|
| Trial 1 | Raw | `results/incident_002_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f` |
| Trial 1 | Redaction-v1 | `results/incident_002_redaction_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `aaaad02bc5bdaa6dd07cbe5785d92d6a38e9475b34bf13c4191a52072e611f33` |
| Trial 1 | HMAC-v1 | `results/incident_002_hmac_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `20f91837846ed9bac0d50d09671aee4166033e58d51622aed6905a628edb71ad` |
| Trial 1 | Tokenization-v1 | `results/incident_002_tokenization_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `f6d0f56f65d44140692a6d5a3eebff6a662897356346d8872b4a804e55d694d3` |
| Trial 1 | Format-preserving-v1 | `results/incident_002_format_preserving_v1_sol_development_gpt_5_6_sol_medium.jsonl` | `03cce974a6ac2ad9f5d7d393ab6b139fcbb6072d44ccb8a080e1a73056661fa0` |
| Trials 2–3 | Raw | `results/incident_002_raw_sol_repeated_trials_2_3.jsonl` | `ad8d8e059efdea20c7a25f325c1bf3f3ae5e65b7c2eb7eef6953f0039528026a` |
| Trials 2–3 | Redaction-v1 | `results/incident_002_redaction_v1_sol_repeated_trials_2_3.jsonl` | `56f43a72ce4bdf8160cade695bfc83995ef29846ebbe0b10d887b6b87040ee15` |
| Trials 2–3 | HMAC-v1 | `results/incident_002_hmac_v1_sol_repeated_trials_2_3.jsonl` | `b2fda91b0c958dcc11e405c30c4431a982735070f1667b86b155415f407f1b31` |
| Trials 2–3 | Tokenization-v1 | `results/incident_002_tokenization_v1_sol_repeated_trials_2_3.jsonl` | `441a603bb1e31f373ac4920eaf31e0882d3538f833b683e1c159f2ec7cde11df` |
| Trials 2–3 | Format-preserving-v1 | `results/incident_002_format_preserving_v1_sol_repeated_trials_2_3.jsonl` | `cb1b17e8ad57ce4788ddb3d37e5249fde27263d912f16f03664dc506956df318` |
| Recovery sensitivity | Redaction-v1 and tokenization-v1 | `results/incident_002_sol_transport_recovery.jsonl` | `87902fa3217aaca020cb2cd2df14effc19c8c97a6f823031ed171a6f0ef4747e` |

No local JSONL should be edited, regenerated under the same experiment ID, or
committed. No further Incident 002 provider call is authorized at this stage.
