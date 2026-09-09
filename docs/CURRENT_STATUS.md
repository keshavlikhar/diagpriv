# Current Status

Last updated: 2026-09-09.

## Handoff point

The repository is on `feat/format-preserving-v1`. The offline implementation,
tests, development configuration, and protocol documentation are complete. The
five-seed development observation has been reviewed and frozen; the branch is
ready for a code/documentation checkpoint and later pull-request review.

No format-preserving validation or held-out provider observation exists. Do not
rerun the development observation or tune the transformation after its 4/5
result.

## Frozen protocol

- Benchmark: DiagBench `0.2`, Incident Family 001.
- Prompt: `raw-rca-v2`.
- Prompt-template SHA-256:
  `744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d`.
- Taxonomy: `rca-taxonomy-v2`.
- Scorer: `raw-rca-scorer-v2`.
- Model: `gpt-5.6-luna`.
- Reasoning effort: `medium`.
- Temperature: originally intended as zero, but omitted because the provider
  rejected the parameter for this model/configuration.
- Calls per seed: one.

The historical field `prompt_sha256` records the frozen prompt-template bytes,
not the rendered prompt containing a particular ModelView. See
`docs/EXPERIMENT_PROTOCOL.md` for the compatibility and future-provenance note.

Exact RCA v2 requires all five canonical dimensions to be correct:
`observed_outcome`, `trigger`, `subsequent_action`, `failure_mechanism`, and
`affected_component`. `overall_correct` additionally requires supported
evidence under the frozen deterministic evidence scorer.

## Frozen observations

These are small development/validation observations, not general research
conclusions.

| Condition | Seeds | Valid | Exact RCA | Status |
|---|---:|---:|---:|---|
| Raw v2 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Raw v2 validation | 2000–2009 | 10/10 | 10/10 | Frozen; 9/10 overall |
| Redaction v1 development | 1000–1004 | 5/5 | 4/5 | Frozen |
| HMAC v1 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Tokenization v1 development | 1000–1004 | 5/5 | 5/5 | Frozen |
| Format-preserving v1 development | 1000–1004 | 5/5 | 4/5 | Frozen |

For `format-preserving-v1`, outcome, trigger, subsequent action, and failure
mechanism were each correct in 5/5 cases. Seed 1000 was the only exact-RCA miss:
the response selected `request_ingress` rather than the oracle
`operation_executor`. Evidence precision was 1.0000, recall was approximately
0.742857, and F1 was approximately 0.848018. Total usage was 23,918 tokens and
estimated cost under the configured pricing snapshot was $0.00840885. No
provider, parser, rate-limit, or refusal failure occurred.

The component disagreement is retained as an observation. It does not justify
changing the oracle or any post-observation protocol element.

## Component-ownership interpretation

The v2 prompt defines `affected_component` as the architectural role that owns
the failure mechanism, not a component that merely reports a symptom. Incident
001 shows the ingress/edge handler accepting arrivals and reporting the
caller-facing deadline. The operation executor/payment worker then persists two
distinct successful effects for the same logical request. Missing or ineffective
idempotency is therefore assigned to `operation_executor`: that is the role that
must prevent a repeated arrival from producing the second durable effect.

`request_ingress` is nevertheless a plausible model-sensitive localization
because it observes the timeout and accepts the re-arrival. Component ownership
should be evaluated across models and repeated trials after the protocol is
extended; it may be less stable than outcome, trigger, subsequent action, or
mechanism. This is a research caution, not an oracle revision.

## Frozen local artifact ledger

Experiment JSONLs are ignored by Git and remain local append-only research
records. Their contents must not be edited or regenerated under the same
experiment IDs.

| Artifact | SHA-256 |
|---|---|
| `results/raw_pilot_v2_gpt_5_6_luna_medium.jsonl` | `dbf72a9a3d3e33e510622e3eab9df11d4e5c138d35fb89c6ed04e1ccdde4ab2b` |
| `results/raw_pilot_v2_validation_gpt_5_6_luna_medium.jsonl` | `c9d4cfa93c3176590ad820484266843c464e8a58f92994beebf7d10548c6028e` |
| `results/redaction_v1_development_gpt_5_6_luna_medium.jsonl` | `b3a885a65e9369a26e9cdb69b7fcc1244739cee0812d6313040a3f03203b1559` |
| `results/hmac_v1_development_gpt_5_6_luna_medium.jsonl` | `063137ee4c29d5f2ef0c6688754a485822b45d4434b4c16cdb0f2476a36508e3` |
| `results/tokenization_v1_development_gpt_5_6_luna_medium.jsonl` | `acb9d5fb53b8177c6b5dac954569fda6c0b74f25b7e479f6b393cc0ce33b6695` |
| `results/format_preserving_v1_development_gpt_5_6_luna_medium.jsonl` | `3b32fff6fc7604afec2e467f18f850ffafa89c63633e0155b8cfc397fa9e1fa9` |

Earlier raw-v1 HTTP failures and the seed-1000 taxonomy diagnostic remain local
infrastructure/development history. The HTTP 400 attempts are not RCA
observations. The v1 taxonomy finding motivated a separately versioned v2
protocol; v1 was not overwritten.

## Methodological interpretation

Incident 001 requires equality, inequality, cross-source identity, ordering,
success state, amount equality, and row cardinality. It does not require
sensitive-value format for diagnosis. Consequently, the current result cannot
establish whether format preservation adds utility beyond ordinary
relationship-preserving pseudonymization.

A future incident family must make structural information explicitly necessary
for RCA—for example truncation, leading-zero loss, separator corruption,
malformed identifier shape, fixed-width mismatch, or a structural/check-digit
violation. That family has not been implemented.

## Immediate prohibitions

- Do not rerun or edit any frozen development/validation observation.
- Do not run privacy baselines on validation seeds without separate approval.
- Do not generate or inspect held-out seeds 20000–20999.
- Never use retired seeds 10000–10999.
- Do not modify frozen prompts, taxonomies, scorers, generator behavior, oracle,
  evidence definitions, model configuration, or completed JSONLs in place.
- Do not infer research validity from passing tests or five-instance results.
- Do not implement DiagPriv as a silent extension of a baseline protocol.

## Known limitations

- Only one incident family exists, so current scores cannot establish
  generality or the utility of format preservation.
- Development and validation samples are small and generated by one family.
- No human difficulty or evidence-sufficiency study has been completed.
- Provider determinism is not guaranteed even with fixed input and one call.
- Component ownership may be more interpretation-sensitive than other RCA
  dimensions.
- Result artifacts are local/ignored; a collaboration-safe distribution policy
  remains to be chosen.
- The runner directly constructs Incident Family 001 and needs a reviewed
  family registry before broad multi-family evaluation.
