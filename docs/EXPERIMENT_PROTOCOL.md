# Experiment Protocol

## Purpose

This document is the operational handoff for running DiagPriv experiments. It
describes the current v2 protocol and execution controls. Historical details for
the original raw-v1 harness remain in `docs/evaluation_protocol.md`.

No command in this document grants permission to make provider calls. A real
run requires both explicit human approval and the `--execute` flag.

## Fixed v2 RCA protocol

| Item | Value |
|---|---|
| Prompt | `raw-rca-v2` |
| Prompt template SHA-256 | `744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d` |
| Taxonomy | `rca-taxonomy-v2` |
| Scorer | `raw-rca-scorer-v2` |
| Initial model | `gpt-5.6-luna` |
| Reasoning effort | `medium` |
| Temperature | omitted |
| Calls per configured seed | one |

The Luna provider rejected the originally intended `temperature=0` parameter.
Luna requests therefore omit temperature while retaining the intended value
and reason in metadata. Matched GPT-5.6 Sol experiments also omit temperature
to preserve the decoding protocol; this does not claim that Sol rejects the
parameter. Do not substitute another decoding parameter silently.

The historical manifest/config field named `prompt_sha256` is specifically the
SHA-256 of the frozen UTF-8 `raw_rca_v2.txt` **template before**
`{{MODEL_VIEW_JSON}}` is replaced. It is identical across observations using
that template and must not be interpreted as a digest of the fully rendered
provider request. Renaming the persisted field now would be backward
incompatible with frozen results; documentation therefore refers to it as the
prompt-template hash while preserving the field and its meaning.

Historical manifest schemas through `raw-rca-manifest-v5` retain only that
template hash. The Incident 002 experiment introduces
`raw-rca-manifest-v6`, which adds `model_input_sha256`: SHA-256 over the exact
UTF-8 rendered prompt string placed in `ModelRequest.prompt` and sent as the
provider's model-visible `input`. It changes with the rendered ModelView. It
does not hash decoding settings, transport fields, credentials, or any hidden
oracle data. Historical observations are not retroactively augmented or
rewritten.

Repeated Incident 002 observations use `raw-rca-manifest-v7`. Schema v7 keeps
the v6 rendered-input hash and requires a positive integer `trial_index`.
Historical schema-v6 observations do not acquire this field; the repeated-trial
analysis protocol maps those frozen records to trial 1 externally. Trial index
is provenance only and never enters the rendered prompt. The reviewed configs
schedule only indices 2 and 3 and require them to continue consecutively after
the one historical trial.

Transport-recovery records use `raw-rca-manifest-v8`, preserving logical trial
2 or 3 and requiring a separate `recovery_provenance` object. It records attempt
1, the recovery protocol, original condition/seed/trial, original failure type,
source experiment ID, and immutable source-artifact reference/SHA-256.
Recovery metadata never enters the prompt. Historical schemas and JSONLs are
unchanged. The dedicated sparse runner verifies all original failures and
input hashes before provider setup and reserves a new fixed result path before
the first call. See `docs/INCIDENT_002_TRANSPORT_RECOVERY.md`.

The prompt exposes the complete fixed taxonomy but no family-specific answer.
The required canonical dimensions are:

1. `observed_outcome`;
2. `trigger`;
3. `subsequent_action`;
4. `failure_mechanism`; and
5. `affected_component`.

`exact_root_cause_correct` requires all five dimensions. Evidence precision,
recall, and F1 compare cited model-visible evidence IDs with oracle expected
evidence IDs. `evidence_supported` requires at least one expected visible ID and
no nonexistent ID. `overall_correct` requires exact RCA and supported evidence.
No LLM grader participates in primary scoring.

## Seed policy

| Split | Range | Rule |
|---|---:|---|
| Development | 1000–1999 | Transformation debugging and approved pilots |
| Validation | 2000–2999 | Separately approved protocol assessment |
| Retired | 10000–10999 | Never invoke; mechanically audited before LLM evaluation |
| Held-out evaluation | 20000–20999 | Generate only after complete protocol freeze and explicit override |

Normal pilot configurations reject held-out seeds and enforce whether a file is
development-only or validation-only. Unassigned seeds are rejected. Do not use
the existence of an override as routine authorization.

### Frozen Incident 002 development comparison set

