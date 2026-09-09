from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.schema import Incident
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt import PROMPT_SHA256 as PROMPT_SHA256_V1
from diagpriv.evaluation.prompt_v2 import (
    PROMPT_SHA256 as PROMPT_SHA256_V2,
    PROMPT_VERSION as PROMPT_VERSION_V2,
    build_prompt_v2,
    prompt_template_v2,
)
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.reporting import summarize_manifests
from diagpriv.evaluation.response import (
    RCAResponse,
    RCAResponseV2,
    parse_response,
    parse_response_v2,
)
from diagpriv.evaluation.runner import RawRunConfig, run_raw_experiment
from diagpriv.evaluation.scoring import score_response
from diagpriv.evaluation.scoring_v2 import (
    ProtocolVersionError,
    RCAScoreV2,
    score_response_v2,
)
from diagpriv.evaluation.taxonomy_v2 import (
    CATEGORIES_BY_FIELD,
    TAXONOMY_VERSION,
)

ROOT = Path(__file__).parents[1]
VALIDATION_CONFIG = ROOT / "experiments" / "raw_pilot_v2_validation.toml"


def _expected_ids(seed: int = 1001) -> tuple[str, ...]:
    incident = generate_incident_001(seed)
    return tuple(
        sorted(
            {
                str(reference.selector["evidence_id"])
                for expected in incident.expected_evidence
                for reference in expected.references
            }
        )
    )


def _correct_response_v2(seed: int = 1001) -> RCAResponseV2:
    oracle = generate_incident_001(seed).ground_truth_v2
    return RCAResponseV2(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=_expected_ids(seed),
        explanation="A deadline led to a repeated arrival that produced two effects.",
        confidence=0.95,
    )


def test_v2_oracle_uses_approved_five_dimensional_decomposition() -> None:
    incident = generate_incident_001(1001)
    assert incident.ground_truth_v2.to_dict() == {
        "observed_outcome": "duplicate_effect",
        "trigger": "timeout_or_deadline",
        "subsequent_action": "retry_or_rearrival",
        "failure_mechanism": "missing_or_ineffective_idempotency",
        "affected_component": "operation_executor",
        "logical_operation_repeated": True,
        "explanation": (
            "A caller repeated one logical operation after a response deadline, "
            "and the operation executor persisted both arrivals as distinct effects."
        ),
    }
    restored = Incident.from_json(incident.to_json())
    assert restored.ground_truth_v2 == incident.ground_truth_v2


def test_v2_accepts_every_canonical_label_in_its_declared_field() -> None:
    baseline = _correct_response_v2().to_dict()
    for field, categories in CATEGORIES_BY_FIELD.items():
        for category in categories:
            parsed = parse_response_v2(json.dumps({**baseline, field: category}))
            assert parsed.status == "valid", (field, category, parsed.error)


@pytest.mark.parametrize(
    ("field", "noncanonical_value"),
    [
        ("observed_outcome", "duplicate_charge"),
        ("trigger", "response_timeout"),
        ("subsequent_action", "retry"),
        ("failure_mechanism", "missing_idempotency"),
        ("affected_component", "payment_worker"),
    ],
)
def test_v2_rejects_noncanonical_semantic_aliases(
    field: str, noncanonical_value: str
) -> None:
    payload = {**_correct_response_v2().to_dict(), field: noncanonical_value}
    parsed = parse_response_v2(json.dumps(payload))
    assert parsed.status == "unknown_category"
    assert parsed.unknown_fields == (field,)


def test_v2_requires_subsequent_action() -> None:
    payload = _correct_response_v2().to_dict()
    del payload["subsequent_action"]
    parsed = parse_response_v2(json.dumps(payload))
    assert parsed.status == "missing_fields"
    assert "subsequent_action" in (parsed.error or "")


def test_v1_prompt_parser_and_alias_behavior_remain_frozen() -> None:
    response = RCAResponse(
        observed_outcome="double_charge",
        trigger="caller_retry_after_timeout",
        failure_mechanism="missing_idempotency",
        affected_component="payment_worker",
        supporting_evidence=(),
        explanation="Frozen v1 alias behavior.",
        confidence=0.5,
    )
    assert PROMPT_SHA256_V1 == (
        "0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd"
    )
    parsed = parse_response(response.to_json())
    assert parsed.status == "valid"
    assert isinstance(parsed.response, RCAResponse)
    assert "subsequent_action" not in response.to_dict()


