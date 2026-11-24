#!/usr/bin/env python3
"""Native CLI statusline handler for AgyBar.

Outputs high-precision, pastel-themed progress telemetry directly to stdout
for Claude Code and Gemini Antigravity (agy) native statusline slots.
Anchored directly under the user's interactive typing prompt and shortcut help line,
remaining rock-solid and unchanging in position.
"""

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from state import STATE_DIR, SessionState, get_latest_session_file
from renderer import ProgressBarRenderer, RESET, DIM, BOLD, load_config


def read_stdin_json(timeout_sec: float = 0.05) -> Dict[str, Any]:
    """Safely read JSON payload from stdin without blocking or hanging."""
    try:
        if not sys.stdin.isatty():
            rlist, _, _ = select.select([sys.stdin], [], [], timeout_sec)
            if rlist:
                raw = sys.stdin.read()
                if raw.strip():
                    return json.loads(raw)
    except Exception:
        pass
    return {}


def resolve_session(payload: Dict[str, Any]) -> Tuple[Optional[SessionState], Dict[str, Any]]:
    """Resolve active SessionState from stdin payload or latest cache."""
    conv_id = payload.get("session_id") or payload.get("conversationId")
    transcript_path = payload.get("transcript_path") or payload.get("transcriptPath")
    cwd = payload.get("cwd")
    if not cwd and isinstance(payload.get("workspace"), dict):
        cwd = payload.get("workspace", {}).get("current_dir")

    state = None
    if conv_id:
        candidate = SessionState(conv_id, workspace_path=cwd)
        if candidate.file_path.exists():
            state = candidate
        else:
            return None, payload
    else:
        latest = get_latest_session_file()
        if latest and latest.exists():
            try:
                with open(latest, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    c_id = saved_data.get("conversation_id", "default")
                    ws = cwd or saved_data.get("workspace_path")
                    state = SessionState(c_id, workspace_path=ws)
            except Exception:
                pass

    if state:
        if transcript_path and os.path.exists(transcript_path):
            state.sync_from_transcript(transcript_path)
        else:
            state.sniff_workspace_plan_files()

    return state, payload


def _run_chain_command(cmd: str, payload: Dict[str, Any]) -> Optional[str]:
    """Execute chained fallback statusline command if configured."""
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=1.5,
        )
        out = res.stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return None


def generate_statusline(payload: Optional[Dict[str, Any]] = None) -> str:
    """Generate the formatted statusline string."""
    if payload is None:
        payload = read_stdin_json()

    conf = load_config()
    renderer = ProgressBarRenderer()
    state, payload = resolve_session(payload)

    # Context window & model details from CLI if provided
    ctx_pct = None
    if isinstance(payload.get("context_window"), dict):
        ctx_pct = payload["context_window"].get("used_percentage")

    model_display = None
    if isinstance(payload.get("model"), dict):
        model_display = payload["model"].get("display_name")

    chain_cmd = conf.get("chain_command")

    if not state or not state.data:
        if chain_cmd:
            chained = _run_chain_command(chain_cmd, payload)
            if chained:
                return chained

        idle_mode = conf.get("idle_display", "ready")
        if idle_mode == "empty":
            return ""
        badge = renderer.format_badge("idle")
        ctx_str = f" • {int(ctx_pct)}% ctx" if ctx_pct is not None else ""
        model_str = f" [{model_display}]" if model_display else ""
        return f"{badge} {DIM}Idle • Ready{model_str}{ctx_str}{RESET}"

    status = state.data.get("status", "running")
    last_update = state.data.get("last_update", 0)
    now = time.time()

    # Append context telemetry to Radar line if available
    if ctx_pct is not None:
        current_action = state.data.get("subagent_action") or state.data.get("step_name") or ""
        if current_action and "ctx" not in current_action:
            state.data["subagent_action"] = f"{current_action} • {int(ctx_pct)}% ctx"

    if status == "running":
        return renderer.format_line(state.data)

    elif status == "completed":
        completed_at = state.data.get("completed_at") or state.data.get("last_update", 0)
        # Keep completed badge visible for 60 seconds after finish
        if now - completed_at <= 60:
            return renderer.format_line(state.data)
        else:
            if chain_cmd:
                chained = _run_chain_command(chain_cmd, payload)
                if chained:
                    return chained

            idle_mode = conf.get("idle_display", "ready")
            if idle_mode == "empty":
                return ""
            badge = renderer.format_badge("idle")
            ctx_str = f" • {int(ctx_pct)}% ctx" if ctx_pct is not None else ""
            model_str = f" [{model_display}]" if model_display else ""
            return f"{badge} {DIM}Idle • Ready{model_str}{ctx_str}{RESET}"

    return renderer.format_line(state.data)


def main() -> None:
    line = generate_statusline()
    if line:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
