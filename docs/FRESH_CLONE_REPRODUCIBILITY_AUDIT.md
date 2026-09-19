# Fresh-clone reproducibility audit

Issue #23, phase 1: audit only. Audited on 2026-09-19 at commit
`b01ea3be330f542dab62d10ac93e753934a626a1` (PR #29), whose tests/research code
match main `85e0c1a`. The only intervening changes are under `.github/`.
This report changes no test, fixture, result, scorer, or frozen hash.

> **Status:** the synthetic-fixture repair recommended under
> [Repair alternatives](#repair-alternatives-and-implications) ships in the same
> pull request as this audit. It renames the dependent test to
> `test_v1_manifest_cannot_be_scored_as_v2`, adds
> `tests/fixtures/synthetic_raw_v1_manifest.json` (see `tests/fixtures/README.md`),
> and changes no other finding below. The audit body records the pre-repair state
> at the audited commit.

## Result

A clean clone installs successfully but its complete test suite fails:
**746 passed, 1 failed, 1 skipped, 0 deselected** (748 collected), in 84.41s.
The failure is an unconditional read of an ignored historical v1 JSONL.
The skip is an existing optional two-file historical integrity/rescoring test.

The authenticated GitHub Linux run on the same commit independently reported
the same counts in 194.68s:
[CI run 35415619004](https://github.com/keshavlikhar/diagpriv/actions/runs/35415619004).
All setup, whitespace, secret-scan, and dependency-install steps passed there.
CI correctly fails closed on the missing artifact.

## Clean-clone commands and environment

The audit used a separate local transport clone with `--no-local`, which copies
committed Git objects only, not the working directory, ignored results, existing
virtual environment, or untracked fixtures. No historical artifact was supplied.
Commands below reproduce the executed sequence; the source repository path and
random temporary suffix are parameterized for portability.

```bash
repo_source="$(git rev-parse --show-toplevel)"
audit_root="$(mktemp -d /tmp/diagpriv-clean-audit.XXXXXX)"
git clone --no-local --single-branch \
  --branch fixes/issues-21-22-ci-collaboration "$repo_source" "$audit_root/repo"
cd "$audit_root/repo"
git checkout --detach b01ea3be330f542dab62d10ac93e753934a626a1
env UV_CACHE_DIR=/tmp/diagpriv-uv-cache uv sync --python 3.12 --extra dev
env -u OPENAI_API_KEY -u DIAGPRIV_HMAC_KEY_HEX \
  UV_CACHE_DIR=/tmp/diagpriv-uv-cache uv run pytest -ra
git diff --check
git status --porcelain
git ls-files results
```

The detached checkout is a reproducibility pin; the audited clone already had
that HEAD. The local run used macOS arm64, Python 3.12.13, uv 0.12.1, and pytest
9.1.1 from the existing lockfile. Dependency installation used registry access;
tests ran with provider/HMAC environment variables removed. Existing fake
providers and synthetic public keys satisfy test inputs. No provider call or
new research experiment was performed. Protected-seed rejection/configuration
tests do not authorize protected-instance generation.

`git status --porcelain` and `git diff --check` returned no output after the
suite. `git ls-files results` returned only `results/.gitkeep`. The three
historical paths below were confirmed ignored with `git check-ignore`.
Tests use development constructions already defined by the test suite; no new
sampling, validation data inspection, or held-out construction was performed.

## Missing-artifact dependency inventory

All paths in this table are relative to the repository root.

| Artifact | Dependent test and behavior | Classification |
|---|---|---|
| `results/raw_pilot_v1_gpt_5_6_luna_medium_temperature_omitted_diagnostic_seed_1000.jsonl` | `tests/test_evaluation_v2.py::test_historical_v1_result_cannot_be_scored_as_v2` reads it unconditionally, parses the manifest, checks v1 protocol tags/response type, and expects v2 rejection. Fails before any assertion. | Historical observation intentionally local; unconditional software-test dependency is a packaging/reproducibility gap. |
| `results/incident_003_v2_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `tests/test_incident_003_destructive_baselines.py::test_frozen_historical_jsonls_are_unmodified_and_v3_reproducible` requires both files, verifies SHA-256 and v3 score fields; skips if either is absent. | Expected-local archival validation, explicitly optional in the existing suite. Clean CI cannot certify these historical bytes. |
| `results/incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl` | Same two-file archival test; one present file is not checked when the other is missing. | Expected-local archival validation; all-or-none coverage is a disclosed limitation. |

The archival test embeds SHA-256 values
`54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915`
and `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb`
respectively. They agree with the tracked ledger; the absent bytes were not
reconstructed or independently verified. The v1 test contains no digest check;
this audit does not invent a historical digest.

There is also an inverse dependency on ignored-file **absence** in
`tests/test_incident_003_v3_qualification.py`:

- `test_paired_configs_are_isolated_and_preregister_eight_cases` (three condition
  parameters) asserts each planned result path is absent.
- `test_result_paths_are_unique_ignored_untracked_and_absent` checks all three.

Those paths are `results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl`,
`results/incident_003_v3_relative_time_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl`,
and `results/incident_003_v3_temporal_ablation_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl`.
They are expected absent in the audited preparation snapshot, so a fresh clone
passes these tests. A research checkout containing later observations can fail
them. Do not delete observations to make such a checkout pass; run software
verification from an isolated clone and review lifecycle assertions separately.

## Inventory method and exclusions

Searched all tracked `tests/` sources for JSONL/results paths and file operations
(`read_text`, `read_bytes`, `open`, `is_file`, `exists`, globbing, and skips),
then traced constants and fixture setup. At the audited commit, the dependencies
above are the only tests found that require real ignored historical bytes or
root-level result absence. No additional missing-artifact failure/deselection
was observed. Scope is the committed suite at this exact revision, not future
PR #28 tests or all possible analysis commands.

Other matches are intentionally self-contained:

- Raw, HMAC, tokenization, format, relative-time, and CLI tests write synthetic
  records to pytest temporary directories or assert dry runs create no file.
- Incident 002 raw/Sol/privacy/repeated-trial tests use tracked configs and
  preregistered hashes; their result names are redirected into `tmp_path`.
- `test_incident_002_transport_recovery.py::source_fixture` constructs explicitly
  synthetic FakeProvider inputs and test-specific hashes in temporary paths.
  It does not consume or rewrite the frozen local recovery observations.
- `test_incident_003_evaluation.py`, `test_incident_003_v2.py`, and destructive
  CLI checks use tracked configuration or temporary result paths, apart from
  the archival test listed above.
- Reading `.gitignore`, prompt templates, TOML configs, and canonical tracked
  incident fixtures is a tracked dependency, not missing local research data.

The repository's full research reproducibility also requires access to frozen
observations in its ledger. A green software suite alone cannot establish that
those observations are available, authentic, or scientifically reproducible.

## Repair alternatives and implications

| Alternative | Benefit | Research/review implication |
|---|---|---|
| Publish a separately reviewed immutable archive with verified provenance and digests | Makes exact historical verification possible in a controlled artifact workflow | Requires access/distribution decisions and review of contents. Do not silently copy JSONLs into Git or require provider credentials for CI. |
| Supply an explicitly synthetic, tracked v1 manifest for the protocol compatibility test; additionally check the real file when available | Makes v1 parsing/version/type rejection executable in every clone without claiming historical provenance | Recommended separate software repair. Retain all original version/type/rejection assertions and test legacy field defaults. Disclose that clean CI proves protocol behavior, not historical-byte integrity. |
| Skip the failing test, deselect it, or use `continue-on-error` | Makes the check appear green without exercising the guard | Reject: conflicts with #21 and loses clean-clone compatibility coverage. |
| Regenerate or fabricate a historical provider response | Produces a file with the expected name | Reject: destroys provenance and cannot recover the original observation. |

Recommendation: review the synthetic software fixture repair in a separate PR,
clearly name its provenance, keep historical inputs immutable, and preserve the
existing archival hash check. A second, later artifact-distribution decision
is still needed to certify historical bytes on collaborators' machines.
No repair or fixture is included in this phase-1 audit document.
