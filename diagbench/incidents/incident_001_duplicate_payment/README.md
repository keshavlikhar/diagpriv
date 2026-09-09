# Incident 001 family — internal oracle documentation

This family models one logical payment operation being persisted twice after a
caller-visible response timeout and a second arrival. All identities, events,
and systems are synthetic and fictional.

The directory name, this README, the full `Incident`, structured ground truth,
expected evidence, and invariant annotations are benchmark-oracle information.
They must not be included in model input. Evaluated models may receive only the
result of `Incident.model_view()`.

The checked-in `incident.json` is the canonical development instance for seed
`1001`. Regenerate it with:

```bash
python -m diagbench.generators.incident_001 --seed 1001
```

Other seeds vary bounded nuisance properties while retaining the structured root
cause. Development seeds are 1000–1999, validation seeds are 2000–2999, and
held-out evaluation seeds are 10000–10999.

Version 0.2 removes direct answer wording and diagnostic labels from the model
view, but the incident family has not yet been validated with human or LLM
diagnosticians and should not be treated as representative of production systems.

