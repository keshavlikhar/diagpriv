from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from diagbench.audits.incident_003_destructive_baselines import (
    CONDITIONS,
    STATUS_DEGENERATE,
    STATUS_EXPECTED_NON_PRESERVATION,
    STATUS_GENUINE,
    TEMPORAL_SEMANTICS_UNAVAILABLE,
    audit_destructive_baseline_incident,
    audit_destructive_baseline_range,
    audit_destructive_evidence_satisfiability_range,
    destructive_condition_views,
)
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation import cli as evaluation_cli
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.evidence_support_v3 import score_evidence_support_v3
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v2_evidence_semantics import (
    Incident003V2EvidenceSemanticEvaluator,
)
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.transformations import relative_time_incident
from diagpriv.transformations.hmac_v1 import hmac_key_fingerprint
from diagpriv.transformations.provenance import (
    transformation_configuration_for_condition,
    transformation_configuration_sha256,
)

ROOT = Path(__file__).parents[1]
SAFE_AUDIT_KEY = bytes(range(32))
CONFIGS = {
    condition: ROOT
    / "experiments"
    / f"incident_003_v2_{condition.replace('-', '_')}_sol_development.toml"
    for condition in CONDITIONS
}
RESULT_PATHS = {
    condition: ROOT
    / "results"
    / f"incident_003_v2_{condition.replace('-', '_')}_sol_development_gpt_5_6_sol_medium.jsonl"
    for condition in CONDITIONS
}
RAW_CONFIG = ROOT / "experiments" / "incident_003_v2_raw_sol_development.toml"
RELATIVE_CONFIG = (
    ROOT
    / "experiments"
    / "incident_003_v2_relative_time_v1_sol_development.toml"
)
FROZEN_RESULT_SHA256 = {
    "raw": (
        ROOT
        / "results"
        / "incident_003_v2_raw_sol_development_gpt_5_6_sol_medium.jsonl",
        "54ab224d3b432a5a1531a3d9b11b7d15515eeba56bf05023304ace72344f4915",
    ),
    "relative-time-v1": (
        ROOT
        / "results"
        / "incident_003_v2_relative_time_v1_sol_development_gpt_5_6_sol_medium.jsonl",
        "0ecbb9f2b39a7529a7c5e056d4f57b1f440da9fb08f8c1a851b2939d27540bbb",
    ),
}


def _path_for(requirement_name: str, *, suffix: str = ":structured"):
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    return next(
        path
        for requirement in rubric.requirements
        if requirement.name == requirement_name
        for path in requirement.acceptable_paths
        if path.path_id.endswith(suffix)
    )


def _semantic_requirement_score(
    requirement_name: str,
    model_view,
    temporal_semantics_version: str,
    *,
    suffix: str = ":structured",
    extra_evidence: tuple[str, ...] = (),
):
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    path = next(
        path
        for requirement in rubric.requirements
        if requirement.name == requirement_name
        for path in requirement.acceptable_paths
        if path.path_id.endswith(suffix)
    )
    return score_evidence_support_v4(
        (*path.evidence_ids, *extra_evidence),
        model_view,
        rubric,
        Incident003V2EvidenceSemanticEvaluator(temporal_semantics_version),
    )


def _offline_run_config(condition: str, seed: int) -> RawRunConfig:
    rubric_hashes = PilotDefinition.load(
        RAW_CONFIG
    ).expected_evidence_requirement_set_sha256_by_seed
    rubric_hash = rubric_hashes.get(seed, next(iter(rubric_hashes.values())))
    configuration = transformation_configuration_for_condition(condition)
    return RawRunConfig(
        experiment_id=f"incident-003-destructive-offline-{condition}-{seed}",
        seed=seed,
        model="offline-fixture",
        model_version=None,
        incident_family=INCIDENT_003_V2_FAMILY,
        manifest_schema_version="raw-rca-manifest-v10",
        reasoning_effort="medium",
        condition=condition,  # type: ignore[arg-type]
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Temperature is intentionally omitted.",
        prompt_version="raw-rca-v3",
        hmac_key=SAFE_AUDIT_KEY if condition == "hmac-v1" else None,
        transformation_key_id=(
            "offline-test-key" if condition == "hmac-v1" else None
        ),
        expected_evidence_requirement_set_sha256=rubric_hash,
        expected_incident_generator_version="incident-003-generator-v2",
        expected_incident_protocol_version="incident-003-temporal-protocol-v2",
        expected_evidence_support_version="evidence-support-v4",
        expected_transformation_key_fingerprint=(
            hmac_key_fingerprint(SAFE_AUDIT_KEY)
            if condition == "hmac-v1"
            else None
        ),
        expected_transformation_configuration_sha256=(
            transformation_configuration_sha256(configuration)
        ),
    )


