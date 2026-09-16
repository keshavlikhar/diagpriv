# Architecture

## Overview

DiagPriv is intentionally small and separates benchmark construction,
model-visible evidence, privacy transformation, provider invocation, and oracle
scoring. The provider-facing path never receives the complete Incident object.

```text
                  oracle-only research boundary
  generator ──> Incident ───────────────────────────────┐
                  │                                     │
                  │ model_view()                        │ scoring/invariants
                  ▼                                     │
              ModelView                                 │
                  │                                     │
       raw / redaction-v1 / hmac-v1                     │
                  ▼                                     │
        transformed ModelView                           │
                  │                                     │
          frozen prompt builder                         │
                  ▼                                     │
             ModelRequest ──> provider ──> parse ───────┤
                                                        ▼
                                              score + manifest JSONL
```

## Packages

### `diagbench`

- `schema/models.py` defines JSON-compatible dataclasses.
- `Incident` contains the full oracle: evidence, ground truths, component
  mappings, privacy annotations, diagnostic invariants, expected evidence, and
  metadata.
- `ModelView` contains only the troubleshooting question, structured evidence,
  and log evidence.
- `generators/incident_001.py` and `generators/incident_002.py` create the two
  deterministic families and enforce their construction scopes.
- `incidents/incident_001_duplicate_payment/incident.json` is the canonical
  development fixture for seed 1001.

Stable neutral `evidence_id` values identify rows and logs. Oracle references use
those IDs so privacy transformations may change diagnostic fields without
breaking provenance or scoring.

### `diagpriv.transformations`

Transformers are pure, offline functions that accept an Incident, start from its
ModelView, consult oracle-only privacy annotations, and return a new ModelView.

- `redaction_v1.py` applies generic source-qualified placeholders.
- `hmac_v1.py` applies canonical, domain-separated HMAC-SHA-256 pseudonyms using
  an externally supplied key.
- `relative_time_v1.py` converts annotated visible timestamps to exact
  incident-local millisecond offsets using one visible-data-derived anchor.

No transformer mutates the Incident. The HMAC key exists only in process
memory and is explicitly excluded from dataclass representations and manifests.

### `diagpriv.invariants`

`evaluate_invariants` resolves oracle references against a transformed
ModelView. It retains the exact predicate result and separately reports:

- `genuine_preservation`;
- `broken`;
- `degenerate_all_to_one`; or
- `expected_non_preservation`.

Invariant data is for offline research reporting and is never added to a model
prompt. Raw timestamp evaluation remains on `temporal-semantics-v1`; relative
offset evaluation must explicitly select `relative-time-semantics-v1`.
Transformation-aware observations use `raw-rca-manifest-v10`, which persists
the transformation/parser configuration and its separately preregistered
canonical SHA-256. The hash is checked during preparation and again before
provider initialization; transformation provenance remains outside ModelView.
Knowing one event's absolute time can allow exact relative offsets to reveal
other events' absolute times, so this layer removes absolute representation but
does not provide complete temporal anonymization.

### `diagpriv.evaluation`

- `prompts/`, `prompt.py`, and `prompt_v2.py`: immutable prompt versions and
  hash verification.
- `incident_families.py`: explicit family routing and frozen family-specific
  evaluation seed sets.
- `taxonomy.py` and `taxonomy_v2.py`: canonical output categories.
- `response.py`: deterministic JSON parsing and schema validation.
- `scoring.py` and `scoring_v2.py`: oracle-based RCA and evidence scoring.
- `providers.py`: provider-neutral protocol, offline fake, and one OpenAI
  Responses adapter.
- `runner.py`: seed protection, incident generation, condition selection,
  prompting, invocation, parsing, scoring, and manifest creation for one run.
- `pilot.py`: TOML loading plus protocol/seed/config validation.
- `manifest.py`: append-only JSONL records with backward-compatible loading;
  schema v6 adds an exact rendered model-input hash for new observations.
- `reporting.py`: split summaries, individual response inspection, usage, and
  cost aggregation.
- `pricing.py`: versioned cost snapshots outside scientific scoring.
- `cli.py`: dry-run, explicitly authorized execution, summary, and inspection.

## Data and secret flow

### Raw and redaction

The CLI loads a reviewed TOML, validates the exact protocol, and passes only
non-secret settings to the runner. The selected transformer returns a ModelView,
which is rendered into the frozen prompt.

### HMAC

The TOML stores only the environment-variable name and a human-assigned,
non-secret key ID. On an explicitly executed run, the CLI reads
`DIAGPRIV_HMAC_KEY_HEX`, validates exactly 32 bytes, and passes the bytes in
memory to `RawRunConfig`. The field has `repr=False` and is never copied into the
manifest. The manifest may contain the non-secret key ID.

The provider credential follows a separate path: `OpenAIResponsesProvider`
reads `OPENAI_API_KEY` only when invoked. Neither secret belongs in ModelRequest,
ModelView, errors, results, or configuration files.

## Versioning and compatibility

- Never edit a frozen prompt or taxonomy in place; add a new version and digest.
- A generator/evidence/oracle change requires benchmark-version review.
- A scoring change requires a new scorer version and must not rescore historical
  records under an incompatible label.
- A transformation semantic change requires a new condition name.
- Historical manifests load without HMAC metadata; HMAC records add only a
  non-secret transformation key ID.
- Result JSONLs are local append-only artifacts and are not tracked by Git.

## Extension points

### Adding a transformation

1. Create a versioned module under `diagpriv/transformations/`.
2. Transform only declared sensitive paths and fail closed.
3. Preserve ModelView shape and exclude oracle metadata.
4. Add condition/config validation and runner dispatch.
5. Add plaintext/key leakage, non-sensitive stability, reproducibility, and
   invariant tests.
6. Complete offline review before provider configuration or execution.

### Adding an incident family

1. Define a deterministic generator and canonical development fixture.
2. Use neutral evidence IDs and complete privacy annotations.
3. Declare positive and negative diagnostic invariants and expected evidence.
4. Prove ModelView/oracle separation and nuisance variation in tests.
5. Audit wording and structure for answer leakage.
6. Add the family and its frozen evaluation seed policy to the reviewed family
   registry; never infer a family from a seed number.

### Adding a provider

Implement the `ModelProvider` protocol without coupling provider response shapes
to generation or scoring. Normalize metadata into `InvocationResult`, sanitize
errors with an allowlist, and do not add retries unless a new experimental
protocol explicitly defines them.

## Current architectural limitations

- The family registry is explicit and currently limited to Incidents 001, 002,
  and the versioned Incident 003 protocols.
- There is no artifact registry or remote results store.
- Key management is an external operator procedure, not a production KMS
  integration.
- Invariant evaluation is an offline audit, not automated transformation
  selection.
- The provider adapter uses the Python standard library and one vendor only.
- Deterministic tokenization and format-preserving pseudonymization exist only
  as fixed experimental baselines. No task-aware DiagPriv selection or
  MCP/product layer exists.
