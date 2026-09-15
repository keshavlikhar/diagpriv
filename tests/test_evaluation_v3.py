from __future__ import annotations

from dataclasses import replace
import json

import pytest

from diagbench.generators.incident_003 import generate_incident_003
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagpriv.evaluation.evidence_support_v3 import (
    incident_003_evidence_rubric_v3,
    score_evidence_support_v3,
)
from diagpriv.evaluation.prompt_v3 import (
    PROMPT_SHA256,
    PROMPT_VERSION,
    build_prompt_v3,
    prompt_template_v3,
)
from diagpriv.evaluation.response import (
    RCAResponseV2,
    RCAResponseV3,
    parse_response_v3,
)
from diagpriv.evaluation.scoring_v3 import RCAScoreV3, score_response_v3
from diagpriv.evaluation.scoring_v2 import ProtocolVersionError, score_response_v2
from diagpriv.evaluation.taxonomy_v3 import (
    CATEGORIES_BY_FIELD,
    DEFINITIONS_BY_FIELD,
    TAXONOMY_VERSION,
    ControlBoundaryFactsV3,
    adjudicate_control_boundary_v3,
)


def _target_core_ids(seed: int = 1019) -> tuple[str, ...]:
    incident = generate_incident_003_v2(seed)
    target = incident.metadata["target_operation_id"]
    return tuple(
        str(row["evidence_id"])
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        )
        for row in incident.structured_evidence[source]
        if row["operation_id"] == target
    )


def _correct_response(seed: int = 1019) -> RCAResponseV3:
    oracle = generate_incident_003_v2(seed).ground_truth_v3
    assert oracle is not None
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=_target_core_ids(seed),
        explanation="The cited target rows establish the temporal and terminal-state chain.",
        confidence=0.9,
    )


def test_v3_taxonomy_has_machine_readable_metadata_for_every_label() -> None:
    assert TAXONOMY_VERSION == "rca-taxonomy-v3"
    assert set(DEFINITIONS_BY_FIELD) == set(CATEGORIES_BY_FIELD)
    for field, definitions in DEFINITIONS_BY_FIELD.items():
        assert tuple(item.label for item in definitions) == CATEGORIES_BY_FIELD[field]
        assert len(definitions) >= 9
        for definition in definitions:
            assert definition.operational_definition
            assert definition.label in CATEGORIES_BY_FIELD[field]
            for confusable in definition.confusables:
                assert confusable in CATEGORIES_BY_FIELD[field]


def test_v3_parser_accepts_only_exact_canonical_labels() -> None:
    baseline = _correct_response().to_dict()
    for field, categories in CATEGORIES_BY_FIELD.items():
        for category in categories:
            parsed = parse_response_v3(json.dumps({**baseline, field: category}))
            assert parsed.status == "valid", (field, category, parsed.error)
    parsed = parse_response_v3(
        json.dumps({**baseline, "failure_mechanism": "race_condition"})
    )
    assert parsed.status == "unknown_category"
    assert parsed.unknown_fields == ("failure_mechanism",)


def test_v3_parser_requires_all_five_dimensions() -> None:
    payload = _correct_response().to_dict()
    del payload["subsequent_action"]
    parsed = parse_response_v3(json.dumps(payload))
    assert parsed.status == "missing_fields"
    assert "subsequent_action" in (parsed.error or "")


def test_v3_prompt_is_frozen_family_neutral_and_contains_no_examples() -> None:
    template = prompt_template_v3()
    assert PROMPT_VERSION == "raw-rca-v3"
    assert PROMPT_SHA256 == (
        "a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139"
    )
    for field, definitions in DEFINITIONS_BY_FIELD.items():
        assert field in template
        for definition in definitions:
            assert f"- {definition.label}:" in template
    for forbidden in (
        "Incident 001",
        "Incident 002",
        "Incident 003",
        "duplicate payment",
        "fixed-width identifier",
        "exact-lookup provisioning",
        "active worker",
        "ground_truth",
        "oracle",
        "positive example",
        "contrastive example",
    ):
        assert forbidden.lower() not in template.lower()


