# Zenodo editorial revision v1.1

This file defines the prepared successor to published Zenodo record
`23142445` (version DOI `10.5281/zenodo.23142445`; all-versions DOI
`10.5281/zenodo.23142444`). Zenodo recommends a new version for significant
file changes. Publish this revision under the same all-versions concept so the
original v1 files remain identifiable.

## Scope

This is an editorial revision only. It does not change the benchmark,
transformations, prompts, model observations, scores, frozen artifact hashes,
or scientific conclusions.

The revision:

- uses controlled English based on ASD-STE100 principles;
- adds a glossary for technical terms;
- adds a qualitative transformation information-profile figure;
- reduces the rendered PDF from 7,137 to 4,121 extracted words (42.3%);
- reduces the PDF from 16 to 11 pages.

The ASD-STE100 statement is an editorial target, not formal certification.
A local style audit found that 97.2% of prose sentences contain no more than
25 words.

## Proposed version metadata

**Version:** v1.1

**Resource type:** Publication — Preprint

**Title:** DiagPriv: Preserving Diagnostic Structure While Reducing Sensitive Data Exposure in LLM Root-Cause Analysis

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)

**Description / abstract:**

Operational evidence can help an external large language model (LLM) find a
failure cause. The same evidence can reveal identifiers and time data that the
model does not need. We test transformations that hide selected values but
keep relations needed for root-cause analysis (RCA). Three synthetic incident
families require identifier linkage, identifier shape, or temporal order. The
tests compare redaction, three types of pseudonyms, relative time, and temporal
ablation. A separate exposure vector measures the information that remains
visible. It is not an anonymity score. Development results suggest that
task-specific structure can affect RCA. However, the study uses few synthetic
cases, one model family, and no held-out evaluation. It gives no formal privacy
guarantee.

## Publication files

- `DiagPriv_Preprint_Zenodo.pdf` — revised reader-facing preprint;
- `DiagPriv_Zenodo_Source.zip` — self-contained source for this revision;
- `DiagPriv_Public_Reproducibility_v1.0.zip` — unchanged public Level-1
  reproducibility package copied from v1.

The new version DOI and record URL must be added here after Zenodo publishes
the version. Do not include provider JSONLs, credentials, private archive
material, build caches, validation data, or held-out data.
