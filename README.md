# DiagPriv

DiagPriv is an academic research project studying whether privacy
transformations can remove sensitive identity from operational troubleshooting
evidence while retaining the relationships an LLM needs for root-cause
analysis (RCA). Its companion benchmark, DiagBench, contains three fully
synthetic incident families; no production or customer data is used.

The central hypothesis is that a transformation which preserves explicitly
declared diagnostic invariants will retain more RCA utility than conventional
redaction at comparable privacy exposure. Current results are early pilot
observations, not proof of that hypothesis or evidence of production validity.

## Current status

| Condition | Split | Status | Result |
|---|---|---|---|
| Raw, `raw-rca-v2` | Development 1000–1004 | Frozen | 5/5 exact RCA; 5/5 overall |
| Raw, `raw-rca-v2` | Validation 2000–2009 | Frozen | 10/10 exact RCA; 9/10 overall |
| `redaction-v1` | Development 1000–1004 | Frozen | 4/5 exact RCA; 4/5 overall |
| `hmac-v1` | Development 1000–1004 | Frozen | 5/5 exact RCA |
| `tokenization-v1` | Development 1000–1004 | Frozen | 5/5 exact RCA |
| `format-preserving-v1` | Development 1000–1004 | Frozen | 4/5 exact RCA |

Incident Family 002 is a reviewed synthetic benchmark in which reference
structure is deliberately necessary to diagnose a missing provisioning effect.
Its six-seed, five-condition, three-trial development comparison and separate
transport-recovery sensitivity analysis are complete and frozen. Raw achieved
15/18 correct triggers and failure mechanisms; format-preserving-v1 achieved
10/18; redaction-v1, HMAC-v1, and tokenization-v1 achieved 2/18, 1/18, and 2/18
respectively. These are directional development observations, not causal or
general conclusions. No Incident 002 validation or held-out observation exists.
Do not rerun completed experiments, run a privacy condition on validation, or
inspect held-out seeds without explicit research approval.

Incident Family 003 studies temporal causality. Its frozen v1 raw Sol development
run recovered the temporal chain in all eight observations but scored 0/8 exact
under RCA v2 because every response selected `incorrect_concurrency_control`
instead of the v1 oracle's `incorrect_state_transition`. Offline adjudication
classified the disagreement as taxonomy ambiguity. RCA v3 is implemented as a
separate protocol with an Incident 003 v2 wrapper and fresh development set.
The frozen fresh raw run achieved 8/8 exact RCA but 0/8 evidence-supported
diagnoses under the unchanged v3 citation rubric. `relative-time-v1` is
implemented and audited offline; it has not been sent to a provider. No
Incident 003 privacy, validation, or held-out observation exists.

See [CURRENT_STATUS](docs/CURRENT_STATUS.md) for immutable artifact hashes and
known limitations, and [RESEARCH_PLAN](docs/RESEARCH_PLAN.md) for the roadmap.

## Reproduce the software checks

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) are recommended.

```bash
uv sync --extra dev
uv run pytest
git diff --check
```

Tests use an offline fake provider. They do not authorize real API calls. The
canonical development fixture can be regenerated with:

```bash
uv run python -m diagbench.generators.incident_001 --seed 1001
uv run python -m diagbench.generators.incident_002 --seed 1001
```

## Repository map

- `diagbench/schema/`: oracle and model-visible data models.
- `diagbench/generators/`: deterministic synthetic incident generation and seed
  policy.
- `diagbench/incidents/`: canonical generated fixtures and family notes.
- `diagpriv/evaluation/`: frozen prompts and taxonomies, provider abstraction,
  parsing, scoring, manifests, reporting, and CLI.
- `diagpriv/transformations/`: annotation-driven privacy baselines.
- `diagpriv/invariants/`: offline diagnostic-invariant evaluation.
- `experiments/`: versioned, reviewable pilot and pricing configurations.
- `results/`: local append-only experiment artifacts; ignored by Git except for
  `.gitkeep`.
- `tests/`: benchmark, protocol, transformation, and leakage regression tests.

## Collaboration documents

- [Research plan](docs/RESEARCH_PLAN.md)
- [Current status and artifact ledger](docs/CURRENT_STATUS.md)
- [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md)
- [Incident 003 v1 raw findings](docs/INCIDENT_003_V1_RAW_FINDINGS.md)
- [RCA v3 methodology decision](docs/RCA_V3_METHODOLOGY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Contributing guide](CONTRIBUTING.md)
- [Benchmark specification](docs/benchmark_spec.md)
- [Research charter](docs/research_charter.md)
- [Research questions](docs/research_questions.md)
- [Naive redaction specification](docs/redaction_v1.md)
- [HMAC baseline specification](docs/hmac_v1.md)
- [Tokenization baseline specification](docs/tokenization_v1.md)
- [Format-preserving baseline specification](docs/format_preserving_v1.md)
- [Relative-time baseline specification](docs/relative_time_v1.md)
- [Incident 002 protocol](docs/incident_002_protocol.md)
- [Incident 002 final development findings](docs/INCIDENT_002_FINAL_FINDINGS.md)

## Safety and scope

- Never commit API credentials, HMAC secrets, `.env` files, or authorization
  headers.
- Evaluated models receive `ModelView`, never the full oracle-bearing
  `Incident`.
- Development seeds are 1000–1999; validation seeds are 2000–2999; the retired
  range 10000–10999 must never be used; final held-out seeds 20000–20999 require
  an explicit override after protocol freeze.
- Real provider commands require `--execute`. Absence of that flag is a dry run.
- Frozen JSONL observations are append-only research records and must not be
  edited or silently rerun.

DiagPriv is not an anonymization guarantee, compliance tool, production privacy
gateway, MCP service, or enterprise security product.
