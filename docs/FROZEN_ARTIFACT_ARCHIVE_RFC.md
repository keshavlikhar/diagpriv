# RFC: provenance-safe archive for frozen provider observations

Status: **design for review, not an implemented archive**. Issue #35. No
provider observation was uploaded, copied into Git, distributed, regenerated,
or changed by this RFC. The verifier and manifest are provider-free metadata
and synthetic-test tooling only.

## 1. Problem and scope

The manuscript can reproduce its deterministic tables from tracked summaries,
but a clean checkout cannot independently obtain the exact ignored JSONLs
behind those summaries. A result hash in a paper is an identity, not a
distribution mechanism. An authorized collaborator needs an approved way to
identify, obtain, verify, and then inspect/rescore the historical **bytes**
without invoking an LLM. This RFC covers the paper-ledger observations; it
does not archive every file under `results/`.

Non-goals: new provider calls, retrospective repair of observations, scoring
or protocol changes, a production data lake, public release, validation or
held-out inspection in this task, or automatic download/upload. Source code,
synthetic fixtures, and aggregates are not substitutes for provider output.

## 2. Artifact taxonomy and paper-critical inventory

| Class | Current treatment | Archive decision |
| --- | --- | --- |
| Deterministic synthetic fixtures/configs | Tracked under `diagbench/`, `experiments/`, tests | Already in source Git; no provider archive |
| Aggregate/provenance summaries | `paper/data/frozen_development_results_v1.json`, result documents, generated TeX | Tracked; preserve source hashes and methodological caveats |
| Deterministic exposure analysis | `docs/data/privacy_exposure_development_v1.json` | Tracked and independently regenerable; not provider output |
| Frozen provider observations | Ignored `results/*.jsonl` | Candidate for **private** exact-byte archive after approval |
| Generated manuscript files | `paper/build/` PDF/auxiliary files | Rebuild from tracked source; not a frozen observation |
| Historical/optional compatibility inputs | Older v1/v2 JSONLs and optional tests that skip when absent | Do not automatically add to the paper archive; separate inventory/review if needed |

`artifacts/frozen_artifacts_v1.json` identifies the **20** files cited by the
paper ledger: Incident 001 (five development conditions plus raw-only
validation metadata), Incident 002 (five trial-1 files, five trials-2–3 files,
one transport-recovery sensitivity file), and Incident 003 v3 (raw Stage 1,
relative-time Stage 2, temporal-ablation Stage 3). It records paths and
SHA-256 values from the frozen ledger, without inventing a storage location.
The recovery file is a sensitivity artifact; it never replaces the primary
transport failures. Stage-1 evidence-support-v4 remains primary and its
later v5 rescore does not replace the underlying JSONL.

The three high-priority Incident 003 identities are:

| Artifact | SHA-256 | Bytes |
| --- | --- | ---: |
| Stage 1 raw | `b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2` | 45,240 |
| Stage 2 relative-time | `f020511aeb497eab8c4ca5da4487ed87e20c6fe5e8b37a56613eb521297536e4` | 50,010 |
| Stage 3 temporal ablation | `40d48f58f95b9bf837fa75a6a13209f6d00c6bbedca8c24d90ddb0927e1bb55a` | 47,901 |

The 19 development files were locally read **only to hash and size them**;
each matched its pre-existing ledger digest. Their contents were not printed
or copied. The raw-only validation file's path and digest come from tracked
documentation; its byte size is deliberately `null` / `not_inspected_validation`
because this task did not inspect validation data. Thus full size verification
of that one record is a future authorized migration step, not a claimed result
of this RFC. No held-out artifact is in this inventory. Development-only
diagnostic and failed HTTP attempts outside the manuscript ledger are also
excluded; their scientific role would need separate review.

## 3. Threat model and privacy review

Threats are accidental replacement, wrong-version download, incomplete
transfer, locator drift, archive deletion, unauthorized access, or a clean
clone silently treating missing files as reproducible observations. SHA-256
against a reviewed Git-tracked manifest detects changed bytes but does **not**
itself authenticate a maliciously rewritten manifest. Protected `main`, PR
review, and an immutable release reduce that risk. This is not a defense
against a compromised maintainer with control of both Git history and storage.

JSONLs can contain model-generated text, synthetic evidence, rendered prompts
or prompt-derived text, identifiers, response IDs, provider timestamps,
sanitized API errors, token counts, model/service-tier metadata, and
transformation-specific linkage. Synthetic inputs do not imply automatic
public-release safety. Review for secrets, unexpected personal data,
provider terms, and re-identification/linkability exposure before broadening
access. Nothing in this RFC claims anonymity or provider-side security.

