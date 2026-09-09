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

The provider rejected the originally intended `temperature=0` parameter. The
request therefore omits temperature entirely, while manifests retain the
intended value and the reason for omission. Do not substitute another decoding
parameter silently.

The historical manifest/config field named `prompt_sha256` is specifically the
SHA-256 of the frozen UTF-8 `raw_rca_v2.txt` **template before**
`{{MODEL_VIEW_JSON}}` is replaced. It is identical across observations using
that template and must not be interpreted as a digest of the fully rendered
provider request. Renaming the persisted field now would be backward
incompatible with frozen results; documentation therefore refers to it as the
prompt-template hash while preserving the field and its meaning.

A future, versioned manifest schema may add a separate
`rendered_request_sha256` (or `model_input_sha256`) computed over the exact
provider-bound prompt. Such a field would strengthen per-observation provenance
without changing or retroactively augmenting historical records. It has not
been added in the current schema.

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
