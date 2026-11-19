#!/usr/bin/env bash
# ==============================================================================
# AgyBar Universal Installer
# Real-time progress bar & planning tracker for Gemini Antigravity (agy)
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
  echo -e " ${BOLD}Real-Time Progress Bar for Gemini Antigravity (agy)${RESET}"
  echo " ------------------------------------------------------------"
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
        echo -e "${YELLOW}Warning: No project path specified with -p. Using current directory: $(pwd)${RESET}"
        PROJECT_PATH="$(pwd)"
      fi
      shift 2 || shift
      ;;
    --help|-h)
      echo "Usage: ./install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --global, -g           Install globally to ~/.gemini/config/plugins/agybar/ (Default)"
      echo "  --project, -p <PATH>   Install locally to <PATH>/.agents/plugins/agybar/"
      echo "  --help, -h             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ "$TARGET_MODE" == "global" ]]; then
  DEST_DIR="$HOME/.gemini/config/plugins/agybar"
  echo -e "${CYAN}Target Mode:${RESET} Global (~/.gemini/config/plugins/agybar/)"
else
  PROJECT_PATH="$(cd "$PROJECT_PATH" && pwd)"
  DEST_DIR="$PROJECT_PATH/.agents/plugins/agybar"
  echo -e "${CYAN}Target Mode:${RESET} Project-Local ($DEST_DIR)"
fi

echo -e "${DIM}Copying plugin files...${RESET}"
mkdir -p "$DEST_DIR"

# Copy core components
cp "$SCRIPT_DIR/plugin.json" "$DEST_DIR/"
cp "$SCRIPT_DIR/hooks.json" "$DEST_DIR/"

mkdir -p "$DEST_DIR/rules"
cp -R "$SCRIPT_DIR/rules/"* "$DEST_DIR/rules/"

mkdir -p "$DEST_DIR/scripts"
cp -R "$SCRIPT_DIR/scripts/"* "$DEST_DIR/scripts/"
chmod +x "$DEST_DIR/scripts/"*.py

# Optional: Link CLI binary to user PATH if ~/.local/bin exists
if [[ -d "$HOME/.local/bin" ]]; then
  ln -sf "$SCRIPT_DIR/bin/agybar" "$HOME/.local/bin/agybar"
  echo -e "${DIM}Linked 'agybar' CLI to ~/.local/bin/agybar${RESET}"
fi

echo ""
echo -e "${GREEN}${BOLD}✔ AgyBar installation complete!${RESET}"
echo ""
echo "What happens next:"
echo "1. Whenever you run an 'agy' session, AgyBar's lifecycle hooks will monitor tool execution."
echo "2. The agent will formulate a plan first and advance through each milestone."
echo "3. You'll see real-time progress bars rendered directly in your terminal!"
echo ""
echo -e "Try running a demo right now:  ${BOLD}./bin/agybar demo${RESET}"
echo -e "Check active session status:   ${BOLD}./bin/agybar status${RESET}"
echo -e "Live terminal monitor:         ${BOLD}./bin/agybar watch${RESET}"
echo ""