def test_historical_v1_result_cannot_be_scored_as_v2() -> None:
    historical_path = (
        ROOT
        / "results"
        / "raw_pilot_v1_gpt_5_6_luna_medium_temperature_omitted_diagnostic_seed_1000.jsonl"
    )
    manifest = ExperimentManifest.from_json(
        historical_path.read_text(encoding="utf-8").strip()
    )
    assert manifest.prompt_version == "raw-rca-v1"
    assert manifest.taxonomy_version == "rca-taxonomy-v1"
    assert manifest.scorer_version == "raw-rca-scorer-v1"
    assert isinstance(manifest.response.response, RCAResponse)
    with pytest.raises(ProtocolVersionError, match="RCAResponseV2"):
        score_response_v2(generate_incident_001(1000), manifest.response.response)


def test_v2_ground_truth_and_other_oracle_data_are_absent_from_model_view() -> None:
    incident = generate_incident_001(1001)
    serialized = incident.model_view().to_json().lower()
    assert "ground_truth_v2" not in serialized
    assert "expected_evidence" not in serialized
    assert "diagnostic_invariants" not in serialized
    assert "sensitive_fields" not in serialized
    for value in (
        incident.ground_truth_v2.observed_outcome,
        incident.ground_truth_v2.trigger,
        incident.ground_truth_v2.subsequent_action,
        incident.ground_truth_v2.failure_mechanism,
        incident.ground_truth_v2.affected_component,
        incident.ground_truth_v2.explanation,
    ):
        assert value is None or value.lower() not in serialized


def test_v2_prompt_exposes_complete_taxonomy_without_identifying_the_answer() -> None:
    template = prompt_template_v2()
    assert PROMPT_VERSION_V2 == "raw-rca-v2"
    assert PROMPT_SHA256_V2 == (
        "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
    )
    for categories in CATEGORIES_BY_FIELD.values():
        for category in categories:
            assert f"\n{category}\n" in template

    oracle = generate_incident_001(1001).ground_truth_v2
    for correct_value in (
        oracle.observed_outcome,
        oracle.trigger,
        oracle.subsequent_action,
        oracle.failure_mechanism,
        oracle.affected_component,
    ):
        assert template.count(correct_value) == 1
    for forbidden in (
        "Incident 001",
        "duplicate_payment",
        "retry_after_timeout",
        "payment_worker",
        "ground_truth",
        "oracle",
    ):
        assert forbidden not in template


def test_v2_prompt_is_built_only_from_model_view() -> None:
    incident = generate_incident_001(1001)
    prompt = build_prompt_v2(incident.model_view())
    assert incident.model_view().to_json().strip() in prompt
    assert incident.ground_truth.explanation not in prompt
    assert incident.ground_truth_v2.explanation not in prompt


def test_exact_rca_v2_requires_all_five_dimensions() -> None:
    incident = generate_incident_001(1001)
    correct = _correct_response_v2()
    score = score_response_v2(incident, correct)
    assert score.exact_root_cause_correct
    assert score.subsequent_action_correct
    assert score.evidence_precision == 1.0
    assert score.evidence_recall == 1.0
    assert score.evidence_f1 == 1.0

    alternatives = {
        "observed_outcome": "missing_effect",
        "trigger": "dependency_error",
        "subsequent_action": "manual_reprocessing",
        "failure_mechanism": "incorrect_retry_policy",
        "affected_component": "state_store",
    }
    score_fields = {
        "observed_outcome": "outcome_correct",
        "trigger": "trigger_correct",
        "subsequent_action": "subsequent_action_correct",
        "failure_mechanism": "failure_mechanism_correct",
        "affected_component": "affected_component_correct",
    }
    for response_field, alternative in alternatives.items():
        changed = replace(correct, **{response_field: alternative})
        changed_score = score_response_v2(incident, changed)
        assert not getattr(changed_score, score_fields[response_field])
        assert not changed_score.exact_root_cause_correct
        assert changed_score.evidence_f1 == 1.0