The Incident 002 set was chosen mechanically. Starting at seed 1000, generation
was inspected in ascending order. A seed was selected exactly when its hidden
generator-side `defect_class` had not appeared previously, and inspection
stopped immediately after all six classes had appeared. Structural template,
expected provider behavior, transformation behavior, target position, evidence
complexity, and model difficulty were not selection criteria.
The procedure is identified as
`incident-002-first-defect-class-occurrence-v1` in the pilot configuration.

| Seed | Generator-side defect class | Structural template | Observable structural delta |
|---:|---|---|---|
| 1000 | `extra_separator` | `hyphenated_mixed_b` | `extra_separator` |
| 1001 | `missing_separator` | `hyphenated_mixed_b` | `missing_separator` |
| 1003 | `case_class_mismatch` | `underscored_mixed` | `case_class_mismatch` |
| 1004 | `truncation` | `slashed_mixed` | `truncation` |
| 1005 | `leading_zero_loss` | `slashed_mixed` | `numeric_run_leading_position_deletion` |
| 1017 | `fixed_width_mismatch` | `slashed_mixed` | `fixed_width_mismatch` |

The scan generated seeds 1000 through 1017 and then stopped. These six seeds,
in this order, are frozen for every matched Incident 002 development condition:
raw, redaction-v1, hmac-v1, tokenization-v1, format-preserving-v1, and a future
DiagPriv condition. They must not be replaced after observing model behavior.
The evaluation registry rejects every other seed for Incident 002; its current
pilot configuration also requires an empty validation and held-out set.

### Incident 002 raw development experiments

`experiments/incident_002_raw_development.toml` binds Incident 002 and the six
frozen seeds to the unchanged v2 RCA protocol, GPT-5.6 Luna with medium
reasoning, omitted temperature, raw evidence, and one call per seed. The
frozen append-only local result path is
`results/incident_002_raw_development_gpt_5_6_luna_medium.jsonl`. Preparation
commit `f71aad0f1b7670cfd27f9fe723048417e2d2e8f6` and result SHA-256
`43004a011443fd2b2ca1789e4ce57198484b8cad01e50f80b240679148d6b425`
identify that development observation.

The separate `experiments/incident_002_raw_sol_development.toml` qualification
changes only the substantive experimental variable `requested_model`, from
`gpt-5.6-luna` to `gpt-5.6-sol`. Pilot/result identifiers and the separate Sol
pricing snapshot are administrative provenance. The configuration embeds the
frozen Luna `model_input_sha256` for each seed. Loading the configuration
reconstructs every raw prompt and fails closed if any digest differs, before a
provider is configured. Temperature remains omitted; no Sol-specific decoding
parameter is introduced. The omission preserves the matched Luna decoding
protocol and does not claim that GPT-5.6 Sol rejects temperature. Its frozen
result produced 6/6 valid responses, 4/6 exact RCA, and 4/6
`overall_correct`; its SHA-256 is
`b8bdaef010a74bc5256363c818c914e146172160e3745bc7a8e9407e775e5c0f`.

### Incident 002 Sol privacy comparison and repetition

The four privacy configurations were executed together on the six frozen seeds
using GPT-5.6 Sol, medium reasoning, omitted temperature, one call per seed,
and unchanged v2 prompt, taxonomy, scorer, evidence, and manifest semantics.
Each configuration preregistered the exact transformed `model_input_sha256` for
every seed. HMAC also checked the established non-secret key fingerprint while
keeping the key external.

Trial 1 yielded trigger/mechanism correctness of 6/6 raw, 2/6 redaction, 0/6
HMAC, 1/6 tokenization, and 4/6 format-preserving. The accepted assessment is
**mixed, with directional support for the preregistered hypothesis**. The
preregistered development hypothesis remains
`Raw ≈ Format-preserving > HMAC / Tokenization / Redaction`. Contrary results
must be retained.

The completed repeated-trial protocol attempted exactly two further calls for
every one of the 30 seed-condition cells. Manifest v7 records trial indices 2
and 3; each index reconstructed the same frozen model input as trial 1. Primary
reporting remains exact RCA, `overall_correct`, each RCA dimension, evidence
precision/recall/F1, response/failure counts, token usage, and cost. Trigger and
failure mechanism remain the preregistered primary Incident 002 diagnostic
dimensions; component accuracy is reported separately and is not folded into a
new post-hoc metric.

