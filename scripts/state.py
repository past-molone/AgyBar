#!/usr/bin/env python3
"""Session state management & Universal Plan Sniffer for AgyBar.

Supports Gemini Antigravity (agy), Claude Code, Gemini CLI, and generic AI agents.
Automatically detects and adapts to existing planning plugins/skills (e.g., TODO.md,
markdown checklists, planning tools) without requiring a proprietary format.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

STATE_DIR = Path("/tmp/agybar")

# Common plan files that external skills or user workflows create
COMMON_PLAN_FILES = [
    "TODO.md",
    "todo.md",
    "PLAN.md",
    "plan.md",
    "TASKS.md",
    "tasks.md",
    ".plan.md",
    ".tasks.md",
    ".agents/plan.md",
    ".claude/plan.md",
]


def ensure_state_dir() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR


def get_state_file(conversation_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", conversation_id)
    return ensure_state_dir() / f"{safe_id}.json"


class SessionState:
    def __init__(self, conversation_id: str, workspace_path: Optional[str] = None):
        self.conversation_id = conversation_id
        self.workspace_path = workspace_path or os.getcwd()
        self.file_path = get_state_file(conversation_id)
        self.data: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "workspace_path": self.workspace_path,
            "start_time": time.time(),
            "last_update": time.time(),
            "status": "running",
            "total_steps": 4,  # Adaptive baseline until plan is detected
            "current_step": 1,
            "step_name": "Initializing task",
            "plan_source": "adaptive",  # "external_file" | "transcript_checklist" | "explicit_tag" | "adaptive"
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

        # Check if workspace plan file was created/updated during execution
        if not self.data.get("plan_detected") or self.data.get("plan_source") == "external_file":
            self.sniff_workspace_plan_files()

        if not self.data.get("plan_detected"):
            tools_count = len(self.data["tool_history"])
            if tools_count >= self.data["total_steps"]:
                self.data["total_steps"] = tools_count + 1
            self.data["current_step"] = min(tools_count, self.data["total_steps"])
            self.data["step_name"] = action_desc
        else:
            # Plan exists: update active tool action without overriding step name if already set
            if not self.data.get("step_name") or self.data.get("step_name") == "Initializing task":
                self.data["step_name"] = action_desc

        self.save()

    def mark_completed(self) -> None:
        self.data["status"] = "completed"
        self.data["current_step"] = self.data["total_steps"]
        self.data["step_name"] = "All steps completed"
        self.save()

    def sniff_workspace_plan_files(self) -> bool:
        """Inspect common plan/todo files created by other AI skills (e.g. TODO.md, plan.md)."""
        ws = Path(self.workspace_path)
        for rel_path in COMMON_PLAN_FILES:
            plan_file = ws / rel_path
            if plan_file.exists() and plan_file.is_file():
                try:
                    content = plan_file.read_text(encoding="utf-8")
                    parsed = self._parse_markdown_checklist(content)
                    if parsed:
                        total, done, current_idx, active_task, all_steps = parsed
                        if total > 0:
                            self.data["total_steps"] = total
                            self.data["current_step"] = current_idx
                            self.data["step_name"] = active_task
                            self.data["plan_steps"] = all_steps
                            self.data["plan_detected"] = True
                            self.data["plan_source"] = f"file:{rel_path}"
                            self.save()
                            return True
                except Exception:
                    pass
        return False

    def sync_from_transcript(self, transcript_path: Optional[str]) -> bool:
        """Universal transcript parser.

        First checks for existing workspace plan files.
        Then checks for markdown checklists (- [ ] / - [x]) in the conversation.
        Finally falls back to explicit tags or numbered steps.
        """
        # 1. Check if an external planning skill already created a plan file
        if self.sniff_workspace_plan_files():
            return True

        if not transcript_path or not os.path.exists(transcript_path):
            return False

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return False

        # 2. Check for markdown checklists anywhere in the conversation (- [ ] / - [x])
        parsed_checklist = self._parse_markdown_checklist(content)
        if parsed_checklist:
            total, done, current_idx, active_task, all_steps = parsed_checklist
            if total >= 2:  # Valid multi-step checklist found from another plugin/skill
                self.data["total_steps"] = total
                self.data["current_step"] = current_idx
                self.data["step_name"] = active_task
                self.data["plan_steps"] = all_steps
                self.data["plan_detected"] = True
                self.data["plan_source"] = "transcript_checklist"
                self.save()
                return True

        # 3. Check for explicit JSON tag: <!-- agybar:plan {"total": 4, "steps": [...]} -->
        plan_match = re.search(r"<!--\s*agybar:plan\s*(\{.*?\})\s*-->", content, re.DOTALL)
        if plan_match:
            try:
                plan_json = json.loads(plan_match.group(1))
                total = int(plan_json.get("total", 0))
                steps = plan_json.get("steps", [])
                if total > 0:
                    self.data["total_steps"] = total
                    self.data["plan_steps"] = steps
                    self.data["plan_detected"] = True
                    self.data["plan_source"] = "explicit_tag"
            except Exception:
                pass

        # 4. Check for explicit step tag: <!-- agybar:step {"current": 2, "name": "..."} -->
        step_match = re.findall(r"<!--\s*agybar:step\s*(\{.*?\})\s*-->", content, re.DOTALL)
        if step_match:
            try:
                latest_step = json.loads(step_match[-1])
                curr = int(latest_step.get("current", self.data["current_step"]))
                name = latest_step.get("name", self.data["step_name"])
                self.data["current_step"] = curr
                self.data["step_name"] = name
            except Exception:
                pass

        # 5. Check for numbered headers e.g. "### Step 2: Implement..." or "[Step 2/5]"
        heuristic_steps = re.findall(
            r"\[?(?:Step|Phase)\s+(\d+)\s*/\s*(\d+)\]?:?\s*([^\n\r`]{2,50})",
            content,
            re.IGNORECASE,
        )
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
                    self.data["plan_source"] = "numbered_step"
            except Exception:
                pass

        self.save()
        return True

    def _parse_markdown_checklist(self, text: str) -> Optional[Tuple[int, int, int, str, List[str]]]:
        """Detects standard markdown task lists used by Claude Code, GitHub, and planning plugins.

        Matches:
          - [ ] Task 1
          - [x] Task 2
          - [X] Task 3
          * [ ] Task 4
          1. [ ] Task 5
        """
        pattern = r"^[ \t]*(?:[-*]|\d+\.)\s*\[([ xX\-\/])\]\s*(.+)$"
        matches = re.findall(pattern, text, re.MULTILINE)
        if not matches:
            return None

        all_steps = []
        done_count = 0
        first_pending = ""
        current_idx = 1

        for idx, (status, task_desc) in enumerate(matches, 1):
            clean_desc = task_desc.strip()
            # Strip markdown formatting like **bold**
            clean_desc = re.sub(r"[*_`]", "", clean_desc)
            all_steps.append(clean_desc)

            if status in ("x", "X"):
                done_count += 1
            elif not first_pending:
                first_pending = clean_desc
                current_idx = idx

        total = len(matches)
        if done_count == total:
            current_idx = total
            active_task = all_steps[-1] if all_steps else "All items completed"
        else:
            active_task = first_pending or (all_steps[0] if all_steps else "In progress")

        return total, done_count, current_idx, active_task, all_steps

    def _summarize_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        # Standard Antigravity tools
        if tool_name == "run_command":
            cmd = args.get("CommandLine", "")
            summary = args.get("toolSummary", "")
            return summary or (f"Executing: {cmd[:35]}..." if len(cmd) > 35 else f"Executing: {cmd}")
        elif tool_name in ("edit_file", "write_file", "read_file"):
            path = args.get("Path", "")
            basename = os.path.basename(path) if path else "file"
            action = "Editing" if tool_name == "edit_file" else ("Writing" if tool_name == "write_file" else "Reading")
            return f"{action} {basename}"
        # Claude Code / generic CLI tools
        elif tool_name in ("Bash", "bash", "execute_command"):
            cmd = args.get("command", "")
            return f"Executing: {cmd[:35]}..." if len(cmd) > 35 else f"Executing: {cmd}"
        elif tool_name in ("FileEdit", "Edit", "str_replace_editor"):
            path = args.get("file_path", args.get("path", ""))
            return f"Editing {os.path.basename(path)}" if path else "Editing file"
        elif tool_name in ("FileView", "View", "read"):
            path = args.get("file_path", args.get("path", ""))
            return f"Reading {os.path.basename(path)}" if path else "Reading file"
        elif tool_name in ("FileCreate", "write"):
            path = args.get("file_path", args.get("path", ""))
            return f"Writing {os.path.basename(path)}" if path else "Writing file"
        elif tool_name == "search_web":
            q = args.get("query", "")
            return f"Web search: {q[:30]}..." if len(q) > 30 else f"Web search: {q}"
        elif tool_name == "invoke_subagent":
            role = args.get("Role", "Subagent")
            return f"Delegating to {role}"
        return f"Running {tool_name}"