@pytest.mark.parametrize("condition", CONDITIONS)
def test_destructive_configs_freeze_one_matched_condition(condition: str) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    assert definition.incident_family == INCIDENT_003_V2_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v10"
    assert definition.condition == condition
    assert definition.development_seeds == INCIDENT_003_V2_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.result_path_must_not_exist is True
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert definition.decoding_settings == {"max_output_tokens": 4096}
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v3"
    assert definition.taxonomy_version == "rca-taxonomy-v3"
    assert definition.scorer_version == "raw-rca-scorer-v3"
    assert definition.expected_evidence_support_version == "evidence-support-v4"
    assert set(definition.expected_model_input_sha256_by_seed) == set(
        INCIDENT_003_V2_DEVELOPMENT_SEEDS
    )
    assert set(definition.expected_evidence_requirement_set_sha256_by_seed) == set(
        INCIDENT_003_V2_DEVELOPMENT_SEEDS
    )
    assert definition.expected_transformation_configuration_sha256 == (
        transformation_configuration_sha256(
            transformation_configuration_for_condition(condition)
        )
    )


def test_manifest_v10_records_evidence_support_v4() -> None:
    seed = 1019
    incident = generate_incident_003_v2(seed)
    oracle = incident.ground_truth_v3
    assert oracle is not None
    response = json.dumps(
        {
            "observed_outcome": oracle.observed_outcome,
            "trigger": oracle.trigger,
            "subsequent_action": oracle.subsequent_action,
            "failure_mechanism": oracle.failure_mechanism,
            "affected_component": oracle.affected_component,
            "supporting_evidence": [],
            "explanation": "Offline protocol-version fixture.",
            "confidence": 0.5,
        }
    )
    manifest = run_raw_experiment(
        _offline_run_config("redaction-v1", seed),
        FakeProvider(raw_output=response),
    )
    assert manifest.manifest_schema_version == "raw-rca-manifest-v10"
    assert manifest.scorer_version == "raw-rca-scorer-v3"
    assert manifest.evidence_support_version == "evidence-support-v4"


def test_planned_result_paths_are_unique_ignored_and_not_configuration_inputs() -> None:
    assert len(set(RESULT_PATHS.values())) == len(CONDITIONS)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "results/*" in gitignore
    for condition, result_path in RESULT_PATHS.items():
        assert condition.replace("-", "_") in result_path.name
        assert str(result_path.relative_to(ROOT)) not in CONFIGS[
            condition
        ].read_text(encoding="utf-8")


@pytest.mark.parametrize("condition", CONDITIONS)
def test_each_condition_dispatches_without_raw_fallback(condition: str) -> None:
    seed = INCIDENT_003_V2_DEVELOPMENT_SEEDS[0]
    prepared = prepare_model_input(_offline_run_config(condition, seed))
    assert prepared.model_view != prepared.incident.model_view()
    assert prepared.transformation_provenance is not None
    assert prepared.transformation_provenance.configuration() == (
        transformation_configuration_for_condition(condition)
    )


def test_temporal_ablation_is_restricted_to_incident_003_v2() -> None:
    with pytest.raises(ValueError, match="supports Incident 003 v2 only"):
        prepare_model_input(
            replace(
                _offline_run_config("temporal-ablation-v1", 1019),
                incident_family="incident_001",
                seed=1000,
                prompt_version="raw-rca-v2",
                expected_evidence_requirement_set_sha256=None,
                expected_incident_generator_version=None,
                expected_incident_protocol_version=None,
                expected_evidence_support_version=None,
            )
        )


