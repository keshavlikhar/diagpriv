"""Generic, versioned structural signatures for visible ASCII strings."""

from __future__ import annotations

import string
from typing import Literal

STRUCTURAL_SIGNATURE_VERSION = "structural-signature-v1"

ObservableStructuralDelta = Literal[
    "missing_separator",
    "extra_separator",
    "truncation",
    "fixed_width_mismatch",
    "numeric_run_leading_position_deletion",
    "case_class_mismatch",
]

SUPPORTED_STRUCTURAL_DELTAS: tuple[ObservableStructuralDelta, ...] = (
    "missing_separator",
    "extra_separator",
    "truncation",
    "fixed_width_mismatch",
    "numeric_run_leading_position_deletion",
    "case_class_mismatch",
)

_CLASS_ATOMS = frozenset({"U", "l", "D"})


def structural_signature(value: str) -> str:
    """Return a visible character-by-character structural signature.

    Printable ASCII uppercase letters map to ``U``, lowercase letters to
    ``l``, and decimal digits to ``D``. Printable punctuation and spaces are
    retained literally. Other characters are rejected so this version's
    semantics cannot vary with Unicode implementation details.
    """
    signature: list[str] = []
    for character in value:
        if character in string.ascii_uppercase:
            signature.append("U")
        elif character in string.ascii_lowercase:
            signature.append("l")
        elif character in string.digits:
            signature.append("D")
        elif character in string.printable and character not in "\t\n\r\x0b\x0c":
            signature.append(character)
        else:
            raise ValueError(
                f"{STRUCTURAL_SIGNATURE_VERSION} supports printable ASCII only"
            )
    return "".join(signature)


def structural_defect_matches(
    healthy_values: tuple[str, ...],
    target_value: str,
    defect: str,
) -> bool:
    """Check a declared observable one-edit delta against visible shapes.

    Healthy values must first establish one unanimous signature. The defect is
    then recognized only from the observed signature delta; no latent valid
    identifier or oracle cause label is used as evidence. In particular,
    ``leading_zero_loss`` is not an observable delta in this vocabulary.
    """
    if len(healthy_values) < 3 or defect not in SUPPORTED_STRUCTURAL_DELTAS:
        return False
    healthy_signatures = tuple(structural_signature(value) for value in healthy_values)
    if len(set(healthy_signatures)) != 1:
        return False
    expected = healthy_signatures[0]
    observed = structural_signature(target_value)
    if observed == expected:
        return False

    if defect == "missing_separator":
        return any(
            expected[index] not in _CLASS_ATOMS
            and observed == expected[:index] + expected[index + 1 :]
            for index in range(len(expected))
        )
    if defect == "extra_separator":
        return any(
            observed[index] not in _CLASS_ATOMS
            and expected == observed[:index] + observed[index + 1 :]
            for index in range(len(observed))
        )
    if defect == "truncation":
        return len(expected) > 1 and observed == expected[:-1]
    if defect == "case_class_mismatch":
        differences = [
            index
            for index, (before, after) in enumerate(zip(expected, observed, strict=False))
            if before != after
        ]
        return (
            len(expected) == len(observed)
            and len(differences) == 1
            and {expected[differences[0]], observed[differences[0]]} == {"U", "l"}
        )
    if defect == "numeric_run_leading_position_deletion":
        return any(
            expected[index] == "D"
            and (index == 0 or expected[index - 1] != "D")
            and observed == expected[:index] + expected[index + 1 :]
            for index in range(len(expected))
        )
    if defect == "fixed_width_mismatch":
        return _internal_class_deletion(expected, observed) or _internal_class_deletion(
            observed, expected
        )
    return False


def _internal_class_deletion(longer: str, shorter: str) -> bool:
    """Recognize one internal class-position insertion/deletion."""
    if len(longer) != len(shorter) + 1:
        return False
    for index, atom in enumerate(longer):
        if atom not in _CLASS_ATOMS or index == len(longer) - 1:
            continue
        if atom == "D" and (index == 0 or longer[index - 1] != "D"):
            continue
        if shorter == longer[:index] + longer[index + 1 :]:
            return True
    return False
