# Contributing to DiagPriv

DiagPriv is a research codebase. A change can alter scientific meaning even when
it is mechanically small, so protocol review and artifact preservation are part
of normal engineering work.

## Setup

Use Python 3.12 or newer:

```bash
uv sync --extra dev
uv run pytest
git diff --check
```

The test suite uses synthetic evidence and an offline fake provider. Running
tests is not permission to execute a real experiment.

## Start every task safely

1. Read `README.md`, `docs/CURRENT_STATUS.md`,
   `docs/EXPERIMENT_PROTOCOL.md`, and `docs/THREAT_MODEL.md`.
2. Inspect `git status`, the recent log, and the exact diff before editing.
3. Preserve unrelated or partially completed changes.
4. Determine whether the task is software-only, a protocol change, or an
   explicitly authorized provider experiment.
5. Keep validation and held-out instances outside ordinary development work.

## Research protocol changes

The following are immutable once used in a frozen observation:

- prompt text and hash;
- taxonomy labels and definitions;
- scorer semantics;
- incident generator, oracle, expected evidence, and invariant definitions;
- transformation semantics;
- seed assignment;
- model/reasoning/temperature configuration; and
- completed JSONL observations.

Do not modify a frozen artifact in place. Create a new named version, document
the reason before observing results, add compatibility tests, and obtain review.
Never rescore an incompatible historical response as if it came from the new
protocol.

Passing tests demonstrates software properties only. Do not describe it as
validation of the research hypothesis, privacy, realism, or model capability.

## Provider execution rules

- No real call without explicit approval for the exact config, seeds, model,
  condition, and result path.
- Review the dry-run output before adding `--execute`.
- Do not retry failures or incorrect cases automatically.
- Do not alter the protocol after seeing an outcome.
- Preserve infrastructure failures separately from RCA observations.
- Summarize, inspect, and hash every completed JSONL before further work.
- Never run validation merely because a development pilot succeeded.
- Never generate or inspect held-out seeds 20000–20999 before final protocol
  freeze and authorization. Never use retired seeds 10000–10999.

## Secrets and local artifacts

Never commit or paste:

- `OPENAI_API_KEY` values;
- `DIAGPRIV_HMAC_KEY_HEX` values;
- Authorization headers;
- `.env` files;
- private keys or certificates; or
- arbitrary provider headers or unsanitized error bodies.

Environment-variable names and human-assigned non-secret key IDs may be tracked.
Public test-vector keys must be explicitly marked non-secret and must never be
reused for experiments.

The repository ignores `.env`, `.env.*`, `.secrets/`, common private-key files,
and `results/*`. Do not force-add them. Frozen local JSONLs are research records,
not scratch files; verify their documented SHA-256 before and after adjacent
work.

Before a commit or push, scan tracked and staged content with a secret scanner
that redacts matches. If a possible match appears, inspect only sanitized
context, determine whether it is a documented placeholder or public fixture,
and stop immediately if it may be real.

## Code expectations

- Prefer small standard-library modules and deterministic behavior.
- Keep transformations pure and fail closed when an annotated field is missing
  or unsupported.
- Preserve non-sensitive evidence byte-for-value unless the new version
  explicitly says otherwise.
- Keep oracle objects, privacy annotations, invariants, and expected evidence out
  of ModelView and prompts.
- Keep provider-specific logic behind `ModelProvider`.
- Keep pricing outside scientific scoring.
- Use `apply_patch` for deliberate edits and avoid destructive Git commands.

## Required tests by change type

### Benchmark or incident

- deterministic same-seed generation;
- nuisance variation across development seeds;
- schema/JSON round trip;
- invariant/reference resolution;
- ModelView/oracle separation;
- answer-leakage audit; and
- protected-seed behavior.

### Privacy transformation

- only annotated fields change;
- sensitive plaintext is absent;
- non-sensitive evidence is unchanged;
- intended equality, inequality, ordering, cardinality, and cross-source identity;
- deterministic reproducibility;
- key/secret non-leakage when applicable;
- complete invariant status; and
- old conditions remain unchanged.

### Prompt, taxonomy, or scorer

- new version and frozen digest;
- canonical-label validation;
- exact-score definition;
- historical-version compatibility; and
- no family-specific oracle answer exposed to the model.

### Provider or manifest

- fake-provider end-to-end coverage;
- allowlisted sanitized errors;
- token and model metadata;
- append-only uniqueness;
- credentials absent from serialized output; and
- no implicit retry.

## Commits and pull requests

Use focused commits with descriptive messages such as `feat:`, `fix:`, `docs:`,
or `test:`. A pull request should state:

- the research or engineering reason;
- files and protocol versions affected;
- whether model-visible evidence changes;
- whether historical results remain comparable;
- seeds generated or inspected;
- whether any provider calls occurred;
- tests and `git diff --check` results;
- secret-scan result; and
- unresolved methodological decisions.

Do not push result artifacts, secrets, or a protocol-changing commit merely to
make a test pass. Ask for research review when scientific interpretation could
change.