@pytest.mark.parametrize("seed", [1000, 1018, 1024, 1027, 1029, 1999, 2000, 20000])
def test_destructive_conditions_reject_nonfrozen_seeds_before_generation(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated = False

    def fail_if_generated(candidate: int):
        nonlocal generated
        generated = True
        raise AssertionError(candidate)

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_003_v2",
        fail_if_generated,
    )
    with pytest.raises(ProtectedSeedError):
        prepare_model_input(_offline_run_config("redaction-v1", seed))
    assert generated is False


def test_condition_and_provenance_mismatch_fails_closed() -> None:
    definition = PilotDefinition.load(CONFIGS["redaction-v1"])
    with pytest.raises(ValueError, match="frozen transformation configuration"):
        replace(definition, condition="tokenization-v1").validate()
    with pytest.raises(ValueError, match="configuration SHA-256 mismatch"):
        replace(
            definition,
            expected_transformation_configuration_sha256="0" * 64,
        ).validate()


def test_destructive_evidence_protocol_version_drift_fails_closed() -> None:
    definition = PilotDefinition.load(CONFIGS["redaction-v1"])
    with pytest.raises(ValueError, match="frozen incident/evidence versions"):
        replace(
            definition,
            expected_evidence_support_version="evidence-support-v3",
        ).validate()
    with pytest.raises(ValueError, match="requires evidence-support-v4"):
        prepare_model_input(
            replace(
                _offline_run_config("redaction-v1", 1019),
                expected_evidence_support_version="evidence-support-v3",
            )
        )


def test_overwrite_protection_precedes_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "already-exists.jsonl"
    existing.write_text("historical\n", encoding="utf-8")
    provider_initialized = False

    def provider_must_not_initialize(definition: PilotDefinition):
        nonlocal provider_initialized
        provider_initialized = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_initialize)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIGS["redaction-v1"]),
            "--results",
            str(existing),
            "--execute",
        ]
    )
    with pytest.raises(SystemExit, match="already exists"):
        args.handler(args)
    assert provider_initialized is False
    assert existing.read_text(encoding="utf-8") == "historical\n"


