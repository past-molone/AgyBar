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


def cmd_config(args: argparse.Namespace) -> None:
    conf_path = Path.home() / ".agybar.json"
    conf = {}
    if conf_path.exists():
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
        except Exception:
            pass

    changed = False
    if getattr(args, "style", None):
        conf["style"] = args.style
        changed = True
    if getattr(args, "theme", None):
        conf["theme"] = args.theme
        changed = True
    if getattr(args, "width", None):
        conf["width"] = args.width
        changed = True
    if getattr(args, "badge_name", None):
        conf["badge_name"] = args.badge_name
        changed = True
    if getattr(args, "badge_symbol", None):
        conf["badge_symbol"] = args.badge_symbol
        changed = True
    if getattr(args, "badge_style", None):
        conf["badge_style"] = args.badge_style
        changed = True

    if changed:
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump(conf, f, indent=2)
        print(f"{GREEN}✔ Saved configuration to ~/.agybar.json{RESET}")

    r = ProgressBarRenderer()
    print(f"\n{BOLD}Active AgyBar Configuration:{RESET}")
    print(f"  • Theme:        {r.theme}")
    print(f"  • Style:        {r.style}")
    print(f"  • Width:        {r.width} chars")
    print(f"  • Badge Name:   {r.badge_name}")
    print(f"  • Badge Symbol: {r.badge_symbol}")
    print(f"  • Badge Style:  {r.badge_style}")
    print(f"\n{BOLD}Live Preview:{RESET}")
    mock_state = {"current_step": 3, "total_steps": 5, "step_name": "Running test suite", "status": "running"}
    print(f"  {r.format_line(mock_state)}\n")


def cmd_demo(args: argparse.Namespace) -> None:
    print(f"\n{MAGENTA}{BOLD}Running AgyBar Demonstration (Smooth Pink + Violet Progress)...{RESET}\n")
    demo_session_id = "demo-session"
    state = SessionState(demo_session_id)
    renderer = ProgressBarRenderer(style=args.style, theme=args.theme)

    steps = [
        ("Initial repo scan • 3 modified files detected", "read_file", {"Path": "src/main.py"}, 18.5),
        ("Patched 2/4 functions • ast parser verified", "edit_file", {"Path": "src/main.py"}, 42.0),
        ("12/12 unit tests passing • regression clean", "run_command", {"CommandLine": "pytest tests/ -v"}, 67.5),
        ("Docs & changelog drafted • typechecks clean", "write_file", {"Path": "README.md"}, 86.0),
        ("Final verification • commit prepped", "run_command", {"CommandLine": "git commit -m 'feat: progress bar'"}, 97.5),
    ]

    state.data["status"] = "running"
    state.data["total_steps"] = len(steps)
    state.data["plan_steps"] = [s[0] for s in steps]
    state.data["plan_detected"] = True
    state.data["start_time"] = time.time()
    state.save()

    for idx, (title, tool, tool_args, granular_pct) in enumerate(steps, 1):
        state.data["current_step"] = idx
        state.data["granular_pct"] = granular_pct
        state.data["step_name"] = title
        state.data["subagent_source"] = "Radar"
        state.data["subagent_action"] = title
        state.record_tool_call(tool, tool_args, step_idx=idx)
        renderer.render(state.data, newline=False)
        time.sleep(1.2)

    state.mark_completed()
    state.data["granular_pct"] = 100.0
    state.data["subagent_action"] = "All steps verified by subagent • Build clean"
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


def cmd_preview(args: argparse.Namespace) -> None:
    html_file = ROOT_DIR / "preview" / "index.html"
    print(f"\n{CYAN}{BOLD}AgyBar Interactive Designer & Terminal Visualizer{RESET}")
    print(f"Open this file in your browser to interactively customize your progress bar:")
    print(f"  {BOLD}file://{html_file}{RESET}\n")
    try:
        import subprocess
        if sys.platform == "darwin":
            subprocess.run(["open", str(html_file)], check=False)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(html_file)], check=False)
    except Exception:
        pass


def cmd_test(args: argparse.Namespace) -> None:
    print(f"\n{CYAN}{BOLD}Running AgyBar Integration & Unit Tests...{RESET}\n")
    test_file = ROOT_DIR / "tests" / "test_engine.py"
    import subprocess
    res = subprocess.run([sys.executable, str(test_file)], check=False)
    if res.returncode == 0:
        print(f"\n{GREEN}{BOLD}✔ All AgyBar tests passed!{RESET}\n")
    else:
        print(f"\n{YELLOW}{BOLD}✖ Tests failed (exit code {res.returncode}){RESET}\n")
        sys.exit(res.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgyBar - Progress Bar for Gemini Antigravity & Claude Code")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # preview
    p_preview = subparsers.add_parser("preview", help="Open the interactive design studio in your browser")

    # status
    p_status = subparsers.add_parser("status", help="Show current or latest session status")
    p_status.add_argument("--session", "-s", help="Specific session file or ID")

    # watch
    p_watch = subparsers.add_parser("watch", help="Watch progress live in terminal")
    p_watch.add_argument("--session", "-s", help="Specific session file or ID")

    # demo
    p_demo = subparsers.add_parser("demo", help="Run animated progress bar demo")
    p_demo.add_argument("--style", choices=["smooth", "blocks", "ascii", "dots"], default="smooth", help="Bar style")
    p_demo.add_argument("--theme", choices=["pink", "cyan", "green", "purple", "amber"], default="pink", help="Color theme")

    # config
    p_config = subparsers.add_parser("config", help="View or modify active bar configuration")
    p_config.add_argument("--style", choices=["smooth", "blocks", "ascii", "dots"], help="Bar graphic style")
    p_config.add_argument("--theme", choices=["pink", "cyan", "green", "purple", "amber"], help="Color theme")
    p_config.add_argument("--width", type=int, help="Bar width in characters")
    p_config.add_argument("--badge-name", help="Badge text label (e.g. AgyBar, agy)")
    p_config.add_argument("--badge-symbol", help="Badge icon symbol (e.g. ⚡, ◆, 🚀, ✦, 🌸)")
    p_config.add_argument("--badge-style", choices=["default", "pill", "bracket", "minimal"], help="Badge visual style")

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

    # test
    p_test = subparsers.add_parser("test", help="Run automated integration tests")

    args = parser.parse_args()

    if args.command == "test":
        cmd_test(args)
    elif args.command == "preview":
        cmd_preview(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "status":
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
