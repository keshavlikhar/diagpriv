# DiagPriv Evaluation Protocol v0.1 — Raw RCA Baseline

## Purpose

The raw baseline asks whether a model can reliably diagnose Incident Family 001
from an unmodified `ModelView`. It measures benchmark diagnosability before any
privacy condition is introduced.

> The raw baseline establishes whether the benchmark is diagnosable before
> measuring the effect of privacy transformations.

Strong raw-baseline performance would not by itself validate the benchmark,
establish production realism, or demonstrate any privacy or transformation
claim. The initial pilot is for debugging the benchmark and protocol rather than
publication-quality inference.

## Pipeline boundary

The raw pipeline separates six stages:

1. deterministic incident generation;
2. prompt construction from `ModelView` only;
3. provider-independent model invocation;
4. structured response parsing;
5. deterministic scoring against oracle annotations; and
6. append-only manifest persistence.

The provider receives a `ModelRequest` containing the rendered prompt, model
identity, version, and decoding settings. It never receives an `Incident` or an
oracle object. No vendor API implementation is included. `FakeProvider` makes
the complete pipeline testable offline.

## Structured model response

The required JSON object is:

```json
{
  "observed_outcome": "concise_snake_case_label",
  "trigger": "concise_snake_case_label",
  "failure_mechanism": "concise_snake_case_label",
  "affected_component": "canonical role or service name visible in the evidence",
  "supporting_evidence": ["evidence_id", "evidence_id"],
  "explanation": "brief evidence-based explanation",
  "confidence": 0.0
}
```

`supporting_evidence` contains model-visible `evidence_id` strings. Confidence is
bounded from 0.0 through 1.0. Explanation is retained for human inspection but is
not the primary scoring target.

The protocol uses deterministic normalization and a small, explicit synonym
table for outcome, trigger, and failure-mechanism labels. Unknown labels remain
recorded and are marked `unknown_category`; they are not interpreted by another
model. The synonym table is implementation-visible in
`diagpriv/evaluation/taxonomy.py` and must be versioned if changed.

## Component names

Incident oracle data contains explicit `ComponentMapping` entries connecting a
canonical conceptual role to service names visible in that generated instance.
The scorer accepts either the canonical role or an associated visible alias.

For example, the canonical `payment_worker` role may map to `ledger-writer` in
one seed and `transaction-processor` in another. This mapping is excluded from
the `ModelView` and prompt.

## Versioned model prompt

Prompt version: `raw-rca-v1`

SHA-256:
`0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd`

Prompt loading verifies this digest and fails if the versioned file changes
without a deliberate version/hash update. Every experiment manifest records both
the version and digest.

```text
Investigate the supplied operational evidence and identify the most likely root cause of the reported incident. Base your diagnosis only on the supplied evidence.

Return exactly one JSON object with these fields:

{
  "observed_outcome": "concise_snake_case_label",
  "trigger": "concise_snake_case_label",
  "failure_mechanism": "concise_snake_case_label",
  "affected_component": "canonical role or service name visible in the evidence",
  "supporting_evidence": ["evidence_id", "evidence_id"],
  "explanation": "brief evidence-based explanation",
  "confidence": 0.0
}

Use a confidence value from 0.0 to 1.0. Every supporting-evidence value must be an evidence_id present in the supplied evidence. Do not add markdown fences or text outside the JSON object.

Operational evidence:
{{MODEL_VIEW_JSON}}
```

The prompt does not mention the project, privacy, transformations, invariants,
oracle categories, expected evidence, or the internal incident-family name.

## Deterministic scoring

Four causal dimensions are scored independently:

- `outcome_correct`;
- `trigger_correct`;
- `failure_mechanism_correct`; and
- `affected_component_correct`.

`exact_root_cause_correct` is true only when all four are correct. This is the
initial primary metric: **Exact Root Cause Accuracy**.

Expected evidence IDs are the unique `evidence_id` selectors appearing in the
oracle's expected-evidence references. Submitted IDs are divided into visible,
matched, and nonexistent sets.

```text
evidence precision = matched expected IDs / all submitted IDs
evidence recall    = matched expected IDs / all expected IDs
evidence F1        = harmonic mean of precision and recall
```

An answer is `evidence_supported` when it cites at least one expected visible ID
and cites no nonexistent ID. `overall_correct` requires both exact root-cause
correctness and `evidence_supported`. Precision, recall, F1, and the exact sets
remain available for stricter later analysis.

Secondary metrics are outcome, trigger, mechanism, and component accuracy plus
evidence precision, recall, and F1. Confidence calibration is deferred until a
sufficient sample and a calibration analysis plan exist.

No LLM grader is used by the primary scoring path.

## Initial real-provider adapter

