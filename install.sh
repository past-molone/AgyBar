#!/usr/bin/env bash
# ==============================================================================
# AgyBar Universal Multi-CLI Installer
# Real-time progress bar & planning tracker for Gemini Antigravity (agy)
# and Claude Code (claude).
# ==============================================================================

set -euo pipefail

# ANSI Colors
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_MODE="global"
TARGET_CLI="all"
PROJECT_PATH=""

print_banner() {
  echo -e "${CYAN}${BOLD}"
  echo "  █████╗  ██████╗ ██╗   ██╗██████╗  █████╗ ██████╗ "
  echo " ██╔══██╗██╔════╝ ╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗"
  echo " ███████║██║  ███╗ ╚████╔╝ ██████╔╝███████║██████╔╝"
  echo " ██╔══██║██║   ██║  ╚██╔╝  ██╔══██╗██╔══██║██╔══██╗"
  echo " ██║  ██║╚██████╔╝   ██║   ██████╔╝██║  ██║██║  ██║"
  echo " ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
  echo -e "${RESET}"
  echo -e " ${BOLD}Real-Time Progress Bar for Gemini Antigravity & Claude Code${RESET}"
  echo " ------------------------------------------------------------------"
}

print_banner

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --global|-g)
      TARGET_MODE="global"
      shift
      ;;
    --project|-p)
      TARGET_MODE="project"
      PROJECT_PATH="${2:-}"
      if [[ -z "$PROJECT_PATH" ]]; then
        PROJECT_PATH="$(pwd)"
      fi
      shift 2 || shift
      ;;
    --cli|-c)
      TARGET_CLI="${2:-all}"
      shift 2 || shift
      ;;
    --help|-h)
      echo "Usage: ./install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --global, -g           Install globally (Default)"
      echo "  --project, -p <PATH>   Install locally to project repository"
      echo "  --cli, -c <CLI>        Target AI CLI: agy, claude, or all (Default: all)"
      echo "  --help, -h             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

copy_plugin_payload() {
  local dest="$1"
  mkdir -p "$dest"
  cp "$SCRIPT_DIR/plugin.json" "$dest/"
  cp "$SCRIPT_DIR/hooks.json" "$dest/"
  
  mkdir -p "$dest/rules"
  cp -R "$SCRIPT_DIR/rules/"* "$dest/rules/"

  mkdir -p "$dest/scripts"
  cp -R "$SCRIPT_DIR/scripts/"* "$dest/scripts/"
  chmod +x "$dest/scripts/"*.py
}

installed_targets=()

# 1. Antigravity (agy)
if [[ "$TARGET_CLI" == "all" || "$TARGET_CLI" == "agy" ]]; then
  if [[ "$TARGET_MODE" == "global" ]]; then
    DEST_DIR="$HOME/.gemini/config/plugins/agybar"
  else
    PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
    DEST_DIR="$PROJECT_PATH/.agents/plugins/agybar"
  fi
  copy_plugin_payload "$DEST_DIR"
  installed_targets+=("Gemini Antigravity ($DEST_DIR)")
fi

# 2. Claude Code (claude)
if [[ "$TARGET_CLI" == "all" || "$TARGET_CLI" == "claude" ]]; then
  if [[ "$TARGET_MODE" == "global" ]]; then
    DEST_DIR="$HOME/.claude/plugins/agybar"
  else
    PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
    DEST_DIR="$PROJECT_PATH/.claude-plugins/agybar"
    # Also drop CLAUDE.md rule if not already present
    if [[ ! -f "$PROJECT_PATH/CLAUDE.md" ]]; then
      cp "$SCRIPT_DIR/rules/CLAUDE.md" "$PROJECT_PATH/CLAUDE.md"
    fi
  fi
  copy_plugin_payload "$DEST_DIR"
  installed_targets+=("Claude Code ($DEST_DIR)")
fi

# Link CLI binary to user PATH if ~/.local/bin exists
if [[ -d "$HOME/.local/bin" ]]; then
  ln -sf "$SCRIPT_DIR/bin/agybar" "$HOME/.local/bin/agybar"
  echo -e "${DIM}Linked 'agybar' CLI to ~/.local/bin/agybar${RESET}"
fi

configure_statusline() {
  local cli_target="$1"

  # Claude Code statusLine in ~/.claude/settings.json
  if [[ "$cli_target" == "all" || "$cli_target" == "claude" ]]; then
    local claude_settings="$HOME/.claude/settings.json"
    if [[ -f "$claude_settings" ]]; then
      python3 -c "
import json
from pathlib import Path

p = Path('$claude_settings')
try:
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    prev = data.get('statusLine', {})
    prev_cmd = prev.get('command', '') if isinstance(prev, dict) else ''
    if prev_cmd and 'agybar' not in prev_cmd:
        agy_conf_path = Path.home() / '.agybar.json'
        conf = {}
        if agy_conf_path.exists():
            try:
                with open(agy_conf_path) as cf:
                    conf = json.load(cf)
            except Exception:
                pass
        conf['chain_command'] = prev_cmd
        with open(agy_conf_path, 'w', encoding='utf-8') as cf:
            json.dump(conf, cf, indent=2)

    data['statusLine'] = {
        'type': 'command',
        'command': 'agybar statusline',
        'padding': 0,
        'refreshInterval': 2
    }
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print('  • Configured Claude Code native statusLine in ~/.claude/settings.json')
except Exception as e:
    print('  • Notice: Could not configure Claude Code statusLine:', e)
"
    fi
  fi

  # Antigravity CLI statusLine in ~/.gemini/antigravity-cli/settings.json
  if [[ "$cli_target" == "all" || "$cli_target" == "agy" ]]; then
    local agy_settings="$HOME/.gemini/antigravity-cli/settings.json"
    python3 -c "
import json
from pathlib import Path

p = Path('$agy_settings')
try:
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data['statusLine'] = {
        'command': 'agybar statusline'
    }
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print('  • Configured Gemini Antigravity native statusLine in ~/.gemini/antigravity-cli/settings.json')
except Exception as e:
    print('  • Notice: Could not configure Antigravity statusLine:', e)
"
  fi
}

echo ""
echo -e "${BOLD}Configuring native terminal statusLine integration...${RESET}"
configure_statusline "$TARGET_CLI"

echo ""
echo -e "${GREEN}${BOLD}✔ AgyBar installation complete!${RESET}"
echo ""
echo "Installed targets:"
for target in "${installed_targets[@]}"; do
  echo -e "  • ${CYAN}$target${RESET}"
done
echo ""
echo "Key highlights:"
echo "1. If your agent or any existing skill/plugin already creates a plan (TODO.md, /plan, markdown checklists),"
echo "   AgyBar automatically adopts and tracks that existing plan without forcing a new format!"
echo "2. Tool operations and tasks are tracked with real-time terminal progress telemetry."
echo ""
echo -e "Try running a demo right now:  ${BOLD}./bin/agybar demo${RESET}"
echo -e "Check active session status:   ${BOLD}./bin/agybar status${RESET}"
echo -e "Live terminal monitor:         ${BOLD}./bin/agybar watch${RESET}"
echo ""