def test_v3_prompt_uses_model_view_only() -> None:
    incident = generate_incident_003_v2(1019)
    prompt = build_prompt_v3(incident.model_view())
    assert incident.model_view().to_json().strip() in prompt
    assert incident.ground_truth_v3 is not None
    assert incident.ground_truth_v3.explanation not in prompt
    for forbidden in (
        "ground_truth_v3",
        "diagnostic_invariants",
        "expected_evidence",
        "sensitive_fields",
        "temporal_template_name",
        "target_operation_id",
    ):
        assert forbidden not in prompt


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            ControlBoundaryFactsV3(
                repeated_logical_identity=True,
                effective_idempotency_alone_prevents_outcome=True,
                overlapping_actors_required=True,
                concurrency_control_prevents_outcome=True,
            ),
            "missing_or_ineffective_idempotency",
        ),
        (
            ControlBoundaryFactsV3(
                overlapping_actors_required=True,
                concurrency_control_prevents_outcome=True,
                invalid_transition_remains_under_serialization=True,
            ),
            "incorrect_concurrency_control",
        ),
        (
            ControlBoundaryFactsV3(
                invalid_transition_remains_under_serialization=True
            ),
            "incorrect_state_transition",
        ),
        (
            ControlBoundaryFactsV3(
                serialized_multi_part_operation_can_partially_apply=True
            ),
            "non_atomic_commit_or_rollback",
        ),
        (
            ControlBoundaryFactsV3(
                retry_decision_defective_with_effective_idempotency=True
            ),
            "incorrect_retry_policy",
        ),
        (ControlBoundaryFactsV3(), "unknown_failure_mechanism"),
    ],
)
def test_v3_control_boundary_precedence(
    facts: ControlBoundaryFactsV3, expected: str
) -> None:
    assert adjudicate_control_boundary_v3(facts) == expected


def test_v3_semantic_evidence_accepts_complete_structured_or_log_path() -> None:
    incident = generate_incident_003_v2(1019)
    structured = score_evidence_support_v3(incident, _target_core_ids())
    assert structured.essential_requirement_coverage == 1.0
    assert structured.evidence_supported is True
    assert structured.invalid_citation_count == 0
    assert structured.wrong_subject_citation_count == 0

    rubric = incident_003_evidence_rubric_v3(incident)
    log_path = next(
        path.evidence_ids
        for requirement in rubric.requirements
        if requirement.name == "target_identity_linkage"
        for path in requirement.acceptable_paths
        if path.path_id.endswith(":logs")
    )
    log_score = score_evidence_support_v3(incident, log_path)
    assert log_score.essential_requirement_coverage == 1.0
    assert log_score.evidence_supported is True


def test_v3_semantic_evidence_rejects_missing_invalid_and_wrong_subject_citations() -> None:
    incident = generate_incident_003_v2(1019)
    incomplete = score_evidence_support_v3(incident, _target_core_ids()[:-1])
    assert incomplete.essential_requirement_coverage < 1.0
    assert incomplete.evidence_supported is False

    invalid = score_evidence_support_v3(
        incident, (*_target_core_ids(), "NOT-AN-EVIDENCE-ID")
    )
    assert invalid.invalid_citation_count == 1
    assert invalid.evidence_supported is False

    target = str(incident.metadata["target_operation_id"])
    unrelated = next(
        str(row["evidence_id"])
        for row in incident.structured_evidence["workflow_attempts"]
        if row["operation_id"] != target
        and row["operation_id"]
        not in {
            incident.metadata["slow_control_operation_id"],
            incident.metadata["legitimate_compensation_operation_id"],
        }
    )
    wrong = score_evidence_support_v3(incident, (*_target_core_ids(), unrelated))
    assert wrong.wrong_subject_citation_count == 1
    assert unrelated in wrong.wrong_subject_evidence_ids


def test_exact_rca_v3_requires_all_labels_and_semantic_evidence() -> None:
    incident = generate_incident_003_v2(1019)
    response = _correct_response()
    score = score_response_v3(incident, response)
    assert isinstance(score, RCAScoreV3)
    assert score.exact_root_cause_correct is True
    assert score.evidence_supported is True
    assert score.overall_correct is True

    changed = replace(response, failure_mechanism="incorrect_state_transition")
    changed_score = score_response_v3(incident, changed)
    assert changed_score.failure_mechanism_correct is False
    assert changed_score.exact_root_cause_correct is False
    assert changed_score.evidence_supported is True
    assert changed_score.overall_correct is False


def test_v2_and_v3_responses_cannot_cross_protocol_scorers() -> None:
    v1_incident = generate_incident_003(1000)
    v2_oracle = v1_incident.ground_truth_v2
    response_v2 = RCAResponseV2(
        observed_outcome=v2_oracle.observed_outcome,
        trigger=v2_oracle.trigger,
        subsequent_action=v2_oracle.subsequent_action,
        failure_mechanism=v2_oracle.failure_mechanism,
        affected_component=v2_oracle.affected_component,
        supporting_evidence=(),
        explanation="Historical protocol fixture.",
        confidence=0.5,
    )
    with pytest.raises(ProtocolVersionError, match="RCAResponseV3"):
        score_response_v3(generate_incident_003_v2(1019), response_v2)  # type: ignore[arg-type]
    with pytest.raises(ProtocolVersionError, match="RCAResponseV2"):
        score_response_v2(v1_incident, _correct_response())  # type: ignore[arg-type]
