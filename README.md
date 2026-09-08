# DiagPriv

DiagPriv is an academic research project studying whether operational
troubleshooting evidence can be privacy-transformed without materially reducing
an LLM's root-cause-analysis utility. Its companion benchmark, DiagBench, uses
only fictional, synthetic incidents.

## Current milestone

DiagBench v0.1 contains one carefully designed incident: a duplicate payment
caused by a retry being processed without idempotency protection. The repository
currently provides JSON-compatible incident and diagnostic-invariant models,
deterministic incident generation, research documentation, and validation tests.

## What DiagPriv is not yet

DiagPriv is not currently:

- an enterprise security product;
- an anonymization guarantee;
- a compliance tool;
- an MCP gateway; or
- a production database connector.

It does not yet implement privacy transformations, LLM evaluation, external
integrations, or deployment infrastructure.

## Quick start

Python 3.12 or newer is required.

```bash
python -m pip install -e '.[dev]'
pytest
python -m diagbench.generators.incident_001 --seed 1001
```

The generator command writes the canonical JSON fixture in
`diagbench/incidents/incident_001_duplicate_payment/incident.json`.

## Repository guide

- `docs/` records the research charter, questions, and benchmark contract.
- `diagbench/` defines schemas, synthetic incidents, and deterministic generators.
- `diagpriv/` reserves small modules for future transformations and evaluation.
- `tests/` checks schema round trips and benchmark integrity.
- `experiments/` and `results/` are reserved for later empirical work.

No claim about privacy protection or diagnostic effectiveness is made at this
stage.

