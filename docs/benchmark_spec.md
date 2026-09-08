# DiagBench v0.1 Specification

## Purpose

DiagBench provides small, fully synthetic troubleshooting incidents for studying
privacy/utility trade-offs. Version 0.1 contains only Incident 001.

## Incident contract

Each incident has stable identifying information, a troubleshooting question,
an unambiguous ground-truth root cause, structured and log evidence, explicit
sensitive-field declarations, diagnostic invariants, expected supporting
evidence, a difficulty label, and JSON-compatible metadata.

Structured evidence is a mapping from source names to lists of row objects. Log
evidence is a list of timestamped records. Field references use dotted paths:
`source.field` for structured evidence and `logs.field` for log evidence.

Sensitive-field declarations describe data classification and research policy;
they do not themselves perform a transformation. Diagnostic invariants state
which relationships must or need not survive a future transformation.

## Determinism and fictionality

A generator given the same integer seed must emit byte-equivalent logical data.
Every incident must set `metadata.synthetic` to `true`. Names must clearly signal
fictionality, emails use the reserved `example.invalid` domain, SSNs use an
unissued synthetic range, and identifiers carry a `SYN-` prefix.

## Incident 001 acceptance criteria

Incident 001 includes surrounding normal data plus exactly two rows for the
problematic logical payment. Those rows share customer, account, request, and
amount; have near-identical ordered timestamps; and are both successful. Logs
must show an initial request timing out, a retry, and a second successful insert
without an idempotency check.

## Versioning

Schema and benchmark changes should be reviewed separately. Future incidents may
extend the schema through metadata or new optional fields, but must remain cleanly
serializable to JSON.

