from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from diagbench.audits.relative_time_v1 import (
    audit_relative_time_incident,
    audit_relative_time_range,
    audit_seed_1021_equality,
    incident_003_privacy_invariant_matrix,
)
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagbench.relative_time import (
    RELATIVE_TIME_SEMANTICS_VERSION,
    after,
    before,
    equal,
    interval_duration_seconds,
    intervals_overlap,
    ordered_sequence,
    paired_before,
    parse_relative_time,
)
from diagbench.temporal import parse_timestamp
from diagpriv.evaluation import cli as evaluation_cli
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
)
from diagpriv.evaluation.manifest import ExperimentManifest, RecoveryProvenance
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.relative_time_v1 import (
    ANCHOR_RULE,
    PRECISION,
    TRANSFORMATION_VERSION,
    relative_time_incident,
    transformation_configuration,
    transformation_configuration_json,
    transformation_configuration_sha256,
)
from diagpriv.transformations.provenance import (
    transformation_configuration_for_condition,
    transformation_configuration_sha256 as hash_transformation_configuration,
)
from diagpriv.transformations.tokenization_v1 import tokenize_incident

ROOT = Path(__file__).parents[1]
CONFIG = (
    ROOT
    / "experiments"
    / "incident_003_v2_relative_time_v1_sol_development.toml"
)
EXPECTED_HASHES = {
    1019: "606420ee8a2832b5e2ceee584ceb0c5133dec90785632d7ee1e28a8c32d23cda",
    1020: "ffff6212ea681333d391b0271635c91222c15b05d0f45daeb26b9e76f3939523",
    1021: "b70bf4170fc96755b1ad2e97e80f3c307edbdf0fbdbce61d4ec91336e4f0a8c0",
    1022: "782134836be932b1510abadd833a58437d56afaa5b56df715e6576e99012e90b",
    1023: "c9df2c0f54c9b99747f846d3414df86a7864570046b5ca258a89a0cce5fdfd9e",
    1025: "603990c45c51cfa4f28fb522404f73c9e0422a4436ab6d6a9d12fb74dc112723",
    1026: "4a62763f53e76517d7f4c30ce0861c3df081ad177250f05ff30681fc3a2ee40b",
    1028: "03426719e9173d5a562713673a602b588fb49f38e42f1b56c868f36ed51bbf6d",
}
EXPECTED_RUBRIC_HASHES = {
    1019: "c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db",
    1020: "d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377",
    1021: "e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac",
    1022: "f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64",
    1023: "5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60",
    1025: "03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5",
    1026: "d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b",
    1028: "2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26",
}
EXPECTED_TRANSFORMATION_CONFIG_SHA256 = (
    "cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660"
)


def _run_config(seed: int) -> RawRunConfig:
    return RawRunConfig(
        experiment_id=f"relative-time-v1-offline-{seed}",
        seed=seed,
        model="offline-fixture",
        model_version=None,
        incident_family=INCIDENT_003_V2_FAMILY,
        manifest_schema_version="raw-rca-manifest-v10",
        reasoning_effort="medium",
        condition="relative-time-v1",
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Temperature is intentionally omitted.",
        prompt_version="raw-rca-v3",
        expected_model_input_sha256=EXPECTED_HASHES.get(seed),
        expected_evidence_requirement_set_sha256=EXPECTED_RUBRIC_HASHES.get(seed),
        expected_incident_generator_version="incident-003-generator-v2",
        expected_incident_protocol_version="incident-003-temporal-protocol-v2",
        expected_evidence_support_version="evidence-support-v3",
        expected_transformation_configuration_sha256=(
            EXPECTED_TRANSFORMATION_CONFIG_SHA256
        ),
    )


def _response(seed: int) -> RCAResponseV3:
    incident = generate_incident_003_v2(seed)
    oracle = incident.ground_truth_v3
    assert oracle is not None
    evidence_ids = tuple(
        str(row["evidence_id"])
        for rows in incident.model_view().structured_evidence.values()
        for row in rows
    )[:6]
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=evidence_ids,
        explanation="Offline manifest-v10 fixture.",
        confidence=0.9,
    )


def _timestamp_values(incident, view) -> tuple[str, ...]:
    values: list[str] = []
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            for entry in view.log_evidence:
                data = entry.to_dict()
                values.append(str(data[field] if field in data else entry.attributes[field]))
        else:
            values.extend(str(row[field]) for row in view.structured_evidence[source])
    return tuple(values)


