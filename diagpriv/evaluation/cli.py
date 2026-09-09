"""Command-line entry points for the raw RCA pilot and its summary."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import OpenAIResponsesProvider
from diagpriv.evaluation.reporting import summarize_path
from diagpriv.evaluation.runner import RawRunConfig, run_raw_experiment


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Required environment variable is not set: {name}")
    return value


def _run_pilot(args: argparse.Namespace) -> None:
    definition = PilotDefinition.load(args.config)
    if not args.execute:
        print(
            json.dumps(
                {"execution": "pending", "pilot": definition.to_dict()},
                indent=2,
                sort_keys=True,
            )
        )
        return
    if definition.provider != "openai-responses":
        raise SystemExit(f"Unsupported provider: {definition.provider}")

    model = _required_environment(definition.model_environment_variable)
    model_version = _required_environment(
        definition.model_version_environment_variable
    )
    provider = OpenAIResponsesProvider()
    if not provider.is_configured:
        raise SystemExit(
            f"Required environment variable is not set: {provider.api_key_environment_variable}"
        )

    for seed in (*definition.development_seeds, *definition.validation_seeds):
        split = "development" if seed in definition.development_seeds else "validation"
        for call_index in range(1, definition.calls_per_seed + 1):
            experiment_id = (
                f"{definition.pilot_id}-{split}-{seed}-call-{call_index}"
            )
            run_raw_experiment(
                RawRunConfig(
                    experiment_id=experiment_id,
                    seed=seed,
                    model=model,
                    model_version=model_version,
                    decoding_settings=dict(definition.decoding_settings),
                ),
                provider,
                result_path=args.results,
            )
    print(summarize_path(args.results).to_json(), end="")


def _summarize(args: argparse.Namespace) -> None:
    print(summarize_path(args.results).to_json(), end="")


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

    summary_parser = subparsers.add_parser("summarize", help="Summarize JSONL results")
    summary_parser.add_argument("--results", type=Path, required=True)
    summary_parser.set_defaults(handler=_summarize)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
