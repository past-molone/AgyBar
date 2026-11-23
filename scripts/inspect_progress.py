#!/usr/bin/env python3
"""AgyBar Progress Inspector.

Used by the AI instance or a dedicated subagent to measure fine-grained,
empirical progress (0-100%) instead of relying on broad step increments.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from state import get_latest_session_file, SessionState, STATE_DIR


def inspect_git_metrics(workspace_dir: str) -> dict:
    """Inspects git status and diff stats to measure empirical progress."""
    metrics = {
        "modified_files": 0,
        "untracked_files": 0,
        "lines_added": 0,
        "lines_deleted": 0,
    }
    try:
        # Check modified & untracked files
        res = subprocess.run(
            ["git", "-C", workspace_dir, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            for line in lines:
                if line.startswith("??"):
                    metrics["untracked_files"] += 1
                elif line.strip():
                    metrics["modified_files"] += 1

        # Check diff line count
        diff_res = subprocess.run(
            ["git", "-C", workspace_dir, "diff", "--shortstat"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if diff_res.returncode == 0 and diff_res.stdout.strip():
            # e.g., "3 files changed, 45 insertions(+), 12 deletions(-)"
            text = diff_res.stdout.strip()
            import re
            ins = re.search(r"(\d+)\s+insertion", text)
            dels = re.search(r"(\d+)\s+deletion", text)
            if ins:
                metrics["lines_added"] = int(ins.group(1))
            if dels:
                metrics["lines_deleted"] = int(dels.group(1))
    except Exception:
        pass
    return metrics


def calculate_granular_percentage(
    current_step: int,
    total_steps: int,
    git_metrics: dict,
    tools_in_step: int = 1,
) -> float:
    """Calculates a fine-grained percentage between the step boundaries.

    For example, if current_step is 3 of 5 (boundary: 40% to 60%):
    Empirical indicators (files modified, tools run) smoothly interpolate
    between 41% and 59%.
    """
    if total_steps <= 0:
        total_steps = 1
    current_step = max(1, min(current_step, total_steps))

    # Base range for current step
    step_span = 100.0 / total_steps
    step_start = (current_step - 1) * step_span
    step_end = current_step * step_span

    # Micro-progress factors within the step
    # 1. Tool execution depth: 0-40% of the step span
    tool_factor = min(1.0, tools_in_step / 5.0) * 0.4

    # 2. Workspace modifications (files touched): 0-40% of the step span
    mod_count = git_metrics.get("modified_files", 0) + git_metrics.get("untracked_files", 0)
    work_factor = min(1.0, mod_count / 3.0) * 0.4

    # 3. Micro baseline (at least 10% through the step once started)
    base_factor = 0.1

    intra_step_ratio = min(0.95, base_factor + tool_factor + work_factor)
    granular_pct = step_start + (intra_step_ratio * step_span)

    return round(granular_pct, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgyBar Progress Inspector")
    parser.add_argument("--step", type=int, help="Current step number")
    parser.add_argument("--total", type=int, help="Total step count")
    parser.add_argument("--action", type=str, help="Specific action or subtask summary")
    parser.add_argument("--pct", type=float, help="Explicit percentage override (0-100)")
    parser.add_argument("--workspace", type=str, default=os.getcwd(), help="Workspace directory")
    parser.add_argument("--session", type=str, help="Conversation or session ID")

    args = parser.parse_args()

    # Load active session state
    session_file = Path(args.session) if args.session else get_latest_session_file()
    if session_file and session_file.exists():
        conv_id = session_file.stem
        state = SessionState(conv_id, workspace_path=args.workspace)
    else:
        conv_id = "inspector-session"
        state = SessionState(conv_id, workspace_path=args.workspace)

    current_step = args.step or state.data.get("current_step", 1)
    total_steps = args.total or state.data.get("total_steps", 5)

    git_metrics = inspect_git_metrics(args.workspace)
    tools_history = state.data.get("tool_history", [])
    tools_in_step = len(tools_history) % max(1, total_steps) + 1

    if args.pct is not None:
        computed_pct = max(0.0, min(100.0, args.pct))
    else:
        computed_pct = calculate_granular_percentage(
            current_step, total_steps, git_metrics, tools_in_step
        )

    action_text = args.action
    if not action_text:
        mod_files = git_metrics.get("modified_files", 0)
        if mod_files > 0:
            action_text = f"Subagent inspected: {mod_files} files modified"
        else:
            action_text = state.data.get("step_name", f"Step {current_step}/{total_steps} in progress")

    # Update session state with granular data
    state.data["current_step"] = current_step
    state.data["total_steps"] = total_steps
    state.data["granular_pct"] = computed_pct
    state.data["step_name"] = action_text
    state.save()

    # Output formatted telemetry tag
    tag = f'<!-- agybar:progress {{"percent": {computed_pct}, "action": "{action_text}", "source": "subagent"}} -->'
    print(tag)


if __name__ == "__main__":
    main()
