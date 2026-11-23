# ⚡ AgyBar

> **Real-Time Progress Bar & Plan Tracker for Gemini Antigravity & Claude Code**  
> *Supports Gemini Antigravity (`agy`) and Claude Code (`claude`).*

```text
⚡ AgyBar [████████████░░░░░░░░]  60% (3/5) • Running unit test suite [00:14]
```

**AgyBar** brings real-time visual progress tracking and live terminal telemetry to agentic AI CLIs. 

Most importantly, **AgyBar does not force the AI to recreate a plan if an existing plan already exists**. If your agent or project is already using a planning skill (such as `/plan`, an active `TODO.md`, or markdown checklists `- [ ]` / `- [x]`), AgyBar automatically discovers and synchronizes with that plan. Only when no plan exists does it prompt the agent to outline its steps.

---

## ✨ Features

* **Multi-CLI Support**: Tailored for Google Gemini Antigravity (`agy`) and Anthropic's Claude Code (`claude`).
* **Smart Plan Sniffing**: Automatically detects existing plans from `TODO.md`, `PLAN.md`, `/plan` skills, or conversation checklists without forcing duplicate planning.
* **Direct Terminal Telemetry**: Renders live updates directly to `/dev/tty` with ANSI colors, progress blocks (`████░░░░`), percentage, elapsed time, and active step name.
* **Adaptive Fallback**: If an agent starts working without an explicit plan, AgyBar's heuristic engine scales dynamically based on tool executions.
* **Zero Dependencies**: Pure Python 3 and Bash — no virtual environment or external dependencies required.
* **Flexible Installation**: Install globally across all projects, or locally within a specific repository.
* **Included CLI**: Inspect running sessions (`agybar status`), live-stream progress (`agybar watch`), or test animation styles (`agybar demo`).

---

## 🚀 Quick Start

### 1. Global Installation (Antigravity & Claude Code)
Installs AgyBar globally for all AI CLI instances on your machine:

```bash
./install.sh --global
```

Or target a specific CLI:
```bash
./install.sh --global --cli agy     # Antigravity only
./install.sh --global --cli claude  # Claude Code only
```

### 2. Project-Local Installation
Installs AgyBar into your current repository workspace:

```bash
./install.sh --project /path/to/my-project
```

---

## 🧠 Smart Plan Detection: How It Works

```
                        ┌──────────────────────────────────────────────┐
                        │              User Request                    │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         Universal Plan Sniffer               │
                        │                                              │
                        │  1. Check workspace plan files?              │
                        │     (TODO.md, PLAN.md, tasks.md)             │
                        │  2. Existing checklist in conversation?      │
                        │     (- [ ] Task A, - [x] Task B)             │
                        │  3. Planning skill active (/plan)?           │
                        └──────────────┬───────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
            [Plan Detected!]                  [No Plan Found]
     Adopts existing milestones          Rule prompts agent for a
     and tracks completion %             brief 3-5 step outline
                      │                                 │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   Real-Time Terminal Render  │
                        │   ⚡ AgyBar [██████░░] 60%    │
                        └──────────────────────────────┘
```

1. **Existing Plan Priority**: If a `TODO.md`, `PLAN.md`, or markdown checklist (`- [ ]`) is present, AgyBar parses the total tasks and marks progress as items are completed (`- [x]`).
2. **Lifecycle Hooks Engine**: Tracks tool calls (`PreToolUse`, `PostToolUse`, `Stop`) across Antigravity and Claude Code.
3. **Clean Output**: Uses controlling terminal writes (`/dev/tty`) so stdout/stderr output from agent tools is never corrupted.

---

## 🛠️ CLI Usage

AgyBar includes a standalone CLI binary located at `./bin/agybar`:

```bash
# Run a live animated demonstration
agybar demo

# Try alternative bar styles (blocks, ascii, dots)
agybar demo --style ascii
agybar demo --style dots

# Check the current or latest AI session status
agybar status

# Watch a live running task in a separate terminal split
agybar watch
```

---

## 📁 Repository Structure

```text
.
├── bin/
│   └── agybar                 # CLI executable
├── hooks.json                 # Antigravity & Claude Code lifecycle hooks
├── install.sh                 # Universal installer script
├── plugin.json                # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json            # Claude Code plugin manifest
├── rules/
│   ├── AGENTS.md              # Rule protocol for Antigravity
│   └── CLAUDE.md              # Rule protocol for Claude Code
├── scripts/
│   ├── cli.py                 # CLI commands (status, watch, demo, install)
│   ├── hook_runner.py         # Hook dispatcher
│   ├── renderer.py            # Terminal bar formatting & ANSI colors
│   └── state.py               # Universal Plan Sniffer & state engine
├── .gitignore
└── README.md
```

---

## 📄 License

MIT License. Free to use and customize across all your projects.