## 4. Storage alternatives

| Option | Integrity / replacement | Access and reproducibility | Cost / operational burden | Decision |
| --- | --- | --- | --- | --- |
| A. Release assets on the source repository | Ordinary assets are editable/deletable; [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) lock published assets and tag when enabled; always verify our manifest digest | Simple download for repository readers, but a future public source repository could expose the same release assets | Low | Reject as primary because source-publication policy and observation access should be separate |
| B. Separate **private** artifact repository, release assets | Use immutable releases **if the setting is available and enabled**; draft, attach, verify, publish, then lock. Git remains a metadata/control plane, not a JSONL history or LFS store | Small authorized collaborator list, stable tag/asset locator; independent of source-repo visibility | Low to moderate | **Recommend for current small collaboration**, conditional on admin verification of immutability and retention policy |
| C. Versioned object storage with object lock | [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) can protect individual versions; version IDs and SHA-256 still needed | Fine-grained IAM and short-lived delivery; independent of GitHub | IAM, billing, lifecycle and key-management burden | Fallback if immutable private releases are unavailable or governance requires stronger retention controls |
| D. Manually distributed archive plus signed/digested manifest | Digest/signature can detect edits, but custody and availability depend on people | Easy initially, difficult for clean-clone collaborators and long-term review | Low infrastructure, high coordination | Emergency/export copy only, not canonical archive |