def test_hash_mismatch_precedes_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid = tmp_path / "invalid.toml"
    text = CONFIGS["tokenization-v1"].read_text(encoding="utf-8")
    valid_hash = PilotDefinition.load(
        CONFIGS["tokenization-v1"]
    ).expected_transformation_configuration_sha256
    assert valid_hash is not None
    invalid.write_text(text.replace(valid_hash, "0" * 64), encoding="utf-8")
    provider_initialized = False

    def provider_must_not_initialize(definition: PilotDefinition):
        nonlocal provider_initialized
        provider_initialized = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_initialize)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(invalid),
            "--results",
            str(tmp_path / "unused.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match="configuration SHA-256 mismatch"):
        args.handler(args)
    assert provider_initialized is False


def test_hmac_config_records_only_external_key_reference_and_fingerprint() -> None:
    definition = PilotDefinition.load(CONFIGS["hmac-v1"])
    text = CONFIGS["hmac-v1"].read_text(encoding="utf-8")
    assert definition.hmac_key_environment_variable == "DIAGPRIV_HMAC_KEY_HEX"
    assert definition.hmac_key_id == "hmac-v1-synthetic-experiment-key-001"
    assert definition.expected_transformation_key_fingerprint == (
        "fd04c65f6329f9e8c42b392ea8b9253a6c88da58e6f3858a322228bee907997d"
    )
    assert "DIAGPRIV_HMAC_KEY_HEX=" not in text
    assert repr(_offline_run_config("hmac-v1", 1019)).find(SAFE_AUDIT_KEY.hex()) == -1


def test_wrong_hmac_fingerprint_fails_before_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider_initialized = False

    def provider_must_not_initialize(definition: PilotDefinition):
        nonlocal provider_initialized
        provider_initialized = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setenv("DIAGPRIV_HMAC_KEY_HEX", bytes(reversed(range(32))).hex())
    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_initialize)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIGS["hmac-v1"]),
            "--results",
            str(tmp_path / "must-not-exist.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match="HMAC key fingerprint differs"):
        args.handler(args)
    assert provider_initialized is False
    assert (tmp_path / "must-not-exist.jsonl").exists() is False


def test_offline_audit_distinguishes_destructive_semantics() -> None:
    report = audit_destructive_baseline_incident(
        generate_incident_003_v2(1019), hmac_key=SAFE_AUDIT_KEY
    )
    assert report["temporal_ablation_passed"] is True
    for condition in CONDITIONS:
        values = report["conditions"][condition]
        assert values["temporal_semantics_version"] == TEMPORAL_SEMANTICS_UNAVAILABLE
        assert values["transformation_determinism"] == STATUS_GENUINE
        assert values["timestamp_literal_secrecy"] == STATUS_GENUINE
        assert values["timestamp_parseability"] == STATUS_EXPECTED_NON_PRESERVATION
        assert values["strict_ordering"] == STATUS_EXPECTED_NON_PRESERVATION
        assert values["duration"] == STATUS_EXPECTED_NON_PRESERVATION
        assert values["positive_overlap"] == STATUS_EXPECTED_NON_PRESERVATION
        assert values["deadline_crossing"] == STATUS_EXPECTED_NON_PRESERVATION
        assert values["non_sensitive_operational_evidence"] == STATUS_GENUINE
        assert values["evidence_ids"] == STATUS_GENUINE
        assert values["row_cardinality"] == STATUS_GENUINE
    redaction = report["conditions"]["redaction-v1"]
    assert redaction["timestamp_equality"] == STATUS_DEGENERATE
    assert redaction["identifier_distinctness"] == STATUS_DEGENERATE
    assert redaction["cross_source_linkage"] == STATUS_EXPECTED_NON_PRESERVATION


def test_semantic_adversarial_01_raw_strict_before_is_satisfied() -> None:
    incident = generate_incident_003_v2(1019)
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        incident.model_view(),
        TEMPORAL_SEMANTICS_VERSION,
    )
    assert "deadline_before_original_completion" in score.satisfied_essential_requirements


def test_semantic_adversarial_02_relative_strict_before_is_satisfied() -> None:
    incident = generate_incident_003_v2(1019)
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        relative_time_incident(incident),
        RELATIVE_TIME_SEMANTICS_VERSION,
    )
    assert "deadline_before_original_completion" in score.satisfied_essential_requirements


@pytest.mark.parametrize("condition", CONDITIONS)
def test_semantic_adversarial_03_to_07_opaque_strict_before_is_unsatisfied(
    condition: str,
) -> None:
    incident = generate_incident_003_v2(1019)
    view = destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[condition]
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
    )
    assert "deadline_before_original_completion" in score.missing_essential_requirements


def test_semantic_adversarial_08_opaque_values_are_not_lexically_ordered() -> None:
    incident = generate_incident_003_v2(1019)
    view = deepcopy(
        destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[
            "temporal-ablation-v1"
        ]
    )
    path = _path_for("deadline_before_original_completion")
    workflow_id, execution_id = path.evidence_ids
    workflow = next(
        row
        for row in view.structured_evidence["workflow_attempts"]
        if row["evidence_id"] == workflow_id
    )
    execution = next(
        row
        for row in view.structured_evidence["execution_observations"]
        if row["evidence_id"] == execution_id
    )
    workflow["deadline_at"] = "A"
    execution["completed_at"] = "Z"
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
    )
    assert "deadline_before_original_completion" in score.missing_essential_requirements


def test_semantic_adversarial_09_structured_order_is_not_time() -> None:
    incident = generate_incident_003_v2(1019)
    view = destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[
        "temporal-ablation-v1"
    ]
    for rows in view.structured_evidence.values():
        rows.reverse()
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
    )
    assert "deadline_before_original_completion" in score.missing_essential_requirements


