# Incident 002 Transport-Recovery Sensitivity Protocol

## Status and scope

Completed and frozen. All ten preregistered attempt-1 recovery requests were
made once; no second attempt occurred.

Protocol: `incident-002-transport-recovery-v1`.
Source code checkpoint: `e1bd3c125ae2042b81b5ad88d5c0093d6bd553eb`.
Preparation and result-documentation branch:
`experiment/incident-002-transport-recovery`, stacked on the frozen
repeated-trials branch.

The original 60 repeated-trial invocations produced 50 valid responses and ten
transport failures. Their JSONLs and the 30 trial-1 observations are immutable.
There were no parser, rate-limit, or refusal failures. The primary experiment
remains the **as-executed analysis**, including its missing responses. This
recovery is exclusively a **transport-recovery sensitivity analysis**.

## Exact sparse schedule

One later attempt was permitted and completed for each cell below, in this
order. No valid response, other failure, new seed, condition, or additional
trial was eligible. This was an explicit list, not a Cartesian product of seeds
and trials.

| Condition | Seed | Logical trial | Original transport failure |
|---|---:|---:|---|
| redaction-v1 | 1001 | 3 | TimeoutError |
| redaction-v1 | 1003 | 2 | URLError |
| redaction-v1 | 1003 | 3 | URLError |
| redaction-v1 | 1004 | 2 | URLError |
| redaction-v1 | 1004 | 3 | URLError |
| redaction-v1 | 1005 | 2 | URLError |
| redaction-v1 | 1005 | 3 | URLError |
| redaction-v1 | 1017 | 2 | URLError |
| redaction-v1 | 1017 | 3 | URLError |
| tokenization-v1 | 1001 | 2 | TimeoutError |

All cells are within the frozen Incident 002 development population
1000, 1001, 1003, 1004, 1005, 1017. Seed 1000 is not scheduled for recovery.
No validation or held-out incident is generated or inspected.

## Immutable source ledger

The configuration freezes all five repeated-trial artifact hashes, plus all
five trial-1 artifact hashes. Preflight reads these sources to establish that
the complete set of non-valid observations is exactly the ten transport
failures above. A changed, absent, extra-failure, or unexpectedly valid source
stops preparation before incident construction or provider setup.

| Repeated-trial source condition | SHA-256 |
|---|---|
| raw | `ad8d8e059efdea20c7a25f325c1bf3f3ae5e65b7c2eb7eef6953f0039528026a` |
| redaction-v1 | `56f43a72ce4bdf8160cade695bfc83995ef29846ebbe0b10d887b6b87040ee15` |
| hmac-v1 | `b2fda91b0c958dcc11e405c30c4431a982735070f1667b86b155415f407f1b31` |
| tokenization-v1 | `441a603bb1e31f373ac4920eaf31e0882d3538f833b683e1c159f2ec7cde11df` |
| format-preserving-v1 | `cb1b17e8ad57ce4788ddb3d37e5249fde27263d912f16f03664dc506956df318` |

Paths and the trial-1 ledger are in
`experiments/incident_002_transport_recovery.toml`. Local source JSONLs remain
required for preflight; they are neither copied into fixtures nor committed.
Tests create separate synthetic source fixtures in temporary directories.

## Schema and input provenance

New recovery records use `raw-rca-manifest-v8`. Schema v8 retains
`model_input_sha256` and logical `trial_index` 2 or 3. It additionally requires
a `recovery_provenance` object containing:

- `recovery_protocol_version = incident-002-transport-recovery-v1`;
- `recovery_attempt_index = 1`;
- `recovery_of_trial_index`, equal to the outer logical trial index;
- `original_condition` and `original_seed`, equal to the outer identity;
- `original_failure_type`;
- `original_experiment_id`;
- `original_result_artifact`, a repository-relative source path; and
- `original_result_artifact_sha256`.

Each recovery has a distinct experiment ID ending in `trial-N-recovery-1`.
It is not trial 4 and does not amend the original record. Schemas v2 through
v7 retain their serialization and meanings; recovery provenance is rejected
on those schemas. Ordinary trials cannot silently become recovery records.
Inspection output exposes the provenance alongside each response and score.

For every scheduled cell, preflight checks its input hash against both the
failed original observation and its frozen trial-1 counterpart. It also
reconstructs ordinary and recovery inputs and requires byte-identical rendered
prompts. Recovery metadata, experiment IDs, source failures, and artifact
references never enter ModelView or the rendered prompt. Historical
`prompt_sha256` continues to mean the frozen prompt-template hash.

## Frozen request settings

The request uses Incident 002, its original condition, GPT-5.6 Sol, medium
reasoning, omitted temperature, and `max_output_tokens = 4096`.
`raw-rca-v2`, `rca-taxonomy-v2`, and `raw-rca-scorer-v2` remain unchanged.
Model-version metadata, intended temperature, and omission reason are copied
from the immutable source observation, rather than read from a new metadata
environment override. The request contains no recovery instruction or notice.

