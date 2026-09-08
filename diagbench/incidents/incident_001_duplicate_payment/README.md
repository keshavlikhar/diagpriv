# Incident 001 — Duplicate Payment

This fixture is entirely fictional. It describes a retry processed twice because
the synthetic payment worker lacks an idempotency check. Regenerate
`incident.json` with:

```bash
python -m diagbench.generators.incident_001 --seed 1001
```