def test_semantic_adversarial_10_log_order_is_not_time() -> None:
    incident = generate_incident_003_v2(1019)
    view = destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[
        "redaction-v1"
    ]
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
        suffix=":logs",
    )
    assert "deadline_before_original_completion" in score.missing_essential_requirements


def test_semantic_adversarial_11_non_temporal_terminal_state_can_satisfy() -> None:
    incident = generate_incident_003_v2(1019)
    view = destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[
        "temporal-ablation-v1"
    ]
    score = _semantic_requirement_score(
        "inconsistent_terminal_workflow_effect_state",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
    )
    assert (
        "inconsistent_terminal_workflow_effect_state"
        in score.satisfied_essential_requirements
    )


def test_semantic_adversarial_12_redaction_collapse_is_not_identity() -> None:
    incident = generate_incident_003_v2(1019)
    view = destructive_condition_views(incident, hmac_key=SAFE_AUDIT_KEY)[
        "redaction-v1"
    ]
    score = _semantic_requirement_score(
        "target_identity_linkage",
        view,
        TEMPORAL_SEMANTICS_UNAVAILABLE,
    )
    assert "target_identity_linkage" in score.missing_essential_requirements


def test_semantic_adversarial_13_subject_binding_is_enforced() -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    target_path = _path_for("deadline_before_original_completion")
    control = next(
        binding.evidence_ids[0]
        for binding in rubric.subject_bindings
        if binding.role == "contrast"
    )
    score = score_evidence_support_v4(
        (target_path.evidence_ids[0], control),
        incident.model_view(),
        rubric,
        Incident003V2EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_VERSION),
    )
    assert "deadline_before_original_completion" in score.missing_essential_requirements


def test_semantic_adversarial_14_nonexistent_citation_is_invalid() -> None:
    incident = generate_incident_003_v2(1019)
    path = _path_for("deadline_before_original_completion")
    score = _semantic_requirement_score(
        "deadline_before_original_completion",
        incident.model_view(),
        TEMPORAL_SEMANTICS_VERSION,
        extra_evidence=("NOT-AN-EVIDENCE-ID",),
    )
    assert path.evidence_ids
    assert score.invalid_citation_count == 1
    assert score.evidence_supported is False


def test_semantic_adversarial_15_unbound_subject_vetoes_support() -> None:
    incident = generate_incident_003_v2(1019)
    view = incident.model_view()
    unrelated = dict(view.structured_evidence["workflow_attempts"][0])
    unrelated["evidence_id"] = "EV-UNBOUND-SUBJECT"
    unrelated["operation_id"] = "OP-UNBOUND-SUBJECT"
    view.structured_evidence["workflow_attempts"].append(unrelated)
    identity_path = _path_for("target_identity_linkage")
    score = _semantic_requirement_score(
        "target_identity_linkage",
        view,
        TEMPORAL_SEMANTICS_VERSION,
        extra_evidence=("EV-UNBOUND-SUBJECT",),
    )
    assert identity_path.evidence_ids
    assert score.essential_requirement_coverage == 1.0
    assert score.wrong_subject_citation_count == 1
    assert score.evidence_supported is False


def test_200_instance_destructive_baseline_audit() -> None:
    report = audit_destructive_baseline_range(
        range(1000, 1200), hmac_key=SAFE_AUDIT_KEY
    )
    assert report["passed"] is True
    assert report["sample_size"] == 200
    assert report["seed_min"] == 1000
    assert report["seed_max"] == 1199
    assert report["temporal_ablation_pass_count"] == 200
    for condition in CONDITIONS:
        values = report["conditions"][condition]
        assert values["transformation_determinism"]["counts"]["G"] == 200
        assert values["timestamp_literal_secrecy"]["counts"]["G"] == 200
        assert values["timestamp_parseability"]["counts"]["E"] == 200
        assert values["all_essential_temporal_invariants"]["counts"]["E"] == 200
        assert values["evidence_ids"]["counts"]["G"] == 200
        assert values["row_cardinality"]["counts"]["G"] == 200
        assert values["non_sensitive_operational_evidence"]["counts"]["G"] == 200
        assert values["parseable_timestamp_occurrences"] == 0


