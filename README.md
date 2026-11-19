# ⚡ AgyBar

> **Real-Time Progress Bar & Planning Tracker for Gemini Antigravity (`agy`)**

```text
⚡ AgyBar [████████████░░░░░░░░]  60% (3/5) • Running unit test suite [00:14]
```

AgyBar brings real-time visual progress tracking to Google DeepMind's **Gemini Antigravity** agent instances. By combining a lightweight **Planning Protocol** with Antigravity's **Lifecycle Hooks**, AgyBar prompts the agent to establish a step count upfront, then monitors each tool operation to display live terminal telemetry.

---

## ✨ Features

* **Plan-First Architecture**: Encourages the agent to declare its roadmap and step milestones before diving into execution.
* **Zero Dependencies**: Pure Python 3 and Bash — no virtual environment, `pip install`, or external libraries required.
* **Antigravity Native**: Designed as a standard Antigravity plugin (`plugin.json`, `hooks.json`, `rules/AGENTS.md`).
* **Direct Terminal Telemetry**: Renders live updates directly to the controlling terminal (`/dev/tty`) with elapsed timers and clean ANSI styling.
* **Adaptive Fallback**: If an agent starts working without an explicit plan, AgyBar's heuristic engine scales dynamically based on tool executions.
* **Portable & Shareable**: Install once globally for all projects or per-project in `.agents/plugins/agybar/`.
* **Included CLI**: Inspect running sessions (`agybar status`), live-stream progress (`agybar watch`), or test animation styles (`agybar demo`).

---

## 🚀 Quick Start

### 1. Global Installation (Recommended)
Installs AgyBar so that **all Antigravity instances** across any repository automatically display the progress bar:

```bash
./install.sh --global
# Installs to ~/.gemini/config/plugins/agybar/
```

### 2. Project-Local Installation
To install AgyBar into a single repository:

```bash
./install.sh --project /path/to/your/project
# Installs to /path/to/your/project/.agents/plugins/agybar/
```

---

## 🛠️ CLI Usage

AgyBar includes a standalone CLI binary located at `./bin/agybar`:

```bash
# Run a live animated demonstration
agybar demo

# Try alternative bar styles (blocks, ascii, dots)
agybar demo --style ascii
agybar demo --style dots

# Check the current or latest Antigravity session status
agybar status

# Watch a live running Antigravity task in a separate terminal split
agybar watch
```

---

## 🧠 How It Works

```
┌─────────────────────────────────┐
│        User Request             │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     Planning Rule (AGENTS.md)   │
│  Agent outputs:                 │
│  <!-- agybar:plan {"total": 4} │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Antigravity Loop           │
│  PreToolUse / PostToolUse Hooks │
│  Updates state & calculates %   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│     Terminal /dev/tty Render    │
│  ⚡ AgyBar [██████░░] 60% (3/5)  │
└─────────────────────────────────┘
```

1. **Rule Protocol (`rules/AGENTS.md`)**: Injected into the model's instructions, requesting that multi-step tasks declare a step plan:
   ```html
   <!-- agybar:plan {"total": 4, "steps": ["Scan codebase", "Implement fix", "Run tests", "Commit"]} -->
   ```
2. **Lifecycle Hooks (`hooks.json`)**: Intercepts `PreToolUse`, `PostToolUse`, and `Stop` events.
3. **State Engine (`scripts/state.py`)**: Stores atomic session metrics in `/tmp/agybar/<conversation_id>.json`.
4. **Renderer (`scripts/renderer.py`)**: Draws clean progress indicators to the user's terminal without breaking tool stdout/stderr.

---

## 📁 Repository Structure

```text
.
├── bin/
│   └── agybar                 # CLI executable
├── hooks.json                 # Antigravity lifecycle hooks configuration
├── install.sh                 # One-line universal installer
├── plugin.json                # Antigravity plugin manifest
├── rules/
│   └── AGENTS.md              # Agent planning instructions
├── scripts/
│   ├── cli.py                 # CLI commands (status, watch, demo, install)
│   ├── hook_runner.py         # Hook event handler for Antigravity
│   ├── renderer.py            # Terminal bar formatting & ANSI colors
│   └── state.py               # Session state persistence & transcript parser
├── .gitignore
└── README.md
```

---

## 🤝 Contributing

Contributions and feedback are welcome! Feel free to submit issues or pull requests to enhance formatting, add desktop notifications, or improve IDE integrations.

## 📄 License

MIT License. Free to use and customize across all your projects.