def test_v2_preserves_v1_evidence_scoring_methodology() -> None:
    incident = generate_incident_001(1001)
    evidence = (*_expected_ids()[:-1], "SYN-EVD-00000000")
    v1_response = RCAResponse(
        observed_outcome=incident.ground_truth.outcome,
        trigger=incident.ground_truth.trigger,
        failure_mechanism=incident.ground_truth.failure_mechanism,
        affected_component=incident.ground_truth.affected_component,
        supporting_evidence=evidence,
        explanation="Evidence-method comparison.",
        confidence=0.5,
    )
    v2_response = replace(_correct_response_v2(), supporting_evidence=evidence)
    v1_score = score_response(incident, v1_response)
    v2_score = score_response_v2(incident, v2_response)
    for field in (
        "evidence_precision",
        "evidence_recall",
        "evidence_f1",
        "evidence_supported",
        "valid_evidence_ids",
        "matched_evidence_ids",
        "unknown_evidence_ids",
        "expected_evidence_ids",
    ):
        assert getattr(v2_score, field) == getattr(v1_score, field)


def test_v2_runner_versions_prompt_taxonomy_and_scorer_in_manifest() -> None:
    response = _correct_response_v2(1001)
    manifest = run_raw_experiment(
        RawRunConfig(
            experiment_id="raw-v2-test-1001",
            seed=1001,
            model="offline-fixture",
            model_version="1",
            reasoning_effort="medium",
            decoding_settings={"max_output_tokens": 4096},
            intended_temperature=0.0,
            temperature_omission_reason="Provider rejects temperature for this model.",
            prompt_version="raw-rca-v2",
            timestamp="2032-01-01T00:00:00+00:00",
        ),
        FakeProvider(raw_output=response.to_json()),
    )
    assert manifest.prompt_version == "raw-rca-v2"
    assert manifest.prompt_sha256 == PROMPT_SHA256_V2
    assert manifest.taxonomy_version == TAXONOMY_VERSION
    assert manifest.scorer_version == "raw-rca-scorer-v2"
    assert isinstance(manifest.response.response, RCAResponseV2)
    assert isinstance(manifest.score, RCAScoreV2)
    assert manifest.score.exact_root_cause_correct
    assert manifest.to_dict()["score"]["rca"]["subsequent_action_correct"] is True
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest
    assert summarize_manifests((manifest,)).development.subsequent_action_accuracy == 1.0


def test_v2_luna_pilot_is_development_only_and_omits_temperature() -> None:
    definition = PilotDefinition.load(ROOT / "experiments" / "raw_pilot_v2.toml")
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256_V2
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None


def test_v2_validation_pilot_is_exactly_the_approved_validation_scope() -> None:
    definition = PilotDefinition.load(VALIDATION_CONFIG)
    assert definition.pilot_id == "raw-pilot-v2-validation"
    assert definition.seed_scope == "validation_only"
    assert definition.development_seeds == ()
    assert definition.validation_seeds == tuple(range(2000, 2010))
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.condition == "raw"
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256_V2
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"


@pytest.mark.parametrize(
    ("original", "changed", "message"),
    [
        (
            "development_seeds = []",
            "development_seeds = [1000]",
            "Validation-only pilot cannot contain development seeds",
        ),
        (
            "held_out_seeds = []",
            "held_out_seeds = [20000]",
            "must not contain held-out seeds",
        ),
        (
            "validation_seeds = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009]",
            "validation_seeds = [1000]",
            "validation_seeds contains a non-validation seed",
        ),
    ],
)
def test_v2_validation_config_rejects_out_of_scope_seeds(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    config = tmp_path / "invalid-validation.toml"
    config.write_text(
        VALIDATION_CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(config)


@pytest.mark.parametrize(
    ("original", "changed"),
    [
        (
            'taxonomy_version = "rca-taxonomy-v2"',
            'taxonomy_version = "rca-taxonomy-v1"',
        ),
        (
            'scorer_version = "raw-rca-scorer-v2"',
            'scorer_version = "raw-rca-scorer-v1"',
        ),
    ],
)
def test_v2_validation_config_rejects_protocol_version_mismatch(
    tmp_path: Path, original: str, changed: str
) -> None:
    config = tmp_path / "invalid-protocol.toml"
    config.write_text(
        VALIDATION_CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="do not match a frozen protocol"):
        PilotDefinition.load(config)


def test_v2_validation_command_is_pending_without_execute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = tmp_path / "must-not-exist.jsonl"
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(VALIDATION_CONFIG),
            "--results",
            str(results),
        ]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["pilot"]["seed_scope"] == "validation_only"
    assert pending["pilot"]["development_seeds"] == []
    assert pending["pilot"]["validation_seeds"] == list(range(2000, 2010))
    assert pending["pilot"]["held_out_seeds"] == []
    assert not results.exists()
