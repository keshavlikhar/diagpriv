# DiagPriv Research Charter

## Problem

Engineers increasingly use LLMs and coding agents to troubleshoot production
systems. Operational evidence may contain names, Social Security numbers,
emails, phone numbers, customer and account identifiers, IP addresses, secrets,
and other sensitive information.

Traditional redaction or masking can protect privacy but may destroy the
relationships and abnormalities needed for root-cause analysis. For example,
two occurrences of `customer_id = 123` must remain recognizably equal when that
equality is diagnostic. Generic redaction may preserve that equality only by
accident, while independent masking can destroy it.

Likewise, the malformed value `SSN = 1234-567-89` contains evidence in its
format. Replacing it with `[SSN]` removes the evidence required to diagnose the
formatting defect.

The research therefore asks:

> Can we remove sensitive identity while preserving the diagnostic properties
> required by an LLM?

## Main research question

**RQ1:** To what extent can sensitive information be removed or pseudonymized
from operational troubleshooting data without reducing LLM root-cause-analysis
accuracy?

## Supporting questions

- How much diagnostic utility is retained by conventional redaction?
- When does keyed HMAC pseudonymization preserve useful equality and correlation?
- How does deterministic tokenization compare with redaction and HMAC?
- When is format preservation necessary, and what privacy exposure does it add?
- Can task-aware transformations outperform transformations that do not know the
  troubleshooting question?
- Which equality, uniqueness, duplicate, ordering, and cardinality relationships
  must be preserved for a given diagnosis?
- Can cross-source correlation be preserved without retaining source identities?
- How should diagnostic invariants be specified, validated, and measured?
- What trade-off exists between retained diagnostic invariants and privacy
  exposure?

## Initial hypothesis

A privacy transformation that explicitly preserves task-relevant diagnostic
invariants will retain more root-cause-analysis utility than conventional
redaction or masking at comparable privacy exposure.

This is a hypothesis. It has not yet been experimentally demonstrated, and the
current milestone is not evidence for or against it.

## Scope and guardrails

The initial work is a synthetic benchmark and research scaffold. All identities,
events, and system data are fictional. No customer or production data may be
used. Privacy transformations, LLM evaluation, product integrations, compliance
claims, and production deployment are outside the current milestone.