def test_relative_parser_is_strict_and_raw_parser_is_unchanged() -> None:
    assert RELATIVE_TIME_SEMANTICS_VERSION == "relative-time-semantics-v1"
    assert parse_relative_time("T+0ms") == 0
    assert parse_relative_time("T+1250ms") == 1250
    assert before("T+0ms", "T+1250ms")
    assert after("T+1250ms", "T+0ms")
    assert equal("T+1250ms", "T+1250ms")
    assert interval_duration_seconds("T+250ms", "T+1250ms") == 1.0
    assert ordered_sequence(("T+0ms", "T+1ms", "T+1250ms"))
    assert paired_before(("T+0ms", "T+1ms", "T+2ms", "T+3ms"))
    assert intervals_overlap("T+0ms", "T+10ms", "T+5ms", "T+12ms")
    assert parse_timestamp("2036-01-01T00:00:00.000Z").tzinfo is not None
    with pytest.raises(ValueError, match="temporal-semantics-v1"):
        parse_timestamp("T+0ms")


@pytest.mark.parametrize(
    "value",
    ["T+00ms", "T+-1ms", "T+1s", "T+1.0ms", "T +1ms", "2036-01-01T00:00:00Z", ""],
)
def test_relative_parser_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(ValueError, match="relative-time-semantics-v1"):
        parse_relative_time(value)


def test_transform_uses_one_visible_anchor_and_is_metadata_independent() -> None:
    incident = generate_incident_003_v2(1019)
    transformed = relative_time_incident(incident)
    values = _timestamp_values(incident, transformed)
    assert min(map(parse_relative_time, values)) == 0
    assert transformed == relative_time_incident(incident)

    changed_metadata = dict(incident.metadata)
    changed_metadata.update(
        {
            "target_operation_id": "NOT-VISIBLE-ANCHOR",
            "temporal_template_name": "NOT-AN-ANCHOR",
        }
    )
    assert relative_time_incident(replace(incident, metadata=changed_metadata)) == transformed
    assert transformation_configuration() == {
        "transformation_version": "relative-time-v1",
        "temporal_semantics_version": "relative-time-semantics-v1",
        "anchor_rule": "earliest-model-visible-annotated-timestamp-v1",
        "precision": "milliseconds",
        "representation": "T+<nonnegative-integer>ms",
        "annotation_classification": "operational_timestamp",
        "scope_policy": "annotated-model-view-fields-only",
    }
    assert transformation_configuration_json() == (
        '{"anchor_rule":"earliest-model-visible-annotated-timestamp-v1",'
        '"annotation_classification":"operational_timestamp",'
        '"precision":"milliseconds",'
        '"representation":"T+<nonnegative-integer>ms",'
        '"scope_policy":"annotated-model-view-fields-only",'
        '"temporal_semantics_version":"relative-time-semantics-v1",'
        '"transformation_version":"relative-time-v1"}'
    )
    assert (
        transformation_configuration_sha256()
        == EXPECTED_TRANSFORMATION_CONFIG_SHA256
    )
    assert TRANSFORMATION_VERSION == "relative-time-v1"
    assert ANCHOR_RULE == "earliest-model-visible-annotated-timestamp-v1"
    assert PRECISION == "milliseconds"


def test_same_instant_cross_source_equality_and_non_temporal_values_survive() -> None:
    incident = generate_incident_003_v2(1019)
    raw = incident.model_view()
    transformed = relative_time_incident(incident)
    operation_id = str(raw.structured_evidence["workflow_attempts"][0]["operation_id"])
    raw_workflow = next(
        row
        for row in raw.structured_evidence["workflow_attempts"]
        if row["operation_id"] == operation_id
    )
    transformed_workflow = next(
        row
        for row in transformed.structured_evidence["workflow_attempts"]
        if row["operation_id"] == operation_id
    )
    transformed_log = next(
        entry
        for entry in transformed.log_evidence
        if entry.attributes["operation_id"] == operation_id
        and entry.attributes["event_kind"] == "dispatch_recorded"
    )
    assert transformed_workflow["dispatched_at"] == transformed_log.timestamp
    assert parse_relative_time(str(transformed_workflow["dispatched_at"])) >= 0
    assert raw_workflow["operation_id"] == transformed_workflow["operation_id"]
    report = audit_relative_time_incident(incident)
    assert report["passed"] is True
    assert all(report["checks"].values())


