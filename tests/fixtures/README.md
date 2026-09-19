# Software-only fixtures

`synthetic_raw_v1_manifest.json` is hand-authored input for the historical
manifest-format compatibility guard. It is not a captured, regenerated, or
reconstructed provider result. Its experiment ID, model, version, explanation,
fixed timestamp, and absent score explicitly identify its test-only provenance.
The prompt hash is the existing frozen v1 template hash, not a new result hash.

The fixture exercises legacy `model` / `model_version` fields, v1 response
deserialization, and rejection by the v2 scorer. A second test omits explicit
taxonomy/scorer tags to cover legacy defaults. The compatibility test also reads
the original ignored historical file when present, using the same assertions;
malformed present files fail rather than falling back to synthetic data.

Clean-clone success establishes software compatibility only. Exact historical
observations remain local, immutable records; no fixture here certifies their
bytes or replaces their provenance. The separate optional Incident 003 archival
hash/rescoring test remains unchanged. This repair follows the audit in issue
#23. It ships alongside the CI workflow so clean-clone CI can run the full
suite, but it is a software-only fixture and should be reviewed on its own
merits rather than as CI configuration.
