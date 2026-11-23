# AgyBar Universal Planning Protocol (Claude Code)

You are equipped with **AgyBar**, a real-time progress bar and task tracking system.

## 1. Respect Existing Plans & Plugins First
* **Existing Plans / Skills**: If you are already using a planning skill (such as `/plan`, an active `TODO.md`, a task runner, or a markdown task checklist like `- [ ]` / `- [x]`), **continue using it normally**.
* **Automatic Detection**: AgyBar automatically discovers, synchronizes with, and displays progress for your existing plan without requiring changes to your workflow.

## 2. When No Plan Exists
Only if **no plan, checklist, or planning skill is present** and you are embarking on a non-trivial multi-step task:
* Provide a standard markdown checklist:
  ```markdown
  - [ ] Investigate issue
  - [ ] Implement changes
  - [ ] Run test suite
  - [ ] Review and verify
  ```

## 3. Subagent Progress Inspection (Granular Precision)
For multi-file or long-running tasks, run:
```bash
python3 scripts/inspect_progress.py --step <current> --total <total>
```
or output fine-grained telemetry tags:
```html
<!-- agybar:progress {"percent": 63.5, "action": "2/3 files patched, verifying tests"} -->
```
This enables exact, continuous percentages (e.g. `51.6%` -> `63.5%`) rather than jumping in broad block increments.

## 4. Concise Milestones
Keep milestone descriptions short (under 40 characters) so they display cleanly on the user's terminal status line.
