"""Execute named experiments, preserving a result JSON and full log for each run.

Examples:
    python -m tests.run_experiments --experiments archived-reconstruction
    python -m tests.run_experiments --experiments ga-smoke --seed 20260323
    python -m tests.run_experiments --experiments full-replication --runs 10 --seed 20260323
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tests.logging_utils import LOGS_DIR, append_log, build_run_id
from tests.result_writer import RESULTS_DIR, save_result


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = (
    "archived-reconstruction",
    "ga-smoke",
    "full-replication",
)


def positive_integer(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments", nargs="+", choices=EXPERIMENTS, default=["archived-reconstruction"])
    parser.add_argument("--runs", type=positive_integer, default=10, help="GA runs for full-replication.")
    parser.add_argument("--seed", type=int, default=20260323, help="Base seed for new replications.")
    return parser.parse_args()


def stream_command(command: list[str], log_path: Path) -> None:
    append_log(log_path, "$ " + subprocess.list2cmdline(command))
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
        append_log(log_path, line)
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def commands_for(experiment: str, workspace: Path, runs: int, seed: int) -> list[list[str]]:
    runner = [sys.executable, "-m", "diet_optimization.experiments.runner"]
    if experiment == "archived-reconstruction":
        return [
            runner + ["--mode", "archived", "--output-dir", str(workspace)],
            [sys.executable, "-m", "tests.validate_reconstruction", "--workspace", str(workspace)],
        ]
    if experiment == "ga-smoke":
        return [runner + ["--mode", "rerun", "--runs", "1", "--seed", str(seed), "--output-dir", str(workspace)]]
    return [runner + ["--mode", "rerun", "--runs", str(runs), "--seed", str(seed), "--output-dir", str(workspace)]]


def execute(experiment: str, runs: int, seed: int) -> Path:
    run_id = build_run_id()
    workspace = RESULTS_DIR / "artifacts" / f"{experiment}_{run_id}"
    log_path = LOGS_DIR / f"{experiment}_{run_id}.log"
    commands = commands_for(experiment, workspace, runs, seed)
    started_at_utc = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    status = "passed"
    error = None
    try:
        for command in commands:
            stream_command(command, log_path)
    except Exception as exc:
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
        append_log(log_path, error)
    elapsed = time.perf_counter() - started
    result_path = save_result(
        experiment,
        run_id,
        {
            "schema_version": "1.0",
            "experiment": experiment,
            "run_id": run_id,
            "status": status,
            "started_at_utc": started_at_utc,
            "duration_seconds": elapsed,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "runs": 1 if experiment == "ga-smoke" else runs,
            "seed": None if experiment == "archived-reconstruction" else seed,
            "commands": commands,
            "log": str(log_path.relative_to(PROJECT_ROOT)),
            "artifact_workspace": str(workspace.relative_to(PROJECT_ROOT)),
            "error": error,
        },
    )
    print(f"Result: {result_path}")
    print(f"Log: {log_path}")
    if status != "passed":
        raise SystemExit(1)
    return result_path


def main() -> None:
    args = parse_args()
    for experiment in args.experiments:
        execute(experiment, args.runs, args.seed)


if __name__ == "__main__":
    main()
