#!/usr/bin/env python3
"""Antigravity lifecycle hook runner for AgyBar."""

import json
import sys
from pathlib import Path

# Add scripts directory to module lookup path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from state import SessionState
from renderer import ProgressBarRenderer


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
            renderer.render(state.data, newline=False)
            response = {"decision": "allow"}

        elif event_name == "PostToolUse":
            response = {}

        elif event_name == "Stop":
            state.mark_completed()
            renderer.render(state.data, newline=True)
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