def test_200_instance_semantic_evidence_satisfiability_audit() -> None:
    report = audit_destructive_evidence_satisfiability_range(
        range(1000, 1200), hmac_key=SAFE_AUDIT_KEY
    )
    assert report["sample_size"] == 200
    assert report["no_temporal_false_positive"] is True
    conditions = report["conditions"]
    for condition in CONDITIONS:
        for requirement in (
            "deadline_before_original_completion",
            "compensation_after_deadline",
            "execution_compensation_overlap",
            "late_successful_original_effect",
        ):
            assert conditions[condition][requirement] == {
                "satisfied": 0,
                "unsatisfied": 200,
            }
    for condition in (
        "temporal-ablation-v1",
        "hmac-v1",
        "tokenization-v1",
        "format-preserving-v1",
    ):
        assert conditions[condition]["target_identity_linkage"]["satisfied"] == 200
        assert (
            conditions[condition][
                "inconsistent_terminal_workflow_effect_state"
            ]["satisfied"]
            == 200
        )
    assert conditions["redaction-v1"]["target_identity_linkage"]["satisfied"] == 0
    assert (
        conditions["redaction-v1"][
            "inconsistent_terminal_workflow_effect_state"
        ]["satisfied"]
        == 0
    )


def test_historical_raw_and_relative_preregistration_is_unchanged() -> None:
    raw = PilotDefinition.load(RAW_CONFIG)
    relative = PilotDefinition.load(RELATIVE_CONFIG)
    assert raw.manifest_schema_version == "raw-rca-manifest-v9"
    assert raw.condition == "raw"
    assert relative.condition == "relative-time-v1"
    assert relative.expected_transformation_configuration_sha256 == (
        "cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660"
    )
    assert len(raw.expected_model_input_sha256_by_seed) == 8
    assert len(relative.expected_model_input_sha256_by_seed) == 8


def test_frozen_historical_jsonls_are_unmodified_and_v3_reproducible() -> None:
    if not all(path.is_file() for path, _ in FROZEN_RESULT_SHA256.values()):
        pytest.skip("Frozen ignored result artifacts are not present in this checkout")
    for condition, (path, expected_digest) in FROZEN_RESULT_SHA256.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest
        for line in path.read_text(encoding="utf-8").splitlines():
            manifest = ExperimentManifest.from_json(line)
            assert manifest.evidence_support_version == "evidence-support-v3"
            assert manifest.response.response is not None
            assert manifest.score is not None
            incident = generate_incident_003_v2(manifest.seed)
            historical = score_evidence_support_v3(
                manifest.response.response.supporting_evidence,
                incident.model_view(),
                build_incident_003_v2_evidence_rubric(incident),
            )
            for field in (
                "essential_requirement_coverage",
                "contrast_requirement_coverage",
                "supportive_requirement_coverage",
                "useful_citation_precision",
                "invalid_citation_count",
                "invalid_citation_rate",
                "wrong_subject_citation_count",
                "redundant_citation_count",
                "redundant_citation_rate",
                "evidence_supported",
            ):
                assert getattr(historical, field) == getattr(manifest.score, field), (
                    condition,
                    manifest.seed,
                    field,
                )


@pytest.mark.parametrize("condition", tuple(item for item in CONDITIONS if item != "hmac-v1"))
def test_dry_run_verifies_eight_inputs_without_provider_or_result(
    condition: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = tmp_path / f"{condition}.jsonl"

    def provider_must_not_initialize(definition: PilotDefinition):
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_initialize)
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIGS[condition]), "--results", str(result)]
    )
    args.handler(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution"] == "pending"
    assert payload["scheduled_calls"] == 8
    assert payload["input_preflight"]["status"] == "verified"
    assert len(payload["input_preflight"]["model_input_sha256_by_seed"]) == 8
    assert result.exists() is False
