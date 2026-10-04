# Zenodo preprint metadata

This file records the published metadata for the first public DiagPriv preprint.

**Zenodo record:** https://zenodo.org/records/23142445  
**Version DOI:** 10.5281/zenodo.23142445  
**All-versions DOI:** 10.5281/zenodo.23142444

## Basic information

**Resource type:** Publication — Preprint

**Title:** DiagPriv: Preserving Diagnostic Structure While Reducing Sensitive Data Exposure in LLM Root-Cause Analysis

**Publication date:** October 4, 2026

**Language:** English

**Access:** Public

**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)

The manuscript/preprint license is separate from the repository's Apache-2.0
software license.

## Creators

Enter creators in this order:

1. Keshav Likhar
   - ORCID: 0009-0000-1473-8274
   - Affiliation: Independent Researcher
   - Location in manuscript: Boise, Idaho, USA
   - Corresponding email: keshavlikhar007@gmail.com
2. Harsh Mandalgi
   - ORCID: 0009-0000-9956-3636
   - Affiliation: Independent Researcher
   - Location in manuscript: Bengaluru, India
3. Mohit Chaturvedi
   - ORCID: 0009-0001-7496-1504
   - Affiliation: Independent Researcher
   - Location in manuscript: Buffalo, New York, USA

All authors contributed equally. Keshav Likhar is the corresponding author.

## Description / abstract

Operational evidence can contain the facts needed to diagnose a failure and identifiers or temporal details that need not be disclosed to an external model. We study diagnostic-invariant privacy-oriented transformation: changing the representation sent to a large language model while preserving the relationships required for a root-cause-analysis (RCA) task. Three synthetic incident families are designed around different dependencies: identifier equality and cross-source linkage, external-reference shape, and causal temporal order. Fixed redaction, HMAC, tokenization, format-preserving pseudonymization, relative-time conversion, and temporal ablation provide controlled comparisons. A separate versioned exposure vector measures which literal, linkage, shape, cardinality, and temporal properties remain visible; it is not an anonymity score. Development observations are directionally consistent with task-specific structure mattering: the format-sensitive family loses trigger/mechanism accuracy under opaque identifiers, and paired temporal-mechanism discrimination declines from 3/4 under raw evidence to 2/4 under relative time and 0/4 under temporal ablation. Evidence-support scoring separately asks whether cited visible records actually substantiate a diagnosis. These results are limited to selected synthetic development cases, a small number of calls from one model family, and no formal privacy guarantee or held-out evaluation.

## Keywords

- large language models
- root-cause analysis
- operational incident diagnosis
- privacy-oriented data transformation
- diagnostic invariants
- pseudonymization
- de-identification
- evidence grounding
- operational telemetry
- privacy-utility tradeoff

## Version

Published version: **v1**

Version DOI: **10.5281/zenodo.23142445**

All-versions DOI: **10.5281/zenodo.23142444**

## Related identifiers

At initial Zenodo publication:

- https://github.com/keshavlikhar/diagpriv
  - relation: supporting software / source repository

After a future arXiv submission, add the arXiv identifier as a related
identifier and cross-link the two records.

## Published files

- `DiagPriv_Preprint_Zenodo.pdf` — canonical reader-facing preprint
- `DiagPriv_Zenodo_Source.zip` — self-contained LaTeX source used to build the PDF
- `DiagPriv_Public_Reproducibility_v1.0.zip` — verified public Level-1 reproducibility artifact

Do **not** include ignored provider-result JSONLs, credentials, private archive
material, local build caches, or held-out/validation material beyond the
already tracked aggregate statements in the manuscript.

## Publication record

Published on Zenodo as an open preprint under CC BY 4.0. The GitHub repository
remained private at initial publication; the Level-1 reproducibility snapshot
was therefore included directly in the public Zenodo record. No arXiv
identifier should be added until an arXiv record actually exists.