def test_double_application_fails_closed_with_clear_message() -> None:
    incident = generate_incident_003_v2(1019)
    transformed = relative_time_incident(incident)
    already_transformed = replace(
        incident,
        structured_evidence=transformed.structured_evidence,
        log_evidence=transformed.log_evidence,
    )
    with pytest.raises(ValueError, match="refuses already-relative evidence"):
        relative_time_incident(already_transformed)


def test_literal_time_is_removed_and_all_temporal_invariants_hold() -> None:
    incident = generate_incident_003_v2(1020)
    raw = incident.model_view()
    transformed = relative_time_incident(incident)
    serialized = transformed.to_json()
    for literal in _timestamp_values(incident, raw):
        assert literal not in serialized
    assert "2036-" not in serialized
    assert "2037-" not in serialized
    assert "2038-" not in serialized
    results = evaluate_invariants(
        incident,
        transformed,
        temporal_semantics_version=RELATIVE_TIME_SEMANTICS_VERSION,
    )
    assert all(
        result.preserved and result.status == "genuine_preservation"
        for result in results
        if result.relation
        in {"ordered_before", "paired_before", "interval_seconds", "intervals_overlap"}
    )


def test_seed_1021_equal_completion_remains_genuine_equality() -> None:
    assert audit_seed_1021_equality() == {
        "seed": 1021,
        "raw_equal": True,
        "transformed_equal": True,
        "parsed_equal": True,
        "passed": True,
    }


def test_existing_privacy_transformations_remain_distinct_and_deterministic() -> None:
    incident = generate_incident_003_v2(1021)
    functions = (
        redact_incident,
        lambda value: hmac_incident(value, key=bytes(range(32))),
        tokenize_incident,
        format_preserving_incident,
    )
    relative = relative_time_incident(incident)
    for transform in functions:
        first = transform(incident)
        assert first == transform(incident)
        assert first != relative
    matrix = incident_003_privacy_invariant_matrix(incident)["conditions"]
    assert matrix["raw"]["literal_timestamp_secrecy"] == "broken"
    assert matrix["redaction-v1"]["timestamp_equality"] == "degenerate"
    for condition in ("hmac-v1", "tokenization-v1", "format-preserving-v1"):
        assert matrix[condition]["required_temporal_invariants"] == (
            "expected_non_preservation"
        )
    assert set(matrix["relative-time-v1"].values()) == {"genuine_preservation"}


def test_200_instance_relative_time_audit_passes_and_requires_milliseconds() -> None:
    report = audit_relative_time_range(range(1000, 1200))
    assert report["sample_size"] == 200
    assert report["seed_min"] == 1000
    assert report["seed_max"] == 1199
    assert report["failed_check_evaluations"] == 0
    assert report["passed_check_evaluations"] == report["check_evaluations"]
    assert report["precision_audit"]["all_values_millisecond_aligned"] is True
    assert report["precision_audit"]["milliseconds_required"] is True
    assert report["precision_audit"]["strict_distinctions_lost_at_second_precision"] > 0
    assert report["seed_1021_equality"]["passed"] is True
    assert report["passed"] is True


@pytest.mark.parametrize("seeds", [(999,), (1200,), (1000, 2000), ()])
def test_relative_time_audit_refuses_nonconstruction_or_empty_ranges(seeds) -> None:
    with pytest.raises(ValueError, match="1000-1199"):
        audit_relative_time_range(seeds)


def test_future_config_is_development_only_and_fully_preregistered() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert definition.condition == "relative-time-v1"
    assert definition.incident_family == INCIDENT_003_V2_FAMILY
    assert definition.development_seeds == INCIDENT_003_V2_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.prompt_version == "raw-rca-v3"
    assert definition.taxonomy_version == "rca-taxonomy-v3"
    assert definition.scorer_version == "raw-rca-scorer-v3"
    assert definition.manifest_schema_version == "raw-rca-manifest-v10"
    assert definition.expected_model_input_sha256_by_seed == EXPECTED_HASHES
    assert definition.expected_evidence_requirement_set_sha256_by_seed == (
        EXPECTED_RUBRIC_HASHES
    )
    assert definition.transformation_version == "relative-time-v1"
    assert definition.transformation_semantics_version == (
        "relative-time-semantics-v1"
    )
    assert definition.transformation_annotation_classification == (
        "operational_timestamp"
    )
    assert definition.transformation_scope_policy == (
        "annotated-model-view-fields-only"
    )
    assert definition.expected_transformation_configuration_sha256 == (
        EXPECTED_TRANSFORMATION_CONFIG_SHA256
    )


