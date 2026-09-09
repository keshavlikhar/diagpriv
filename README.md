# DiagPriv

DiagPriv is an academic research project studying whether operational
troubleshooting evidence can be privacy-transformed without materially reducing
an LLM's root-cause-analysis utility. Its companion benchmark, DiagBench, uses
only fictional, synthetic incidents.

## Current milestone

DiagBench v0.2 turns Incident 001 into a bounded synthetic incident family and
strictly separates research-oracle annotations from the evidence visible to a
future evaluated model. The repository provides structured RCA ground truth,
element-scoped diagnostic invariants, deterministic generation, explicit seed
splits, research documentation, and experimental-validity tests. Evaluation
Protocol v0.1 adds a provider-independent, offline-testable raw RCA baseline
harness; it does not invoke a real model by default.

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

The generator command writes the canonical development JSON fixture in
`diagbench/incidents/incident_001_duplicate_payment/incident.json`.

## Repository guide

- `docs/` records the research charter, questions, and benchmark contract.
- `diagbench/` defines schemas, synthetic incidents, and deterministic generators.
- `diagpriv/` reserves small modules for future transformations and evaluation.
- `diagpriv/evaluation/` contains the raw prompt, response parser, deterministic
  scorer, provider contract, runner, and append-only manifest support.
- `tests/` checks schema round trips and benchmark integrity.
- `experiments/` and `results/` are reserved for later empirical work.

No claim about privacy protection, benchmark validation, production realism, or
diagnostic effectiveness is made at this stage.
