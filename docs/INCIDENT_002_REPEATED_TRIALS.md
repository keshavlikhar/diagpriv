# Incident 002 Repeated-Trial Development Protocol

## Status and purpose

Completed and frozen. This document originally preregistered two additional
GPT-5.6 Sol observations for every Incident 002 development seed-condition
pair. The execution attempted all 60 calls once and produced 50 valid responses
and ten transport failures. It does not repair, replace, or reinterpret trial 1.

The original hypothesis remains:

`Raw ≈ Format-preserving > HMAC / Tokenization / Redaction`

especially for `trigger` and `failure_mechanism`. The final primary and
transport-recovered sensitivity findings are frozen in
`docs/INCIDENT_002_FINAL_FINDINGS.md`. Three trials per cell remain development
observations and do not support claims of statistical significance, causality,
or general model behavior.

## Frozen trial-1 observations and artifacts

Historical schema-v6 records contain no `trial_index`. This protocol maps each
of the following completed records to trial 1 only during repeated-trial
analysis. It does not add a field to, rewrite, or reserialize a historical
JSONL.

| Condition | Trigger | Mechanism | Exact RCA | Trial-1 artifact SHA-256 |
|---|---:|---:|---:|---|
| Raw | 6/6 | 6/6 | 4/6 | `b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f` |
| Redaction v1 | 2/6 | 2/6 | 0/6 | `aaaad02bc5bdaa6dd07cbe5785d92d6a38e9475b34bf13c4191a52072e611f33` |
| HMAC v1 | 0/6 | 0/6 | 0/6 | `20f91837846ed9bac0d50d09671aee4166033e58d51622aed6905a628edb71ad` |
| Tokenization v1 | 1/6 | 1/6 | 0/6 | `f6d0f56f65d44140692a6d5a3eebff6a662897356346d8872b4a804e55d694d3` |
| Format-preserving v1 | 4/6 | 4/6 | 2/6 | `03cce974a6ac2ad9f5d7d393ab6b139fcbb6072d44ccb8a080e1a73056661fa0` |

These ignored local artifacts are immutable. An incorrect response or a
technical failure is never automatically rerun or replaced.

## Repetition protocol

Protocol ID: `incident-002-three-trial-development-v1`.

Every condition uses Incident Family 002, frozen seeds 1000, 1001, 1003, 1004,
1005, and 1017, GPT-5.6 Sol, medium reasoning, omitted temperature,
`max_output_tokens = 4096`, `raw-rca-v2`, `rca-taxonomy-v2`, and
`raw-rca-scorer-v2`. The benchmark, oracle, evidence, transformations,
namespaces, HMAC key protocol, and invariants are unchanged.

- Trial 1 is the existing schema-v6 observation.
- Trial 2 is one new independent Responses API call.
- Trial 3 is one new independent Responses API call.
- Each new observation is schema v7 and records `trial_index = 2` or
  `trial_index = 3`.
- The trial index is run provenance only and is absent from the prompt.
- A provider, parser, rate-limit, or refusal failure remains its attempted
  observation. There is no application-level retry or replacement policy.

This scheduled exactly `6 seeds × 5 conditions × 2 trials = 60` new calls,
creating 90 attempted observations after combining the 30 immutable trial-1
observations with trials 2 and 3. Ten attempted repeated-trial observations
were transport failures and remain missing in the primary analysis.

## Input identity

Every repeated-trial config freezes the six trial-1 `model_input_sha256` values.
Dry-run and execution preflight reconstruct each input separately for trials 2
and 3, verify both against trial 1, and fail before provider setup if any hash
differs. Because `trial_index` is not used by `prepare_model_input`, it cannot
change the prompt. There are 30 unique seed-condition inputs and 60 verified
future uses of those inputs.

The HMAC condition continues to require external
`DIAGPRIV_HMAC_KEY_HEX`, key ID
`hmac-v1-synthetic-experiment-key-001`, and non-secret SHA-256 fingerprint
`fd04c65f6329f9e8c42b392ea8b9253a6c88da58e6f3858a322228bee907997d`.
The key itself is never placed in the prompt, config, manifest, JSONL, log, or
repository.

## Prespecified reporting

Continue reporting exact RCA, `overall_correct`, the five existing RCA
dimensions, evidence precision/recall/F1, token usage, estimated cost, and all
technical failures. No new post-hoc score is introduced.

For every condition, report:

1. trigger and failure-mechanism correctness across all 18 observations;
2. per-seed trigger and mechanism correctness across three trials;
3. the number of seeds with 0/3, 1/3, 2/3, or 3/3 correctness for each primary
   diagnostic dimension;
