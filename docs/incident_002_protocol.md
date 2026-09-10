# Incident Family 002 Protocol

## Purpose

`incident-002-generator-v1` creates a missing-effect scenario whose intended
cause requires comparing the visible shape of one sensitive external reference
with successful controls. It is an offline construction milestone; no provider
observation is part of this implementation.

The intake role accepts and queues an opaque envelope. The operation executor
owns domain-level reference validation/normalization, performs the exact lookup,
and owns creation of the provisioning effect. This ownership makes
`operation_executor` the canonical affected component even though intake is the
first visible service.

## Structural-signature semantics

The reusable function `diagbench.structural.structural_signature` is versioned
as `structural-signature-v1`:

| Visible character | Signature atom |
|---|---|
| ASCII uppercase letter | `U` |
| ASCII lowercase letter | `l` |
| ASCII decimal digit | `D` |
| Printable punctuation or space | exact literal |

Tabs, line breaks, other control characters, and non-ASCII Unicode are rejected.
The semantics deliberately match the character structure retained by
`format-preserving-v1`, but the helper is benchmark-generic and does not depend
on a privacy transformation.

## Generated defects and observable deltas

- `missing_separator`: remove exactly one literal separator;
- `extra_separator`: insert exactly one literal separator between class atoms;
- `truncation`: remove the final character;
- `fixed_width_mismatch`: insert or remove one internal character-class atom;
- `leading_zero_loss`: hidden construction metadata for removing the first
  digit position of a numeric run whose generated latent value begins with
  zero; and
- `case_class_mismatch`: flip one ASCII letter between upper/lower case.

The first five generated classes change length, so the instance declares a conditional
`target_identifier_length_delta` invariant. The case-class defect instead
requires equal length and exactly one `U`/`l` signature substitution.

The visible `target_identifier_defect_signature` normally uses the generated
class name. The sole deliberate exception is:

```text
hidden generation cause: leading_zero_loss
observable delta:         numeric_run_leading_position_deletion
```

The observable relation requires a unanimous healthy-control signature with a
fixed-width digit run and a target signature equal to that signature after
removing the run's leading `D` position. It does not claim that the missing
literal digit was zero. The latent zero is a generator fact only. The generic
predicate does not recognize `leading_zero_loss`, so hidden metadata cannot make
the invariant pass.

## Domain separation and determinism

Generation seeds a local pseudorandom generator from SHA-256 of the NUL-separated
family ID, generator version, and decimal seed. No Python hash value, global
random state, UUID, wall clock, or insertion-order-dependent assignment is used.
The family currently rejects every seed outside `1000–1999` before generation.

## Shape-ablation audit

`incident-002-shape-ablation-v1` replaces all sensitive external references in
one complete ModelView with equal-length synthetic tokens while preserving
equality, inequality, and cross-source linkage. The local mapping is discarded.
The audit requires:

- the target to be the unique raw structural outlier;
- all ablated references to share one output signature;
- at least two operations to have a lookup miss (the target and benign recovery);
- no cause-bearing field or message; and
- no remaining trivial metadata feature that uniquely names a shape cause.

This deterministic audit is narrower than a claim that no analyst could infer
anything after ablation. It establishes that the constructed direct shape clue
is removed and that the miss field alone is non-unique.

## Expected privacy-condition behavior

| Condition | Equality/linkage | Original structural anomaly |
|---|---|---|
| raw | preserved | preserved |
| redaction-v1 | damaged | destroyed by many-to-one collapse |
| hmac-v1 | preserved | destroyed |
| tokenization-v1 | preserved | destroyed by uniform token shape |
| format-preserving-v1 | preserved | preserved |

When healthy pattern consistency remains true only because all identifiers were
mapped to one output shape, invariant reporting uses
`degenerate_pattern_collapse`; the underlying predicate result remains true for
reproducibility.