See `docs/INCIDENT_002_REPEATED_TRIALS.md` for the trial-1 and repeated-trial
artifact ledgers, configurations, historical commands, and prespecified
reporting. The offline invariant matrix remains in
`docs/INCIDENT_002_PRIVACY_COMPARISON.md`.

The completed repeated-trial primary analysis retains its ten missing transport
responses. The separately preregistered transport recovery produced one valid
attempt-1 response for each eligible missing cell and no second attempts. Those
records are substitutions only in the sensitivity view, never for an originally
valid cell. Both source failure and recovery records remain intact. No new
metric or composite score was introduced, and recovery does not become the
primary as-executed analysis. Final results and interpretation limits are in
`docs/INCIDENT_002_FINAL_FINDINGS.md`.

## Evidence conditions

- `raw`: unmodified `Incident.model_view()`.
- `redaction-v1`: generic placeholders at sensitive annotated paths; no
  intentional identity preservation.
- `hmac-v1`: external-key HMAC pseudonyms at sensitive annotated paths;
  annotation-defined shared or path-specific namespaces.
- `tokenization-v1`: short deterministic ordinal tokens from an ephemeral,
  candidate-population-local mapping.
- `format-preserving-v1`: deterministic same-pattern pseudonyms from an
  ephemeral mapping with explicit collision resolution.

All conditions use the same v2 prompt, taxonomy, scorer, model configuration,
and evidence methodology for matched comparisons. Oracle labels, invariant
definitions, expected evidence, and privacy annotations remain outside the
provider-facing ModelView.

## Provider boundary and failures

`FakeProvider` supports offline tests. `OpenAIResponsesProvider` is the sole real
adapter and reads credentials at invocation time. It does not retry.

Every attempted provider observation must retain status, sanitized error data,
raw output, structured parse status, provider-returned model ID, response ID,
timestamps when available, service tier, token counts, prompt/taxonomy/scorer
versions, seed, split, and condition. HMAC manifests may record the non-secret
experimental key ID, never the key.

HTTP status, error type, error code, parameter, message, and request ID may be
retained when available. API keys, Authorization headers, key material, and
unfiltered response headers must never be persisted or printed.

Provider errors, rate limits, refusals, malformed output, missing fields, and
unknown categories remain explicit outcomes. Do not automatically retry,
rewrite, or exclude them. If a run is invalidated as infrastructure, preserve it
under its original experiment ID and create a separately approved diagnostic
record.

## Manifest and artifact rules

- JSONL manifests are append-only and experiment IDs are unique.
- Never edit a completed line or overwrite a completed result file.
- Do not rerun a completed or incorrect observation automatically.
- After completion, summarize and inspect every individual response.
- Compute and record SHA-256 before interpreting or changing subsequent work.
- Pricing is calculated from a dated configuration separate from scientific
  scoring; stored token counts remain valid when prices change.
- `results/` is Git-ignored. Collaboration requires a separately reviewed
  artifact-sharing mechanism and digest verification.

## Pre-execution checklist

1. Confirm explicit human approval for the exact condition and split.
2. Start from the reviewed commit and inspect `git status`.
3. Verify prompt hash, taxonomy, scorer, model, reasoning, temperature behavior,
   calls per seed, and seed lists.
4. Verify the target result path is new and the corresponding frozen files are
   unchanged.
5. Run the full offline test suite and `git diff --check`.
6. Perform a dry run without `--execute` and review its printed plan.
7. Confirm required secrets exist without printing them.
8. Execute the approved command exactly once.
9. Run `summarize` and `inspect`, record all failures, and compute the JSONL
   digest.
10. Freeze the result before any protocol discussion or code change.

## Completed development comparisons

The following five-seed observations are frozen and must not be invoked again
under their completed experiment IDs:

| Condition | Exact RCA |
|---|---:|
| Raw v2 | 5/5 |
| Redaction v1 | 4/5 |
| HMAC v1 | 5/5 |
| Tokenization v1 | 5/5 |
| Format-preserving v1 | 4/5 |

These are development observations only. No HMAC, tokenization, or
format-preserving validation observation exists, and none of these conditions
has been used on held-out seeds.

## Interpretation limits

Five- and ten-instance pilots are development measurements, not publication
samples. Passing tests validates code properties, not the research hypothesis.
High RCA accuracy does not establish that the transformation is private, and
invariant preservation does not guarantee a model will use the preserved
information correctly.