`OpenAIResponsesProvider` is the single initial real-provider implementation. It
implements the same `ModelProvider` protocol as `FakeProvider` and uses the
Responses API through the Python standard library. Benchmark generation,
prompting, parsing, scoring, and persistence contain no provider-specific logic.

The adapter reads `OPENAI_API_KEY` only at invocation time. An optional
`OPENAI_BASE_URL` may select a compatible endpoint. Neither value is placed in a
model request, response object, experiment manifest, error message, or committed
configuration. Requests set `store` to `false`, send the selected model and raw
prompt as text input, and include temperature or maximum output tokens only when
configured. Responses are parsed by collecting `output_text` content from
message output items rather than assuming the first output item is text.

HTTP 429 is recorded as `rate_limited`. Other HTTP, network, timeout, response-
status, and JSON-decoding failures are recorded as `provider_error` without
persisting response bodies or credentials. The adapter does not retry, so each
configured call remains exactly one provider invocation.

## Failure handling

Every invocation produces a manifest, except a run rejected before invocation by
the seed safeguard. Response status is one of:

- `valid`;
- `malformed_json`;
- `missing_fields`;
- `invalid_schema`;
- `unknown_category`;
- `refusal`;
- `empty_response`; or
- `provider_error`.

Raw provider output and an error description are retained. Responses that can be
parsed structurally may receive component scores even when a category is unknown.
Failures without a structured response have a null score and are never silently
dropped. Nonexistent evidence IDs are retained in `unknown_evidence_ids` and
reduce evidence precision and overall support.

## Experiment manifests and persistence

Each manifest records:

- experiment ID;
- benchmark version and internal incident family;
- seed and split;
- the fixed `raw` condition;
- model and model version;
- prompt version;
- prompt SHA-256;
- decoding settings;
- timestamp;
- raw and parsed response status; and
- component and evidence score, when available.

JSONL persistence is append-only. An experiment ID already present in a result
file is rejected instead of overwritten or duplicated. Reproducible runs require
recording exact provider model versions, decoding settings, benchmark version,
prompt version, seed, environment, and any provider-side determinism controls.

## Seed and split policy

- Development seeds `1000–1999` may be used for prompt and harness debugging.
- Validation seeds `2000–2999` may be used for early benchmark measurements and
  protocol selection.
- Seeds `10000–10999` are retired and cannot be invoked.
- Final held-out evaluation seeds `20000–20999` require `allow_held_out=True` and
  are rejected before incident generation by normal commands.
- Unassigned seeds are rejected by the evaluation runner.

The versioned `experiments/raw_pilot_v1.toml` plan selects development seeds
1000–1004 and validation seeds 2000–2009, with no held-out seeds. It configures
the raw condition, temperature zero, one model, and one call per seed. Model and
model-version values come from `DIAGPRIV_MODEL` and
`DIAGPRIV_MODEL_VERSION`; credentials remain separate in `OPENAI_API_KEY`.

Held-out evidence is protected so prompt wording, normalization rules, scoring
choices, and future transformation settings cannot be tuned against final
evaluation instances. An override exists for an explicitly authorized final run,
not for routine development.

The old range was retired before any LLM evaluation because the required v0.2
construction audit had mechanically generated seeds 10000–10049. No instance
from the replacement 20000–20999 range was generated or inspected while
preparing the first pilot. The safeguard test replaces generation with a failing
sentinel and verifies a normal run is rejected first.

## Pilot commands and reporting

Omitting `--execute` prints the validated plan without calling a provider:

```bash
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/raw_pilot_v1.toml \
  --results results/raw_pilot_v1.jsonl
```

A real run additionally requires the explicit `--execute` flag and environment
configuration:

```bash
export OPENAI_API_KEY='set-outside-the-repository'
export DIAGPRIV_MODEL='provider-model-id'
export DIAGPRIV_MODEL_VERSION='immutable-provider-model-version'
uv run python -m diagpriv.evaluation.cli run-pilot \
  --config experiments/raw_pilot_v1.toml \
  --results results/raw_pilot_v1.jsonl \
  --execute
```

Summaries can be generated before, during, or after a pilot:

```bash
uv run python -m diagpriv.evaluation.cli summarize \
  --results results/raw_pilot_v1.jsonl
```

Development and validation are reported separately. Accuracy and valid-response
rates use all runs in the split as the denominator, so parsing/provider failures
do not disappear from the headline rate. Evidence averages use responses that
produced a structured score. Parse failures, provider failures, rate limits, and
refusals are counted separately. A split with no results is reported as
`pending`, with null rates rather than artificial zeros.

## Initial limitations

The response taxonomy and synonym table require research review. Evidence-support
criteria may be too permissive because one matched ID is sufficient. Exact model
selection, provider-side determinism, rate-limit policy, blind grading, pilot
interpretation, and statistical analysis remain unresolved. Human validation of
incident difficulty and evidence sufficiency is still required before real model
results are interpreted.
