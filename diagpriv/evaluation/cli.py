"""Command-line entry points for the raw RCA pilot and its summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.providers import OpenAIResponsesProvider
from diagpriv.evaluation.reporting import inspection_json, summarize_path
from diagpriv.evaluation.runner import (
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.transformations import parse_hmac_key_hex


def _openai_provider(
    definition: PilotDefinition,
) -> tuple[OpenAIResponsesProvider, str | None]:
    if definition.provider != "openai-responses":
        raise SystemExit(f"Unsupported provider: {definition.provider}")
    version_environment = definition.model_version_metadata_environment_variable
    model_version = (
        os.environ.get(version_environment) if version_environment else None
    )
    provider = OpenAIResponsesProvider()
    if not provider.is_configured:
        raise SystemExit(
            f"Required environment variable is not set: {provider.api_key_environment_variable}"
        )
    return provider, model_version


def _external_hmac_key(definition: PilotDefinition) -> bytes | None:
    if definition.condition != "hmac-v1":
        return None
    variable = definition.hmac_key_environment_variable
    if variable is None:
        raise SystemExit("hmac-v1 key environment variable is not configured")
    value = os.environ.get(variable)
    if value is None:
        raise SystemExit(f"Required environment variable is not set: {variable}")
    try:
        return parse_hmac_key_hex(value)
    except ValueError as error:
        raise SystemExit(f"Invalid HMAC key in {variable}: {error}") from error


def _run_pilot(args: argparse.Namespace) -> None:
    definition = PilotDefinition.load(args.config)
    if not args.execute:
        input_preflight = None
        if definition.expected_model_input_sha256_by_seed:
            input_preflight = _input_preflight(
                definition,
                hmac_key=_external_hmac_key(definition),
            )
        payload: dict[str, object] = {
            "execution": "pending",
            "pilot": definition.to_dict(),
            "scheduled_calls": (
                len(definition.development_seeds)
                + len(definition.validation_seeds)
            )
            * definition.calls_per_seed,
        }
        if input_preflight is not None:
            payload["input_preflight"] = input_preflight
        print(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
        )
        return
    if definition.trial_indices and args.results.exists():
        raise SystemExit(
            "Repeated-trial results path already exists; refusing to call provider"
        )
    hmac_key = _external_hmac_key(definition)
    if definition.expected_model_input_sha256_by_seed:
        _input_preflight(definition, hmac_key=hmac_key)
    provider, model_version = _openai_provider(definition)

    for seed in (*definition.development_seeds, *definition.validation_seeds):
        split = "development" if seed in definition.development_seeds else "validation"
        call_slots = (
            tuple(
                (trial_index, f"trial-{trial_index}")
                for trial_index in definition.trial_indices
            )
            if definition.trial_indices
            else tuple(
                (None, f"call-{call_index}")
                for call_index in range(1, definition.calls_per_seed + 1)
            )
        )
        for trial_index, call_label in call_slots:
            experiment_id = f"{definition.pilot_id}-{split}-{seed}-{call_label}"
            run_raw_experiment(
                RawRunConfig(
                    experiment_id=experiment_id,
                    seed=seed,
                    model=definition.requested_model,
                    model_version=model_version,
                    incident_family=definition.incident_family,
                    manifest_schema_version=definition.manifest_schema_version,
                    reasoning_effort=definition.reasoning_effort,
                    condition=definition.condition,
                    decoding_settings=dict(definition.decoding_settings),
                    intended_temperature=definition.intended_temperature,
                    temperature_omission_reason=(
                        definition.temperature_omission_reason
                    ),
                    prompt_version=definition.prompt_version,
                    hmac_key=hmac_key,
                    transformation_key_id=definition.hmac_key_id,
                    expected_model_input_sha256=(
                        definition.expected_model_input_sha256_by_seed.get(seed)
                    ),
                    expected_transformation_key_fingerprint=(
                        definition.expected_transformation_key_fingerprint
                    ),
                    trial_index=trial_index,
                ),
                provider,
                result_path=args.results,
            )
    pricing = PricingSnapshot.load(definition.pricing_snapshot_path)
    print(summarize_path(args.results, pricing).to_json(), end="")


def _input_preflight(
    definition: PilotDefinition, *, hmac_key: bytes | None
) -> dict[str, object]:
    hashes: dict[str, str] = {}
    trial_hashes: dict[str, dict[str, str]] = {
        str(index): {} for index in definition.trial_indices
    }
    fingerprint: str | None = None
    for seed in (*definition.development_seeds, *definition.validation_seeds):
        indices: tuple[int | None, ...] = (
            definition.trial_indices if definition.trial_indices else (None,)
        )
        prepared_for_seed = []
        for trial_index in indices:
            prepared = prepare_model_input(
                RawRunConfig(
                    experiment_id=(
                        f"{definition.pilot_id}-input-preflight-{seed}"
                    ),
                    seed=seed,
                    model=definition.requested_model,
                    model_version=None,
                    incident_family=definition.incident_family,
                    manifest_schema_version=definition.manifest_schema_version,
                    reasoning_effort=definition.reasoning_effort,
                    condition=definition.condition,
                    decoding_settings=dict(definition.decoding_settings),
                    intended_temperature=definition.intended_temperature,
                    temperature_omission_reason=(
                        definition.temperature_omission_reason
                    ),
                    prompt_version=definition.prompt_version,
                    hmac_key=hmac_key,
                    transformation_key_id=definition.hmac_key_id,
                    expected_model_input_sha256=(
                        definition.expected_model_input_sha256_by_seed[seed]
                    ),
                    expected_transformation_key_fingerprint=(
                        definition.expected_transformation_key_fingerprint
                    ),
                    trial_index=trial_index,
                )
            )
            prepared_for_seed.append(prepared)
            if trial_index is not None:
                trial_hashes[str(trial_index)][str(seed)] = (
                    prepared.model_input_sha256
                )
            if prepared.transformation_key_fingerprint is not None:
                fingerprint = prepared.transformation_key_fingerprint
        distinct_hashes = {
            prepared.model_input_sha256 for prepared in prepared_for_seed
        }
        if len(distinct_hashes) != 1:
            raise ValueError(
                f"Trial index altered model-visible input for seed {seed}"
            )
        hashes[str(seed)] = prepared_for_seed[0].model_input_sha256
    data: dict[str, object] = {
        "status": "verified",
        "model_input_sha256_by_seed": hashes,
    }
    if definition.hmac_key_id is not None:
        data["transformation_key_id"] = definition.hmac_key_id
    if definition.trial_indices:
        data["trial_indices"] = list(definition.trial_indices)
        data["model_input_sha256_by_trial"] = trial_hashes
    if fingerprint is not None:
        data["transformation_key_fingerprint"] = fingerprint
    return data


def _run_diagnostic(args: argparse.Namespace) -> None:
    """Run exactly one development seed into a new, collision-proof result file."""
    definition = PilotDefinition.load(args.config)
    if args.seed not in definition.development_seeds:
        raise SystemExit("Diagnostic seed must be in the configured development set")
    if definition.calls_per_seed != 1:
        raise SystemExit("Diagnostic execution requires calls_per_seed = 1")
    if not args.execute:
        print(
            json.dumps(
                {
                    "execution": "pending",
                    "experiment_id": args.experiment_id,
                    "seed": args.seed,
                    "split": "development",
                    "pilot": definition.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if args.results.exists():
        raise SystemExit(
            "Diagnostic results path already exists; refusing to call provider"
        )

    hmac_key = _external_hmac_key(definition)
    provider, model_version = _openai_provider(definition)
    manifest = run_raw_experiment(
        RawRunConfig(
            experiment_id=args.experiment_id,
            seed=args.seed,
            model=definition.requested_model,
            model_version=model_version,
            incident_family=definition.incident_family,
            manifest_schema_version=definition.manifest_schema_version,
            reasoning_effort=definition.reasoning_effort,
            condition=definition.condition,
            decoding_settings=dict(definition.decoding_settings),
            intended_temperature=definition.intended_temperature,
            temperature_omission_reason=definition.temperature_omission_reason,
            prompt_version=definition.prompt_version,
            hmac_key=hmac_key,
            transformation_key_id=definition.hmac_key_id,
        ),
        provider,
        result_path=args.results,
    )
    print(manifest.to_json(), end="")


def _summarize(args: argparse.Namespace) -> None:
    pricing = None if args.pricing is None else PricingSnapshot.load(args.pricing)
    print(summarize_path(args.results, pricing).to_json(), end="")


def _inspect(args: argparse.Namespace) -> None:
    print(inspection_json(args.results), end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-pilot", help="Run or inspect the pilot")
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--results", type=Path, required=True)
    run_parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly authorize real provider calls; omission is a dry run",
    )
    run_parser.set_defaults(handler=_run_pilot)

    diagnostic_parser = subparsers.add_parser(
        "run-diagnostic", help="Run exactly one configured development seed"
    )
    diagnostic_parser.add_argument("--config", type=Path, required=True)
    diagnostic_parser.add_argument("--results", type=Path, required=True)
    diagnostic_parser.add_argument("--experiment-id", required=True)
    diagnostic_parser.add_argument("--seed", type=int, required=True)
    diagnostic_parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly authorize one real provider call; omission is a dry run",
    )
    diagnostic_parser.set_defaults(handler=_run_diagnostic)

    summary_parser = subparsers.add_parser("summarize", help="Summarize JSONL results")
    summary_parser.add_argument("--results", type=Path, required=True)
    summary_parser.add_argument(
        "--pricing",
        type=Path,
        help="Versioned pricing snapshot used only for cost estimation",
    )
    summary_parser.set_defaults(handler=_summarize)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Show every raw response and individual score"
    )
    inspect_parser.add_argument("--results", type=Path, required=True)
    inspect_parser.set_defaults(handler=_inspect)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
