#!/usr/bin/env python3
"""Session state management for AgyBar."""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

STATE_DIR = Path("/tmp/agybar")


def ensure_state_dir() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR


def get_state_file(conversation_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", conversation_id)
    return ensure_state_dir() / f"{safe_id}.json"


class SessionState:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.file_path = get_state_file(conversation_id)
        self.data: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "start_time": time.time(),
            "last_update": time.time(),
            "status": "running",
            "total_steps": 4,  # default baseline until plan is declared
            "current_step": 1,
            "step_name": "Initializing task",
            "plan_steps": [],
            "plan_detected": False,
            "tool_history": [],
        }
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception:
                pass

    def save(self) -> None:
        self.data["last_update"] = time.time()
        try:
            ensure_state_dir()
            temp_file = self.file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(temp_file, self.file_path)
        except Exception:
            pass

    def record_tool_call(self, tool_name: str, args: Dict[str, Any], step_idx: int) -> None:
        action_desc = self._summarize_tool(tool_name, args)
        self.data["tool_history"].append({
            "step_idx": step_idx,
            "tool": tool_name,
            "action": action_desc,
            "time": time.time(),
        })

        # If no explicit plan, advance step gradually based on tool calls
        if not self.data.get("plan_detected"):
            tools_count = len(self.data["tool_history"])
            # dynamic scaling: if tools exceed total_steps - 1, expand total_steps
            if tools_count >= self.data["total_steps"]:
                self.data["total_steps"] = tools_count + 1
            self.data["current_step"] = min(tools_count, self.data["total_steps"])
            self.data["step_name"] = action_desc
        else:
            self.data["step_name"] = action_desc

        self.save()

    def mark_completed(self) -> None:
        self.data["status"] = "completed"
        self.data["current_step"] = self.data["total_steps"]
        self.data["step_name"] = "All steps completed"
        self.save()

    def sync_from_transcript(self, transcript_path: Optional[str]) -> bool:
        """Scan the conversation transcript for explicit plan tags or markdown step markers."""
        if not transcript_path or not os.path.exists(transcript_path):
            return False

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return False

        # Scan backwards or entire lines for plan declarations
        text_block = "".join(lines)

        # 1. Look for explicit JSON tag: <!-- agybar:plan {"total": 4, "steps": [...]} -->
        plan_match = re.search(r"<!--\s*agybar:plan\s*(\{.*?\})\s*-->", text_block, re.DOTALL)
        if plan_match:
            try:
                plan_json = json.loads(plan_match.group(1))
                total = int(plan_json.get("total", 0))
                steps = plan_json.get("steps", [])
                if total > 0:
                    self.data["total_steps"] = total
                    self.data["plan_steps"] = steps
                    self.data["plan_detected"] = True
            except Exception:
                pass

        # 2. Look for explicit step tag: <!-- agybar:step {"current": 2, "name": "..."} -->
        step_match = re.findall(r"<!--\s*agybar:step\s*(\{.*?\})\s*-->", text_block, re.DOTALL)
        if step_match:
            try:
                latest_step = json.loads(step_match[-1])
                curr = int(latest_step.get("current", self.data["current_step"]))
                name = latest_step.get("name", self.data["step_name"])
                self.data["current_step"] = curr
                self.data["step_name"] = name
            except Exception:
                pass

        # 3. Heuristic fallback: Regex match patterns like "Step 2/5: Editing files" or "[Step 2/5]"
        heuristic_steps = re.findall(r"\[?(?:Step|Phase)\s+(\d+)\s*/\s*(\d+)\]?:?\s*([^\n\r`]{2,50})", text_block, re.IGNORECASE)
        if heuristic_steps:
            last_curr, last_total, last_name = heuristic_steps[-1]
            try:
                c = int(last_curr)
                t = int(last_total)
                if t >= c and t > 0:
                    self.data["total_steps"] = t
                    self.data["current_step"] = c
                    self.data["step_name"] = last_name.strip()
                    self.data["plan_detected"] = True
            except Exception:
                pass

        self.save()
        return True

    def _summarize_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name == "run_command":
            cmd = args.get("CommandLine", "")
            summary = args.get("toolSummary", "")
            return summary or f"Executing: {cmd[:35]}..." if len(cmd) > 35 else f"Executing: {cmd}"
        elif tool_name in ("edit_file", "write_file", "read_file"):
            path = args.get("Path", "")
            basename = os.path.basename(path) if path else "file"
            action = "Editing" if tool_name == "edit_file" else ("Writing" if tool_name == "write_file" else "Reading")
            return f"{action} {basename}"
        elif tool_name == "search_web":
            q = args.get("query", "")
            return f"Web search: {q[:30]}..." if len(q) > 30 else f"Web search: {q}"
        elif tool_name == "invoke_subagent":
            role = args.get("Role", "Subagent")
            return f"Delegating to {role}"
        return f"Running {tool_name}"
