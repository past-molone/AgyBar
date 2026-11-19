# AgyBar Universal Planning Protocol

You are equipped with **AgyBar**, a real-time progress bar and task tracking system.

## 1. Respect Existing Plans & Plugins First
* **Existing Plans / Skills**: If you are already using a planning skill (such as `/plan`, an active `TODO.md`, a task runner, or a markdown task checklist like `- [ ]` / `- [x]`), **continue using it normally**.
* **Automatic Detection**: AgyBar automatically discovers, synchronizes with, and displays progress for your existing plan without requiring changes to your workflow.

## 2. When No Plan Exists
Only if **no plan, checklist, or planning skill is present** and you are embarking on a non-trivial multi-step task:
* Declare a brief task plan at the start of your turn:
  ```html
  <!-- agybar:plan {"total": 4, "steps": ["Investigate", "Draft solution", "Run tests", "Document"]} -->
  ```
  or simply provide a standard markdown checklist:
  ```markdown
  - [ ] Investigate issue
  - [ ] Implement changes
  - [ ] Run test suite
  - [ ] Review and verify
  ```

## 3. Concise Milestones
Keep milestone descriptions short (under 40 characters) so they display cleanly on the user's terminal status line.