Do **not** use ordinary mutable release assets as if they were immutable.
GitHub says collaborators with write access can edit releases; release-asset
retrieval from a private repository requires authenticated read permission
([release management](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository),
[release asset API](https://docs.github.com/en/rest/releases/assets)). Git
LFS in a separate repository would retain provider output in Git-associated
history and add quota/clone semantics without the desired frozen-release
boundary. A versioned object store is sound, but not proportional as the
first choice while these files are small and the collaborator group is small.

**Decision gate before implementation:** confirm the separate private
repository can enforce immutable releases for this account/plan, confirm who
administers it, and approve a retention/deletion policy. If immutability is
unavailable, do not upload to a mutable release and call it frozen; review the
object-store fallback instead. No repository, release, bucket, or asset is
created by this RFC.

## 5. Canonical tracked manifest (`frozen-artifact-manifest-v1`)

Path: `artifacts/frozen_artifacts_v1.json`. Every entry has an artifact ID,
scientific role, expected **relative** local path, exact SHA-256, byte size or
explicitly unknown size, media type, incident family, condition, split,
requested model, reasoning effort, prompt version and **template** hash,
result-manifest schema, scorer, evidence and transformation versions (nullable
where not applicable/known), source config, publication status, and a locator.
`null` never means a guessed value: for example, the recovery file spans two
transformation conditions and its single transformation version is not
fabricated. The source config and individual result manifest remain the more
detailed protocol records. A publication status of `private` is not public
release approval.

All `archive_locator` fields are currently `null`. A later reviewed migration
may use a credential-free locator of the form
`github-release://OWNER/PRIVATE_REPO/TAG/ASSET`; no query string, signed URL,
token, password, or credential-bearing host is allowed. The tag and asset
identify an immutable published release, while the digest remains the final
byte authority. The verifier validates IDs, schema, paths, duplicates, hashes,
sizes, locator syntax, and required metadata before checking any file.

Manifest changes require PR review. A frozen artifact is never replaced under
the same artifact ID/digest. If bytes legitimately change, create a **new**
artifact ID, digest, size, and provenance record; retain the old record and
explain the correction. Published results keep pointing to the historical
record. Never change a hash merely to make a failing download pass.

## 6. Provider-free verification and failure behavior

From a clean checkout, with no provider credentials:

```bash
uv run python -m diagpriv.artifacts verify --artifact incident-003-v3-raw-stage-1
uv run python -m diagpriv.artifacts verify --all
```

This command performs **no network access**, download, provider setup,
scoring, repair, or file write. Exit status 0 means exact SHA-256 **and** size
match. Exit 2 means `MISSING` (normal for a clean clone before authorized
materialization). Exit 3 means size or digest mismatch; stop and quarantine
the candidate bytes, never use them for analysis. Exit 4 means invalid
manifest, unsafe path, unreadable file, unknown ID, or digest-only verification
where the expected size has not been frozen. It prints only ID/status/reason,
not observation contents. A valid hash with unknown size is
`SIZE_UNKNOWN`, **not** full verification.

Optional historical tests may skip when ignored files are absent; this is
distinct from asserting that exact historical observations were reproduced.
CI on a clean clone should validate the manifest and synthetic verifier tests,
not fetch private observations or require provider credentials.

## 7. Future materialization workflow (not implemented here)

1. Obtain approval for the exact artifact IDs and access level; a custodian
   reviews each file for content, policy, and publication class.
2. Custodian verifies local SHA-256/size against the tracked ledger before
   uploading to a **draft** release in the separate private repository.
3. Verify uploaded asset digest/size, publish under enforced immutable-release
   settings, then record tag/asset locator by reviewed PR. The tag is not
   reused. Maintain a second controlled backup to mitigate service loss.
4. Authorized collaborator authenticates to the artifact repository using
   their own read-scoped GitHub access. Download a selected asset to a
   temporary, nontracked location; never commit access tokens or signed URLs.
5. Verify SHA-256 and exact size **before** atomically placing it at the
   manifest's ignored `results/` path. Refuse to overwrite an existing path.
6. Only after verification may offline inspection/rescore be attempted under
   the separate scientific protocol. No fallback to regenerating an LLM
   response exists.

No automatic downloader is included in this issue, so a missing locator or
file is reported honestly rather than silently resolved. A source checkout
alone remains Level 1 reproducibility until distribution is separately
approved and executed.

## 8. Access, public-release boundary, and retention

The archive repository stays private even if the source repository becomes
public. Limit read access to named authorized collaborators; restrict upload,
release publication, and deletion to designated custodians, ideally with MFA,
PR-reviewed manifest edits, and audit logs. CI gets **no** private archive
token. Provider API credentials are never needed for retrieval or verification.
Internal access is not the same as permission to republish.

Publication levels:

1. **Level 1 (current):** source, configs, aggregates, deterministic exposure
   artifact, and hashes; no exact-observation distribution.
2. **Level 2 (future):** approved collaborators obtain exact private provider
   files and verify locally. This is the goal of the later implementation.
3. **Level 3 (not approved):** public observation release only after per-file
   privacy/security/provider-policy review and a separate decision. Files
   may remain `private` or be reported `aggregate_only` indefinitely.

The PI/custodian must set a retention period before upload, covering review
and any publisher/funder requirements. Keep a controlled backup and document
its owner. An immutable release is not a reason to ignore legal or provider
deletion obligations: if withdrawal is required, revoke access/delete the
release according to approved policy, retain a nonsecret tombstone and digest
in the ledger, and state that the historical bytes are no longer obtainable.
Do not silently substitute another file. The exact retention duration and
delete authority are unresolved and block upload, not this RFC.

## 9. Signing and authenticity

SHA-256 is enough to detect accidental or unauthorized asset replacement
**relative to a trusted reviewed Git manifest**. It is not an independent
signature. Branch protection/review plus an immutable GitHub release and its
release attestation are a proportionate first step; verify support before
use. If the threat model expands to malicious Git/storage administrators or
third-party distribution, consider a signed manifest/tag (minisign, GPG, or
Sigstore/cosign) with separately governed keys. Do not add signing machinery
without an owner and key-rotation/recovery procedure.

## 10. Migration and implementation plan

1. Review this ledger against the paper's source documents and configs. The
   19 development digests/sizes already matched their ignored local files;
   the validation size remains deliberately unmeasured in this issue.
2. Obtain explicit authorization for the validation-metadata completion,
   per-file content review, archive platform, access list, retention, and
   backup. Decide which, if any, are `candidate_public` or `aggregate_only`.
3. Provision a separate private artifact repository, enable and verify
   immutable releases, and document two custodians. If unavailable, evaluate
   versioned/object-locked storage before uploading anything.
4. Pilot the workflow with a **synthetic** JSONL and independent clean clone;
   test bad digest, missing asset, and attempted replacement.
5. Only in a separately authorized implementation task, migrate selected
   frozen local files by digest/size, publish immutable assets, and update
   locators in a reviewed PR. Never rewrite reported scientific results.
6. Revisit `paper/STATUS.md` only after Level 2 works end-to-end; do not claim
   full public observation-level reproducibility before Level 3 review.

Unresolved decisions: release-immutability availability for the chosen private
repo; custodian/access list; retention and withdrawal policy; backup location;
per-artifact content/provider-policy approval; whether raw-only validation
should enter Level 2 and, if so, authorized measurement of its byte size.
These block **distribution**, not the design/verifier review.

**No provider artifact was uploaded or distributed by this RFC.**