No generator, oracle, invariant, transformation, namespace, or transformation
parameter changes. No HMAC cell is recovered, so recovery execution needs no
HMAC key and introduces no new HMAC protocol. `OPENAI_API_KEY` remains external.
Later invocation time is documented; it does not establish that an underlying
provider deployment remains identical. Returned model and usage metadata are
recorded normally.

## One-attempt execution and result protection

Configuration: `experiments/incident_002_transport_recovery.toml`.
One dedicated artifact contains the ten explicitly identified cells:
`results/incident_002_sol_transport_recovery.jsonl`.

The CLI requires that exact output path and refuses an existing file or
symlink. After every preflight check and provider configuration check passes,
it reserves the output using exclusive creation before the first invocation.
An empty or partial artifact also blocks a later launch. This avoids repeating
an uncertain request after a runner abort. Do not rename/delete the artifact
to bypass the one-attempt policy.

Each scheduled cell is invoked once. Incorrect valid answers, provider errors,
parser failures, rate limits, and refusals are retained. Recorded failures may
continue through the fixed schedule; an unhandled runner abort leaves the
artifact intact and stops the batch. There is no automatic retry, resume,
replacement, or second recovery attempt.

Dry run (no provider setup):

```bash
uv run python -m diagpriv.evaluation.cli run-recovery \
  --config experiments/incident_002_transport_recovery.toml \
  --results results/incident_002_sol_transport_recovery.jsonl
```

The executed command is retained as protocol history and must not be rerun:

```bash
uv run python -m diagpriv.evaluation.cli run-recovery \
  --config experiments/incident_002_transport_recovery.toml \
  --results results/incident_002_sol_transport_recovery.jsonl \
  --execute
```

All source and recovery JSONLs remain ignored and untracked. The existing
`inspect` command exposes the recovery responses and their source references.

## Frozen recovery outcome

The single authorized attempt produced 10/10 valid responses, 0/10 correct
trigger, 0/10 correct failure mechanism, 0/10 exact RCA, and 7/10 correct
component. There were no recovery provider, parser, rate-limit, or refusal
failures and no second attempts. The immutable local recovery artifact is
`results/incident_002_sol_transport_recovery.jsonl`, with SHA-256
`87902fa3217aaca020cb2cd2df14effc19c8c97a6f823031ed171a6f0ef4747e`.

## Preregistered analysis views

### A. Primary: as executed

Keep the original trial-1 and repeated-trial records unchanged. The ten
transport failures remain missing model responses. Recovery outcomes never
enter primary numerators, denominators, stability tables, evidence averages,
or original cost accounting. Present correct counts across planned slots
alongside available-response counts; never interpret a transport failure as
an incorrect model diagnosis.

### B. Sensitivity: transport recovered

Construct this separately in analysis memory, with explicit source lineage.
Join on condition, seed, and logical trial. For each of the ten eligible
missing cells, admit only its attempt-1 recovery record whose source artifact
SHA, source experiment ID, logical identity, and model-input hash match.
Reject duplicates and any attempted substitution for an originally valid
response. If recovery parses as valid, use its stored scores in this
separately labeled view, including an incorrect answer. If recovery fails,
the logical cell remains missing. Preserve both physical records either way.

Do not append recovery rows to primary data and treat them as extra trials,
choose the best answer, or silently prefer the latest record. Report the
primary and sensitivity comparisons side by side, with missingness and
provenance visible. The completed sensitivity outcome is reported separately
from the primary view in `docs/INCIDENT_002_FINAL_FINDINGS.md`.

Use only the existing metrics: valid responses, exact RCA, `overall_correct`,
all five causal dimensions, evidence precision/recall/F1, token usage,
estimated cost, and technical failures. Trigger and failure mechanism remain
the primary diagnostic dimensions; no new composite score is introduced.
Evidence means cover scored responses and state their available denominator.
Three-response stability is undefined for a cell that still has missing data.

Report recovery resource usage and failures separately, including unsuccessful
recovery attempts when usage is available. Combined resource accounting adds
recovery costs to the original costs; it never erases the costs or uncertainty
of the original failed invocations. Recovery timing and missingness limit
interpretation; the sensitivity view is never promoted to the primary result.

## Planning cost

Using each scheduled cell's frozen trial-1 usage, the ten calls correspond to
78,400 input and 10,119 output tokens, costing approximately **$0.594350** under
snapshot `openai-gpt-5.6-sol-2026-09-10`. Output includes reasoning. A
conservative scenario with those input counts charged at the snapshot's
cache-write rate and all ten outputs reaching 4,096 tokens is **$1.211200**.
These are pricing-snapshot scenarios, not provider invoices or hard spending
limits. Cache behavior, returned usage, and unknown usage on failures can vary.
