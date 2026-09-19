# Fresh-clone reproducibility audit

Issue #23. Re-audited on 2026-09-19 against the tree this pull request
actually proposes: commit `9834cdb1a4bc7240eded24f7075cacdf1784a020`, which merges current main
`c85477456d39dc2f7dab0a118b154dd3da5295c4` (including the evidence-support v5
work from PR #28) into the combined issue 21–27 branch.

That commit is the code tree under audit. Later commits on the branch change
only this document and `.github/CODEOWNERS`, so they cannot affect the suite
result; GitHub CI on the pull-request head is the authoritative verification and
its run is linked from the pull-request description.

This report changes no test, fixture, result, scorer, or frozen hash. The
synthetic-fixture repair it recommends is included in the same pull request and
is described as shipped, not proposed. The original pre-repair audit of commit
`b01ea3b` is preserved in
[Pre-repair baseline](#pre-repair-baseline-historical-record) for comparison.

## Result

A clean clone of the proposed tree installs successfully and its complete test
suite passes: **790 passed, 2 skipped, 0 failed, 0 deselected** (792 collected),
in 84.42s. `git diff --check`, the redacted tracked-file secret scan, and
`git status --porcelain` are all clean afterwards, and `git ls-files results`
returns only `results/.gitkeep`.

Both skips are declared, optional archival checks that require ignored frozen
observations; neither was introduced to make this suite green:

- `tests/test_incident_003_destructive_baselines.py` skips its two-file
  Incident 003 v2 integrity/rescoring check (pre-existing).
- `tests/test_evidence_support_v5.py` skips its Stage-1 v5 secondary-rescore
  check, which arrived with PR #28 after the original audit.

No test fails on a missing artifact any more. The previously failing v1
compatibility guard now runs in every clone against a tracked synthetic
manifest, and additionally against the real historical file when it is present.

## Pre-repair baseline (historical record)

The first audit of this issue ran at commit
`b01ea3be330f542dab62d10ac93e753934a626a1`, before the repair and before PR #28
merged. It found **746 passed, 1 failed, 1 skipped, 0 deselected** (748
collected). The single failure was an unconditional read of an ignored
historical v1 JSONL by
`tests/test_evaluation_v2.py::test_historical_v1_result_cannot_be_scored_as_v2`.
An authenticated GitHub Linux run on that commit independently reported the same
counts:
[CI run 35415619004](https://github.com/keshavlikhar/diagpriv/actions/runs/35415619004).
CI correctly failed closed on the missing artifact, which is the gap the
included repair closes.

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
  --branch fixes/issues-21-27-ci-collaboration-research "$repo_source" "$audit_root/repo"
cd "$audit_root/repo"
git checkout --detach 9834cdb1a4bc7240eded24f7075cacdf1784a020
env UV_CACHE_DIR=/tmp/diagpriv-uv-cache uv sync --python 3.12 --extra dev
env -u OPENAI_API_KEY -u DIAGPRIV_HMAC_KEY_HEX \
  UV_CACHE_DIR=/tmp/diagpriv-uv-cache uv run pytest -ra
git diff --check
git status --porcelain
git ls-files results
```

The detached checkout is a reproducibility pin; the audited clone already had
that HEAD. The same sequence, with the branch and commit substituted, produced
the pre-repair baseline above. The local run used macOS arm64, Python 3.12.13,
uv 0.12.1, and pytest 9.1.1 from the existing lockfile. Dependency installation used registry access;
tests ran with provider/HMAC environment variables removed. Existing fake
providers and synthetic public keys satisfy test inputs. No provider call or
new research experiment was performed. Protected-seed rejection/configuration
tests do not authorize protected-instance generation.

`git status --porcelain` and `git diff --check` returned no output after the
suite. `git ls-files results` returned only `results/.gitkeep`. The four
historical paths below were confirmed ignored with `git check-ignore`.
Tests use development constructions already defined by the test suite; no new
sampling, validation data inspection, or held-out construction was performed.

## Missing-artifact dependency inventory

All paths in this table are relative to the repository root.

| Artifact | Dependent test and behavior | Classification |
|---|---|---|
| `results/raw_pilot_v1_gpt_5_6_luna_medium_temperature_omitted_diagnostic_seed_1000.jsonl` | Was read unconditionally by `tests/test_evaluation_v2.py::test_historical_v1_result_cannot_be_scored_as_v2`, which failed before any assertion. **Repaired in this PR:** `test_v1_manifest_cannot_be_scored_as_v2` is parameterized over a tracked synthetic manifest plus this file when present, keeping the same protocol-tag, response-type, and v2-rejection assertions. | Historical observation intentionally local. The packaging gap is closed: the guard now runs in every clone without asserting anything about these bytes. |
| `results/incident_003_v2_raw_sol_development_gpt_5_6_sol_medium.jsonl` | `tests/test_incident_003_destructive_baselines.py::test_frozen_historical_jsonls_are_unmodified_and_v3_reproducible` requires both files, verifies SHA-256 and v3 score fields; skips if either is absent. | Expected-local archival validation, explicitly optional in the existing suite. Clean CI cannot certify these historical bytes. |
| `results/incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl` | Same two-file archival test; one present file is not checked when the other is missing. | Expected-local archival validation; all-or-none coverage is a disclosed limitation. |
| `results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl` | Added by PR #28. `tests/test_evidence_support_v5.py::test_v5_secondary_rescore_is_explicit_and_does_not_mutate_history` is `skipif`-guarded on its absence; when present it verifies SHA-256 `b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`, runs the v5 secondary rescore, and asserts the bytes are unchanged afterwards. | Expected-local archival validation, declared optional at the test. Clean CI cannot certify these historical bytes. |

The Incident 003 v2 archival test embeds SHA-256 values
`54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915`
and `0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb`
respectively. They agree with the tracked ledger; the absent bytes were not
reconstructed or independently verified. The same holds for the v3 Stage-1
digest above. The v1 compatibility test contains no digest check; neither this
audit nor the included fixture invents a historical digest.

There is also an inverse dependency on ignored-file **absence** in
`tests/test_incident_003_v3_qualification.py` and `tests/test_incident_003_v3.py`.
The three paths involved are
`results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl`,
`results/incident_003_v3_relative_time_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl`,
and `results/incident_003_v3_temporal_ablation_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl`.

The original audit recorded that all three were asserted absent, which meant a
research checkout holding later observations could fail a purely software check.
PR #28 has since narrowed that:

- `test_paired_configs_are_isolated_and_preregister_eight_cases` now allows the
  raw path to exist and pins it to SHA-256
  `b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2`; the other
  two conditions are still asserted absent because they are unexecuted.
- `test_result_paths_are_unique_ignored_untracked_and_unexecuted_paths_absent`
  applies the same split, and `test_v3_preparation_has_only_reviewed_configs_and_no_tracked_result`
  additionally requires any present v3 artifact to be Git-ignored and untracked.

A fresh clone passes either way, since none of the three exist. The residual
caveat is unchanged for the two unexecuted conditions: do not delete
observations to make a research checkout pass. Run software verification from an
isolated clone and review lifecycle assertions separately.

## Inventory method and exclusions

Searched all tracked `tests/` sources for JSONL/results paths and file operations
(`read_text`, `read_bytes`, `open`, `is_file`, `exists`, globbing, and skips),
then traced constants and fixture setup. The re-audit repeated this search over
the merged tree, including the `tests/test_evidence_support_v5.py` suite added
by PR #28. At the audited commit, the dependencies above are the only tests
found that require real ignored historical bytes or root-level result absence.
No missing-artifact failure or deselection was observed. Scope is the committed
suite at this exact revision, not all possible analysis commands.

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
- The PR #28 evidence-support v5 tests construct citations, rubrics, and model
  views in-process; only the single Stage-1 rescore check listed above touches
  an ignored artifact, and it is `skipif`-guarded.
- Reading `.gitignore`, prompt templates, TOML configs, and canonical tracked
  incident fixtures is a tracked dependency, not missing local research data.

The repository's full research reproducibility also requires access to frozen
observations in its ledger. A green software suite alone cannot establish that
those observations are available, authentic, or scientifically reproducible.

## Repair alternatives and implications

| Alternative | Benefit | Research/review implication |
|---|---|---|
| Publish a separately reviewed immutable archive with verified provenance and digests | Makes exact historical verification possible in a controlled artifact workflow | Requires access/distribution decisions and review of contents. Do not silently copy JSONLs into Git or require provider credentials for CI. |
| Supply an explicitly synthetic, tracked v1 manifest for the protocol compatibility test; additionally check the real file when available | Makes v1 parsing/version/type rejection executable in every clone without claiming historical provenance | **Adopted, and included in this pull request.** All original version/type/rejection assertions are retained, legacy field defaults are covered by a new test, and clean CI proves protocol behavior only, not historical-byte integrity. |
| Skip the failing test, deselect it, or use `continue-on-error` | Makes the check appear green without exercising the guard | Reject: conflicts with #21 and loses clean-clone compatibility coverage. |
| Regenerate or fabricate a historical provider response | Produces a file with the expected name | Reject: destroys provenance and cannot recover the original observation. |

## What this pull request implements

The adopted repair ships here rather than separately, so that CI can run the
complete suite from a clean clone:

- `tests/fixtures/synthetic_raw_v1_manifest.json`, a hand-authored manifest whose
  experiment ID, model, version, explanation, fixed timestamp, and absent score
  mark it as test-only input. Its provenance is documented in
  `tests/fixtures/README.md`. It reuses the existing frozen `raw-rca-v1` prompt
  hash and introduces no new result hash.
- `tests/test_evaluation_v2.py::test_v1_manifest_cannot_be_scored_as_v2`,
  parameterized over the synthetic manifest and, when present, the real
  historical file. A malformed present file fails rather than falling back to
  the fixture.
- `tests/test_evaluation_v2.py::test_legacy_v1_manifest_defaults_cannot_promote_response_to_v2`,
  covering legacy taxonomy/scorer defaults and legacy model fields.

No historical JSONL was copied, rewritten, regenerated, or added, and no
existing archival hash check was weakened, skipped, or deselected.

Still outstanding: a separate artifact-distribution decision is needed before
collaborators can verify historical bytes on their own machines. Clean CI
establishes software compatibility only. The two optional archival checks remain
skipped wherever those observations are absent, which is the intended behavior.
