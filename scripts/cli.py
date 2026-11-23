#!/usr/bin/env python3
"""CLI utility for AgyBar - Installation, inspection, and live monitoring."""

import argparse
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

# Module lookup
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from renderer import ProgressBarRenderer, BOLD, CYAN, GREEN, MAGENTA, RESET, YELLOW
from state import STATE_DIR, SessionState


def get_latest_session_file() -> Path | None:
    if not STATE_DIR.exists():
        return None
    files = list(STATE_DIR.glob("*.json"))
    if not files:
        return None
    # Sort by modification time descending
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def cmd_status(args: argparse.Namespace) -> None:
    session_file = Path(args.session) if args.session else get_latest_session_file()
    if not session_file or not session_file.exists():
        print(f"{YELLOW}No active AgyBar session found in {STATE_DIR}{RESET}")
        return

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading session file: {e}")
        return

    renderer = ProgressBarRenderer()
    print(f"\n{BOLD}Active Session:{RESET} {data.get('conversation_id', 'unknown')}")
    print(renderer.format_line(data))
    print(f"\n{BOLD}Plan Steps:{RESET}")
    steps = data.get("plan_steps", [])
    current = data.get("current_step", 1)
    if steps:
        for idx, step in enumerate(steps, 1):
            mark = f"{GREEN}✔{RESET}" if idx < current else (f"{CYAN}➜{RESET}" if idx == current else "○")
            print(f"  {mark} Step {idx}: {step}")
    else:
        print(f"  {YELLOW}(Adaptive tracking active - no static plan declared){RESET}")

    tools = data.get("tool_history", [])
    if tools:
        print(f"\n{BOLD}Recent Tool Actions:{RESET}")
        for t in tools[-5:]:
            print(f"  • [{t.get('tool')}] {t.get('action')}")
    print()


def cmd_watch(args: argparse.Namespace) -> None:
    session_file = Path(args.session) if args.session else get_latest_session_file()
    if not session_file or not session_file.exists():
        print(f"{YELLOW}Waiting for an AgyBar session in {STATE_DIR}... (Ctrl+C to stop){RESET}")
        while not session_file or not session_file.exists():
            time.sleep(1)
            session_file = get_latest_session_file()

    renderer = ProgressBarRenderer()
    print(f"{CYAN}Watching session:{RESET} {session_file.stem} (Ctrl+C to exit)\n")

    last_mtime = 0.0
    try:
        while True:
            if session_file.exists():
                mtime = session_file.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    try:
                        with open(session_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        renderer.render(data, newline=False)
                        if data.get("status") == "completed":
                            print(f"\n{GREEN}✔ Task finished!{RESET}")
                            break
                    except Exception:
                        pass
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n{DIM}Watch stopped.{RESET}")


def cmd_demo(args: argparse.Namespace) -> None:
    print(f"\n{MAGENTA}{BOLD}Running AgyBar Demonstration...{RESET}\n")
    demo_session_id = "demo-session"
    state = SessionState(demo_session_id)
    renderer = ProgressBarRenderer(style=args.style)

    steps = [
        ("Planning task & reading repo structure", "read_file", {"Path": "src/main.py"}),
        ("Drafting feature implementation", "edit_file", {"Path": "src/main.py"}),
        ("Running unit test suite", "run_command", {"CommandLine": "pytest tests/ -v"}),
        ("Refining documentation and README", "write_file", {"Path": "README.md"}),
        ("Committing changes and finishing", "run_command", {"CommandLine": "git commit -m 'feat: progress bar'"}),
    ]

    state.data["total_steps"] = len(steps)
    state.data["plan_steps"] = [s[0] for s in steps]
    state.data["plan_detected"] = True
    state.data["start_time"] = time.time()
    state.save()

    for idx, (title, tool, tool_args) in enumerate(steps, 1):
        state.data["current_step"] = idx
        state.data["step_name"] = title
        state.record_tool_call(tool, tool_args, step_idx=idx)
        renderer.render(state.data, newline=False)
        time.sleep(1.2)

    state.mark_completed()
    renderer.render(state.data, newline=True)
    print(f"\n{GREEN}{BOLD}Demonstration complete!{RESET}\n")


def cmd_install(args: argparse.Namespace) -> None:
    targets = []
    target_cli = getattr(args, "cli", "all")

    if args.global_install:
        if target_cli in ("all", "agy"):
            targets.append(("Antigravity", Path.home() / ".gemini" / "config" / "plugins" / "agybar"))
        if target_cli in ("all", "claude"):
            targets.append(("Claude Code", Path.home() / ".claude" / "plugins" / "agybar"))
    else:
        project_root = Path(args.project).resolve() if args.project else Path.cwd()
        if target_cli in ("all", "agy"):
            targets.append(("Antigravity", project_root / ".agents" / "plugins" / "agybar"))
        if target_cli in ("all", "claude"):
            targets.append(("Claude Code", project_root / ".claude-plugins" / "agybar"))

    items_to_copy = ["plugin.json", "hooks.json", "rules", "scripts"]

    for name, target_dir in targets:
        print(f"{CYAN}Installing AgyBar for {name}:{RESET} {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in items_to_copy:
            src = ROOT_DIR / item
            dst = target_dir / item
            if not src.exists():
                continue
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        for py_file in (target_dir / "scripts").glob("*.py"):
            py_file.chmod(0o755)
        print(f"{GREEN}✔ Successfully installed for {name}!{RESET}")

    print(f"\n{DIM}AI agents will automatically load AgyBar for sessions in scope.{RESET}\n")


def cmd_uninstall(args: argparse.Namespace) -> None:
    if args.global_install:
        target_dir = Path.home() / ".gemini" / "config" / "plugins" / "agybar"
    else:
        project_root = Path(args.project).resolve() if args.project else Path.cwd()
        target_dir = project_root / ".agents" / "plugins" / "agybar"

    if target_dir.exists():
        shutil.rmtree(target_dir)
        print(f"{GREEN}✔ Successfully uninstalled AgyBar from {target_dir}{RESET}")
    else:
        print(f"{YELLOW}AgyBar was not found at {target_dir}{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AgyBar - Progress Bar for Gemini Antigravity")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", help="Show current or latest session status")
    p_status.add_argument("--session", "-s", help="Specific session file or ID")

    # watch
    p_watch = subparsers.add_parser("watch", help="Watch progress live in terminal")
    p_watch.add_argument("--session", "-s", help="Specific session file or ID")

    # demo
    p_demo = subparsers.add_parser("demo", help="Run animated progress bar demo")
    p_demo.add_argument("--style", choices=["blocks", "ascii", "dots"], default="blocks", help="Bar style")

    # install
    p_install = subparsers.add_parser("install", help="Install AgyBar plugin")
    p_install.add_argument("--global", dest="global_install", action="store_true", help="Install globally")
    p_install.add_argument("--project", "-p", help="Target project root directory")
    p_install.add_argument("--cli", "-c", choices=["all", "agy", "claude"], default="all", help="Target AI CLI")

    # uninstall
    p_uninstall = subparsers.add_parser("uninstall", help="Uninstall AgyBar plugin")
    p_uninstall.add_argument("--global", dest="global_install", action="store_true", help="Uninstall globally")
    p_uninstall.add_argument("--project", "-p", help="Target project root directory")
    p_uninstall.add_argument("--cli", "-c", choices=["all", "agy", "claude"], default="all", help="Target AI CLI")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
