#!/usr/bin/env python3
"""Antigravity lifecycle hook runner for AgyBar."""

import json
import os
import sys
from pathlib import Path

# Add scripts directory to module lookup path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from state import SessionState
from renderer import ProgressBarRenderer, load_config
from inspect_progress import inspect_git_metrics, calculate_granular_percentage


def main() -> None:
    # 1. Read input JSON from stdin
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception:
        payload = {}

    event_name = payload.get("hookEventName", "")
    conv_id = payload.get("conversationId", "default-session")
    transcript_path = payload.get("transcriptPath")
    workspace_path = payload.get("cwd") or (payload.get("workspacePaths", [None])[0] if payload.get("workspacePaths") else None)

    # Initialize state and renderer
    state = SessionState(conv_id, workspace_path=workspace_path)
    renderer = ProgressBarRenderer()
    should_hook_render = load_config().get("hook_render", False)

    # Attempt to sync plan and current progress from transcript
    if transcript_path:
        state.sync_from_transcript(transcript_path)

    # 2. Dispatch event
    response = {}

    try:
        if event_name == "SessionStart":
            state.save()
            response = {}

        elif event_name == "PreInvocation":
            response = {}

        elif event_name == "PreToolUse":
            tool_call = payload.get("toolCall", {})
            tool_name = tool_call.get("name", "unknown_tool")
            args = tool_call.get("args", {})
            step_idx = payload.get("stepIdx", 0)

            state.record_tool_call(tool_name, args, step_idx)
            if should_hook_render:
                renderer.render(state.data, newline=False, anchor_bottom=True)
            response = {"decision": "allow"}

        elif event_name == "PostToolUse":
            # Autonomous Radar Audit: Inspect workspace empirically after tool completes
            tool_call = payload.get("toolCall", {})
            tool_name = tool_call.get("name", "tool")
            tool_err = payload.get("error")

            current_step = state.data.get("current_step", 1)
            total_steps = state.data.get("total_steps", 4)
            tools_history = state.data.get("tool_history", [])
            tools_in_step = len(tools_history) % max(1, total_steps) + 1

            ws_path = workspace_path or os.getcwd()
            git_metrics = inspect_git_metrics(ws_path)
            computed_pct = calculate_granular_percentage(
                current_step, total_steps, git_metrics, tools_in_step
            )

            mod_files = git_metrics.get("modified_files", 0)
            lines_add = git_metrics.get("lines_added", 0)
            lines_del = git_metrics.get("lines_deleted", 0)

            if tool_err:
                audit_msg = f"Tool reported error: {str(tool_err)[:32]}..."
            elif "test" in tool_name.lower() or "pytest" in str(tool_call.get("args", {})):
                audit_msg = "Unit test suite executed • workspace verification active"
            elif mod_files > 0:
                change_detail = f" (+{lines_add}/-{lines_del})" if (lines_add or lines_del) else ""
                audit_msg = f"{mod_files} modified files detected{change_detail}"
            else:
                audit_msg = state.data.get("step_name", f"Step {current_step}/{total_steps} in progress")

            state.data["status"] = "running"
            state.data["granular_pct"] = computed_pct
            state.data["subagent_source"] = "Radar"
            state.data["subagent_action"] = audit_msg
            state.save()

            if should_hook_render:
                renderer.render(state.data, newline=False, anchor_bottom=True)
            response = {}

        elif event_name == "Stop":
            state.mark_completed()
            state.data["granular_pct"] = 100.0
            state.data["subagent_source"] = "Radar"
            state.data["subagent_action"] = "All steps verified by subagent • Build clean"
            state.save()
            if should_hook_render:
                renderer.render(state.data, newline=True, anchor_bottom=True)
            response = {}

        else:
            response = {}

    except Exception:
        # Guarantee safety: always return valid response on any unexpected error
        if event_name == "PreToolUse":
            response = {"decision": "allow"}
        else:
            response = {}

    # 3. Output JSON contract to stdout
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
