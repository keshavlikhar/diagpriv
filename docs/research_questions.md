# Research Questions

## Primary question

**RQ1:** To what extent can sensitive information be removed or pseudonymized
from operational troubleshooting data without reducing LLM root-cause-analysis
accuracy?

## Operational questions

1. Which diagnostic invariants are necessary and sufficient for each incident?
2. How should root-cause accuracy and supporting-evidence quality be scored?
3. How much linkability and attribute leakage remains after each transformation?
4. How do redaction, HMAC, deterministic tokenization, format preservation, and
   task-aware transformation compare under matched privacy-exposure criteria?
5. Does preserving cross-source identity improve diagnosis enough to justify its
   added linkability?
6. Are results stable across model families, prompt variations, and repeated
   trials?
7. Which incident properties—difficulty, evidence type, and invariant class—most
   affect the privacy/utility trade-off?

## Questions requiring protocol decisions

The research team must predefine the privacy threat model, comparable exposure
levels, RCA scoring rubric, model and prompt selection, number of repetitions,
and statistical analysis plan before drawing conclusions. These choices should
be versioned alongside experimental results.