def test_preregistered_model_and_rubric_hashes_reconstruct_exactly() -> None:
    for seed in INCIDENT_003_V2_DEVELOPMENT_SEEDS:
        prepared = prepare_model_input(_run_config(seed))
        assert prepared.model_input_sha256 == EXPECTED_HASHES[seed]
        assert prepared.evidence_requirement_set_sha256 == EXPECTED_RUBRIC_HASHES[seed]
        assert hashlib.sha256(prepared.prompt.encode("utf-8")).hexdigest() == (
            EXPECTED_HASHES[seed]
        )
        assert all(
            marker not in prepared.prompt
            for marker in (
                "ground_truth_v3",
                "diagnostic_invariants",
                "expected_evidence",
                "sensitive_fields",
                "target_operation_id",
            )
        )


def test_manifest_v10_round_trips_complete_transformation_provenance() -> None:
    seed = 1019
    manifest = run_raw_experiment(
        _run_config(seed), FakeProvider(raw_output=_response(seed).to_json())
    )
    assert manifest.manifest_schema_version == "raw-rca-manifest-v10"
    provenance = manifest.transformation_provenance
    assert provenance is not None
    assert provenance.configuration() == transformation_configuration()
    assert (
        provenance.transformation_configuration_sha256
        == EXPECTED_TRANSFORMATION_CONFIG_SHA256
    )
    serialized = manifest.to_dict()
    assert serialized["transformation_provenance"] == {
        **transformation_configuration(),
        "transformation_configuration_sha256": (
            EXPECTED_TRANSFORMATION_CONFIG_SHA256
        ),
    }
    assert manifest.score is not None
    assert "selected_evidence_paths" in serialized["score"]["evidence"]
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_manifest_v9_raw_protocol_remains_without_transformation_provenance() -> None:
    seed = 1019
    raw_v9_config = replace(
        _run_config(seed),
        condition="raw",
        manifest_schema_version="raw-rca-manifest-v9",
        expected_model_input_sha256=None,
        expected_transformation_configuration_sha256=None,
    )
    manifest = run_raw_experiment(
        raw_v9_config,
        FakeProvider(raw_output=_response(seed).to_json()),
    )
    assert manifest.manifest_schema_version == "raw-rca-manifest-v9"
    assert manifest.transformation_provenance is None
    assert "transformation_provenance" not in manifest.to_dict()
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_historical_manifest_v2_through_v8_round_trips_unchanged() -> None:
    seed = 1019
    base = replace(
        _run_config(seed),
        condition="raw",
        expected_model_input_sha256=None,
        expected_transformation_configuration_sha256=None,
    )
    manifests: list[ExperimentManifest] = []
    for version in range(2, 7):
        manifests.append(
            run_raw_experiment(
                replace(
                    base,
                    manifest_schema_version=f"raw-rca-manifest-v{version}",
                ),
                FakeProvider(raw_output=_response(seed).to_json()),
            )
        )
    v7 = run_raw_experiment(
        replace(
            base,
            manifest_schema_version="raw-rca-manifest-v7",
            trial_index=1,
        ),
        FakeProvider(raw_output=_response(seed).to_json()),
    )
    manifests.append(v7)
    recovery = RecoveryProvenance(
        recovery_protocol_version="incident-002-transport-recovery-v1",
        recovery_attempt_index=1,
        recovery_of_trial_index=2,
        original_condition="redaction-v1",
        original_seed=1001,
        original_failure_type="TimeoutError",
        original_experiment_id="historical-fixture",
        original_result_artifact="results/historical-fixture.jsonl",
        original_result_artifact_sha256="1" * 64,
    )
    manifests.append(
        replace(
            v7,
            manifest_schema_version="raw-rca-manifest-v8",
            seed=1001,
            condition="redaction-v1",
            trial_index=2,
            recovery_provenance=recovery,
        )
    )
    assert [manifest.manifest_schema_version for manifest in manifests] == [
        f"raw-rca-manifest-v{version}" for version in range(2, 9)
    ]
    for manifest in manifests:
        assert manifest.transformation_provenance is None
        assert "transformation_provenance" not in manifest.to_dict()
        assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_manifest_v10_raw_uses_explicit_canonical_nontransformation() -> None:
    seed = 1019
    raw_configuration = transformation_configuration_for_condition("raw")
    config = replace(
        _run_config(seed),
        condition="raw",
        expected_model_input_sha256=None,
        expected_transformation_configuration_sha256=(
            hash_transformation_configuration(raw_configuration)
        ),
    )
    manifest = run_raw_experiment(
        config, FakeProvider(raw_output=_response(seed).to_json())
    )
    provenance = manifest.transformation_provenance
    assert provenance is not None
    assert provenance.configuration() == raw_configuration
    assert provenance.transformation_version == "raw"
    assert provenance.scope_policy == "no-transformation"
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_transformed_v10_missing_configuration_hash_fails_before_invocation() -> None:
    provider = FakeProvider(raw_output=_response(1019).to_json())
    with pytest.raises(
        ValueError,
        match="requires a preregistered transformation configuration SHA-256",
    ):
        run_raw_experiment(
            replace(
                _run_config(1019),
                expected_transformation_configuration_sha256=None,
            ),
            provider,
        )
    assert provider.requests == []


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            EXPECTED_TRANSFORMATION_CONFIG_SHA256,
            "0" * 64,
            "Transformation configuration SHA-256 mismatch",
        ),
        (
            'temporal_semantics_version = "relative-time-semantics-v1"',
            'temporal_semantics_version = "unknown-temporal-semantics"',
            "frozen transformation configuration",
        ),
    ],
)
def test_invalid_provenance_fails_before_provider_initialization(
    old: str,
    new: str,
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "invalid-relative-time.toml"
    changed.write_text(
        CONFIG.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )
    provider_initialized = False

    def provider_must_not_be_configured(definition: PilotDefinition):
        nonlocal provider_initialized
        provider_initialized = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(changed),
            "--results",
            str(tmp_path / "must-not-exist.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match=message):
        args.handler(args)
    assert provider_initialized is False


def test_runtime_configuration_is_rehashed_immediately_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_configuration = transformation_configuration()
    runtime_configuration["precision"] = "seconds"
    provider_initialized = False

    def changed_runtime_configuration(condition: str) -> dict[str, str]:
        assert condition == "relative-time-v1"
        return runtime_configuration

    def provider_must_not_be_configured(definition: PilotDefinition):
        nonlocal provider_initialized
        provider_initialized = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(
        "diagpriv.evaluation.runner.transformation_configuration_for_condition",
        changed_runtime_configuration,
    )
    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIG),
            "--results",
            str(tmp_path / "must-not-exist.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match="Transformation configuration SHA-256 mismatch"):
        args.handler(args)
    assert provider_initialized is False


@pytest.mark.parametrize("seed", [1000, 1018, 1024, 1027, 1029, 1999, 2000, 20000])
def test_relative_time_runner_rejects_every_nonfrozen_seed_before_generation(
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
        prepare_model_input(_run_config(seed))
    assert generated is False


def test_relative_time_dry_run_preflights_without_provider_or_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = tmp_path / "relative-time.jsonl"

    def provider_must_not_be_configured(definition: PilotDefinition):
        raise AssertionError(f"Provider configured: {definition.pilot_id}")

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIG), "--results", str(result)]
    )
    args.handler(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution"] == "pending"
    assert payload["scheduled_calls"] == 8
    assert payload["pilot"]["transformation"] == transformation_configuration()
    assert payload["pilot"]["input_provenance"][
        "transformation_configuration_sha256"
    ] == EXPECTED_TRANSFORMATION_CONFIG_SHA256
    assert payload["input_preflight"][
        "transformation_configuration_sha256"
    ] == EXPECTED_TRANSFORMATION_CONFIG_SHA256
    assert payload["input_preflight"]["model_input_sha256_by_seed"] == {
        str(seed): digest for seed, digest in EXPECTED_HASHES.items()
    }
    assert payload["input_preflight"][
        "evidence_requirement_set_sha256_by_seed"
    ] == {str(seed): digest for seed, digest in EXPECTED_RUBRIC_HASHES.items()}
    assert result.exists() is False
