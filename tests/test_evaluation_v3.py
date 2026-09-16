from __future__ import annotations

from dataclasses import replace
import json
from itertools import combinations
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import generate_incident_002
from diagbench.generators.incident_003 import generate_incident_003
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagpriv.evaluation.evidence_support_v3 import (
    canonical_rubric_json_v3,
    evidence_requirement_set_sha256_v3,
    score_evidence_support_v3,
    validate_evidence_rubric_v3,
)
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
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


def _score_evidence(
    evidence_ids: tuple[str, ...], seed: int = 1019
):
    incident = generate_incident_003_v2(seed)
    return score_evidence_support_v3(
        evidence_ids,
        incident.model_view(),
        build_incident_003_v2_evidence_rubric(incident),
    )


def _score_response(response: RCAResponseV3, seed: int = 1019) -> RCAScoreV3:
    incident = generate_incident_003_v2(seed)
    return score_response_v3(
        incident,
        response,
        build_incident_003_v2_evidence_rubric(incident),
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


def test_v3_taxonomy_has_reviewed_stale_and_dependency_boundaries() -> None:
    mechanisms = {
        item.label: item for item in DEFINITIONS_BY_FIELD["failure_mechanism"]
    }
    stale = mechanisms["stale_or_inconsistent_data"]
    assert set(stale.confusables) == {
        "data_integrity_failure",
        "incorrect_concurrency_control",
    }
    assert stale.exclusion_notes and stale.decision_guidance
    dependency = mechanisms["dependency_contract_failure"]
    validation = mechanisms["validation_or_input_handling_failure"]
    assert validation.label in dependency.confusables
    assert dependency.label in validation.confusables
    assert dependency.exclusion_notes and dependency.decision_guidance
    assert validation.exclusion_notes and validation.decision_guidance


def test_incident_001_and_002_v3_mappings_remain_the_approved_v2_labels() -> None:
    incident_001 = generate_incident_001(1000).ground_truth_v2
    incident_002 = generate_incident_002(1000).ground_truth_v2
    assert (
        incident_001.observed_outcome,
        incident_001.trigger,
        incident_001.subsequent_action,
        incident_001.failure_mechanism,
        incident_001.affected_component,
    ) == (
        "duplicate_effect",
        "timeout_or_deadline",
        "retry_or_rearrival",
        "missing_or_ineffective_idempotency",
        "operation_executor",
    )
    assert (
        incident_002.observed_outcome,
        incident_002.trigger,
        incident_002.subsequent_action,
        incident_002.failure_mechanism,
        incident_002.affected_component,
    ) == (
        "missing_effect",
        "malformed_or_unexpected_input",
        "no_follow_on_action",
        "validation_or_input_handling_failure",
        "operation_executor",
    )


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


def test_v3_rubric_serialization_and_hash_are_normative_and_deterministic() -> None:
    incident = generate_incident_003_v2(1019)
    first = build_incident_003_v2_evidence_rubric(incident)
    second = build_incident_003_v2_evidence_rubric(incident)
    validate_evidence_rubric_v3(incident.model_view(), first)
    assert canonical_rubric_json_v3(first) == canonical_rubric_json_v3(second)
    assert "\n" not in canonical_rubric_json_v3(first)
    assert evidence_requirement_set_sha256_v3(first) == (
        "c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db"
    )
    reversed_rubric = replace(
        first,
        requirements=tuple(
            replace(
                requirement,
                acceptable_paths=tuple(
                    replace(
                        path,
                        evidence_ids=tuple(reversed(path.evidence_ids)),
                        optional_evidence_ids=tuple(
                            reversed(path.optional_evidence_ids)
                        ),
                        semantic_parameters=tuple(
                            reversed(path.semantic_parameters)
                        ),
                    )
                    for path in reversed(requirement.acceptable_paths)
                ),
            )
            for requirement in reversed(first.requirements)
        ),
        subject_bindings=tuple(
            replace(binding, evidence_ids=tuple(reversed(binding.evidence_ids)))
            for binding in reversed(first.subject_bindings)
        ),
    )
    assert canonical_rubric_json_v3(reversed_rubric) == canonical_rubric_json_v3(
        first
    )


def test_generic_evidence_module_has_no_incident_003_dependency() -> None:
    source = (
        __import__(
            "diagpriv.evaluation.evidence_support_v3", fromlist=["__file__"]
        ).__file__
    )
    assert source is not None
    text = Path(source).read_text(encoding="utf-8")
    assert "incident_003" not in text
    assert "compensation" not in text
    assert "deadline" not in text


def test_rubric_validation_rejects_nonexistent_and_cross_subject_paths() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    requirement = rubric.requirements[0]
    path = requirement.acceptable_paths[0]
    nonexistent = replace(path, evidence_ids=(*path.evidence_ids, "NOT-AN-ID"))
    bad_requirement = replace(requirement, acceptable_paths=(nonexistent,))
    with pytest.raises(ValueError, match="nonexistent evidence"):
        validate_evidence_rubric_v3(
            incident.model_view(),
            replace(rubric, requirements=(bad_requirement, *rubric.requirements[1:])),
        )

    control_binding = next(
        binding for binding in rubric.subject_bindings if binding.role == "contrast"
    )
    mixed = replace(
        path,
        evidence_ids=(*path.evidence_ids[:-1], control_binding.evidence_ids[0]),
    )
    mixed_requirement = replace(requirement, acceptable_paths=(mixed,))
    with pytest.raises(ValueError, match="mixes incompatible subjects"):
        validate_evidence_rubric_v3(
            incident.model_view(),
            replace(rubric, requirements=(mixed_requirement, *rubric.requirements[1:])),
        )


def test_adversarial_01_one_generic_target_row_is_unsupported() -> None:
    score = _score_evidence(_target_core_ids()[:1])
    assert score.essential_requirement_coverage == 0.0
    assert score.evidence_supported is False


def test_adversarial_02_outcome_without_causal_timing_is_unsupported() -> None:
    workflow, _, effect, _ = _target_core_ids()
    score = _score_evidence((workflow, effect))
    assert score.essential_requirement_coverage == 0.0
    assert score.evidence_supported is False


@pytest.mark.parametrize(
    ("target_source", "other_source"),
    [
        ("workflow_attempts", "execution_observations"),
        ("compensation_records", "execution_observations"),
        ("workflow_attempts", "effect_records"),
    ],
)
def test_adversarial_03_to_05_cross_subject_pairs_are_unsupported(
    target_source: str, other_source: str
) -> None:
    incident = generate_incident_003_v2(1019)
    target = incident.metadata["target_operation_id"]
    target_id = next(
        str(row["evidence_id"])
        for row in incident.structured_evidence[target_source]
        if row["operation_id"] == target
    )
    other_id = next(
        str(row["evidence_id"])
        for row in incident.structured_evidence[other_source]
        if row["operation_id"] != target
    )
    score = _score_evidence((target_id, other_id))
    assert score.essential_requirement_coverage < 1.0
    assert score.evidence_supported is False


def test_adversarial_06_nonexistent_evidence_is_unsupported() -> None:
    score = _score_evidence((*_target_core_ids(), "NOT-AN-EVIDENCE-ID"))
    assert score.invalid_citation_count == 1
    assert score.evidence_supported is False


def test_adversarial_07_complete_proof_plus_unbound_subject_is_unsupported() -> None:
    incident = generate_incident_003_v2(1019)
    view = incident.model_view()
    unrelated = dict(view.structured_evidence["workflow_attempts"][0])
    unrelated["evidence_id"] = "EV-UNRELATED-SUBJECT"
    unrelated["operation_id"] = "OP-UNRELATED-SUBJECT"
    view.structured_evidence["workflow_attempts"].append(unrelated)
    score = score_evidence_support_v3(
        (*_target_core_ids(), "EV-UNRELATED-SUBJECT"),
        view,
        build_incident_003_v2_evidence_rubric(incident),
    )
    assert score.essential_requirement_coverage == 1.0
    assert score.wrong_subject_citation_count == 1
    assert score.evidence_supported is False


def test_adversarial_08_duplicate_does_not_inflate_coverage() -> None:
    core = _target_core_ids()
    baseline = _score_evidence(core)
    duplicated = _score_evidence((*core, core[0], core[0]))
    assert duplicated.essential_requirement_coverage == baseline.essential_requirement_coverage
    assert duplicated.redundant_citation_count == 2


def test_adversarial_09_controls_only_are_unsupported() -> None:
    incident = generate_incident_003_v2(1019)
    target = incident.metadata["target_operation_id"]
    controls = tuple(
        str(row["evidence_id"])
        for rows in incident.structured_evidence.values()
        for row in rows
        if row.get("operation_id") != target
    )
    score = _score_evidence(controls)
    assert score.essential_requirement_coverage == 0.0
    assert score.evidence_supported is False


def test_adversarial_10_exactly_five_of_six_is_unsupported() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    candidate_ids = sorted(
        {
            evidence_id
            for requirement in rubric.requirements
            if requirement.kind == "essential"
            for path in requirement.acceptable_paths
            for evidence_id in path.evidence_ids
        }
    )
    score = None
    for size in range(len(candidate_ids) + 1):
        for candidate in combinations(candidate_ids, size):
            candidate_score = _score_evidence(candidate)
            if len(candidate_score.satisfied_essential_requirements) == 5:
                score = candidate_score
                break
        if score is not None:
            break
    assert score is not None
    assert score.essential_requirement_coverage == pytest.approx(5 / 6)
    assert score.evidence_supported is False


def test_adversarial_11_correct_rca_without_evidence_is_not_overall_correct() -> None:
    score = _score_response(replace(_correct_response(), supporting_evidence=()))
    assert score.exact_root_cause_correct is True
    assert score.evidence_supported is False
    assert score.overall_correct is False


def test_adversarial_12_complete_evidence_with_wrong_rca_is_not_overall_correct() -> None:
    score = _score_response(
        replace(_correct_response(), failure_mechanism="incorrect_state_transition")
    )
    assert score.evidence_supported is True
    assert score.exact_root_cause_correct is False
    assert score.overall_correct is False


def test_adversarial_13_complete_target_without_contrast_is_supported() -> None:
    score = _score_evidence(_target_core_ids())
    assert score.evidence_supported is True
    assert score.contrast_requirement_coverage == 0.0


def test_adversarial_14_legitimate_contrast_increases_contrast_coverage() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    legitimate_path = next(
        path.evidence_ids
        for requirement in rubric.requirements
        if requirement.name == "legitimate_compensation_control"
        for path in requirement.acceptable_paths
        if path.path_id.endswith(":structured")
    )
    score = _score_evidence((*_target_core_ids(), *legitimate_path))
    assert score.evidence_supported is True
    assert score.contrast_requirement_coverage == 0.5


def test_adversarial_15_allowed_context_is_not_wrong_subject() -> None:
    incident = generate_incident_003_v2(1019)
    healthy = incident.metadata["healthy_control_operation_ids"][0]
    contextual = next(
        str(row["evidence_id"])
        for row in incident.structured_evidence["dependency_health"]
        if row["operation_id"] == healthy
    )
    score = _score_evidence((*_target_core_ids(), contextual))
    assert score.evidence_supported is True
    assert score.wrong_subject_citation_count == 0
    assert score.contextual_citation_count == 1
    assert contextual in score.contextual_evidence_ids


def test_adversarial_16_structured_and_log_alternatives_are_equivalent() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    identity = next(
        requirement
        for requirement in rubric.requirements
        if requirement.name == "target_identity_linkage"
    )
    structured = next(
        path.evidence_ids
        for path in identity.acceptable_paths
        if path.path_id.endswith(":structured")
    )
    logs = next(
        path.evidence_ids
        for path in identity.acceptable_paths
        if path.path_id.endswith(":logs")
    )
    for alternative in (structured, logs):
        score = _score_evidence(alternative)
        assert score.essential_requirement_coverage == 1.0
        assert len(score.satisfied_essential_requirements) == 6
        assert score.evidence_supported is True


def test_adversarial_17_redundant_structured_and_logs_do_not_inflate_coverage() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    identity = next(
        requirement
        for requirement in rubric.requirements
        if requirement.name == "target_identity_linkage"
    )
    all_ids = tuple(
        evidence_id
        for path in identity.acceptable_paths
        for evidence_id in path.evidence_ids
    )
    score = _score_evidence(all_ids)
    assert score.essential_requirement_coverage == 1.0
    assert len(score.satisfied_essential_requirements) == 6


def test_exact_rca_v3_requires_all_labels_and_semantic_evidence() -> None:
    score = _score_response(_correct_response())
    assert isinstance(score, RCAScoreV3)
    assert score.exact_root_cause_correct is True
    assert score.evidence_supported is True
    assert score.overall_correct is True


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
        incident_v3 = generate_incident_003_v2(1019)
        score_response_v3(  # type: ignore[arg-type]
            incident_v3,
            response_v2,
            build_incident_003_v2_evidence_rubric(incident_v3),
        )
    with pytest.raises(ProtocolVersionError, match="RCAResponseV2"):
        score_response_v2(v1_incident, _correct_response())  # type: ignore[arg-type]