4. exact RCA across all 18 observations; and
5. affected-component accuracy separately.

Component localization is not combined with trigger/mechanism correctness into
a new causal-core metric.

## Configurations, result paths, and historical commands

Each completed result path is append-only, ignored by Git, and contains both
trial 2 and trial 3 records for one condition. The files must not be rerun,
overwritten, or committed.

| Condition | Configuration | Frozen result path |
|---|---|---|
| Raw | `experiments/incident_002_raw_sol_repeated_trials.toml` | `results/incident_002_raw_sol_repeated_trials_2_3.jsonl` |
| Redaction v1 | `experiments/incident_002_redaction_v1_sol_repeated_trials.toml` | `results/incident_002_redaction_v1_sol_repeated_trials_2_3.jsonl` |
| HMAC v1 | `experiments/incident_002_hmac_v1_sol_repeated_trials.toml` | `results/incident_002_hmac_v1_sol_repeated_trials_2_3.jsonl` |
| Tokenization v1 | `experiments/incident_002_tokenization_v1_sol_repeated_trials.toml` | `results/incident_002_tokenization_v1_sol_repeated_trials_2_3.jsonl` |
| Format-preserving v1 | `experiments/incident_002_format_preserving_v1_sol_repeated_trials.toml` | `results/incident_002_format_preserving_v1_sol_repeated_trials_2_3.jsonl` |

The commands used to create these frozen artifacts are retained only as
protocol history. They are not authorization to rerun them:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot --config experiments/incident_002_raw_sol_repeated_trials.toml --results results/incident_002_raw_sol_repeated_trials_2_3.jsonl --execute
uv run python -m diagpriv.evaluation.cli run-pilot --config experiments/incident_002_redaction_v1_sol_repeated_trials.toml --results results/incident_002_redaction_v1_sol_repeated_trials_2_3.jsonl --execute
uv run python -m diagpriv.evaluation.cli run-pilot --config experiments/incident_002_hmac_v1_sol_repeated_trials.toml --results results/incident_002_hmac_v1_sol_repeated_trials_2_3.jsonl --execute
uv run python -m diagpriv.evaluation.cli run-pilot --config experiments/incident_002_tokenization_v1_sol_repeated_trials.toml --results results/incident_002_tokenization_v1_sol_repeated_trials_2_3.jsonl --execute
uv run python -m diagpriv.evaluation.cli run-pilot --config experiments/incident_002_format_preserving_v1_sol_repeated_trials.toml --results results/incident_002_format_preserving_v1_sol_repeated_trials_2_3.jsonl --execute
```

No repeated-trial command is authorized again under these experiment IDs.

## Frozen repeated-trial artifacts and primary result

| Condition | Trials 2–3 artifact SHA-256 |
|---|---|
| Raw | `ad8d8e059efdea20c7a25f325c1bf3f3ae5e65b7c2eb7eef6953f0039528026a` |
| Redaction-v1 | `56f43a72ce4bdf8160cade695bfc83995ef29846ebbe0b10d887b6b87040ee15` |
| HMAC-v1 | `b2fda91b0c958dcc11e405c30c4431a982735070f1667b86b155415f407f1b31` |
| Tokenization-v1 | `441a603bb1e31f373ac4920eaf31e0882d3538f833b683e1c159f2ec7cde11df` |
| Format-preserving-v1 | `cb1b17e8ad57ce4788ddb3d37e5249fde27263d912f16f03664dc506956df318` |

The primary as-executed result combines trial 1 with trials 2 and 3 while
retaining the ten transport failures as missing responses:

| Condition | Valid /18 | Trigger | Failure mechanism | Exact RCA | Overall correct |
|---|---:|---:|---:|---:|---:|
| Raw | 18 | 15 | 15 | 9 | 9 |
| Redaction-v1 | 9 | 2 | 2 | 0 | 0 |
| HMAC-v1 | 18 | 1 | 1 | 1 | 1 |
| Tokenization-v1 | 17 | 2 | 2 | 0 | 0 |
| Format-preserving-v1 | 18 | 10 | 10 | 4 | 4 |

Recovery never changes this primary view. See
`docs/INCIDENT_002_TRANSPORT_RECOVERY.md` for the separately labeled
sensitivity protocol and outcome.

## Cost estimate

Trial 1 across all five conditions cost an estimated $1.594500 under pricing
snapshot `openai-gpt-5.6-sol-2026-09-10`. If trials 2 and 3 have the same usage
as trial 1, the 60 new calls would cost approximately **$3.189000**. Actual
output and reasoning usage can vary, so this is a planning estimate rather than
a spending guarantee or provider invoice.
