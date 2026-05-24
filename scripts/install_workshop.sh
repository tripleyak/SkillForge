#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tripleyak/SkillForge.git"
LEVEL="balanced"
SCHEDULE=1
SOURCE_DIR=""

usage() {
  cat <<'EOF'
Install SkillForge for the AI for Ecommerce workshop.

Usage:
  bash scripts/install_workshop.sh [options]

Options:
  --level LEVEL     Proactivity level: off, quiet, balanced, active (default: balanced)
  --no-schedule    Do not install the local background advisor schedule
  --source PATH    Install from an existing SkillForge checkout instead of GitHub
  -h, --help       Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --level)
      LEVEL="${2:-}"
      shift 2
      ;;
    --no-schedule)
      SCHEDULE=0
      shift
      ;;
    --source)
      SOURCE_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$LEVEL" in
  off|quiet|balanced|active) ;;
  *)
    echo "Invalid proactivity level: $LEVEL" >&2
    echo "Use one of: off, quiet, balanced, active" >&2
    exit 1
    ;;
esac

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    echo "Install the prerequisites first, then rerun this installer." >&2
    exit 1
  fi
}

require_cmd git
require_cmd python3
require_cmd rsync

TMP_DIR=""
cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

if [[ -z "$SOURCE_DIR" ]]; then
  TMP_DIR="$(mktemp -d)"
  SOURCE_DIR="$TMP_DIR/SkillForge"
  echo "Downloading SkillForge..."
  git clone --depth 1 "$REPO_URL" "$SOURCE_DIR" >/dev/null
else
  SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
fi

if [[ ! -f "$SOURCE_DIR/SKILL.md" || ! -f "$SOURCE_DIR/.skillignore" ]]; then
  echo "Invalid SkillForge source directory: $SOURCE_DIR" >&2
  exit 1
fi

install_skill_copy() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  mkdir -p "$dest"
  rsync -a --delete --delete-excluded --exclude-from="$SOURCE_DIR/.skillignore" "$SOURCE_DIR/" "$dest/"
}

echo "Installing SkillForge skill copies..."
install_skill_copy "$HOME/.claude/skills/skillforge"
install_skill_copy "$HOME/.codex/skills/skillforge"
install_skill_copy "$HOME/.agents/skills/skillforge"

echo "Installing Claude Code /skillforge command..."
mkdir -p "$HOME/.claude/commands"
cp "$SOURCE_DIR/commands/skillforge.md" "$HOME/.claude/commands/skillforge.md"

echo "Configuring SkillForge proactivity level: $LEVEL"
codex_args=(--proactivity-level "$LEVEL" --write-agent-instructions "$HOME/AGENTS.md")
if [[ "$SCHEDULE" -eq 1 && "$LEVEL" != "off" ]]; then
  codex_args+=(--schedule)
fi
python3 "$HOME/.codex/skills/skillforge/scripts/install_skillforge.py" "${codex_args[@]}" >/dev/null

mkdir -p "$HOME/.claude"
python3 "$HOME/.claude/skills/skillforge/scripts/install_skillforge.py" \
  --proactivity-level "$LEVEL" \
  --write-agent-instructions "$HOME/.claude/CLAUDE.md" >/dev/null

if [[ "$SCHEDULE" -eq 1 && "$LEVEL" != "off" && "$(uname -s)" == "Darwin" ]]; then
  plist="$HOME/Library/LaunchAgents/com.skillforge.context-advisor.plist"
  if command -v launchctl >/dev/null 2>&1 && [[ -f "$plist" ]]; then
    launchctl unload "$plist" >/dev/null 2>&1 || true
    if launchctl load "$plist" >/dev/null 2>&1; then
      echo "Loaded SkillForge background advisor schedule."
    else
      echo "Wrote schedule but could not load it automatically. You can load it later with:"
      echo "  launchctl load $plist"
    fi
  fi
fi

echo "Verifying install..."
python3 "$HOME/.claude/skills/skillforge/scripts/quick_validate.py" "$HOME/.claude/skills/skillforge" >/dev/null
python3 "$HOME/.codex/skills/skillforge/scripts/quick_validate.py" "$HOME/.codex/skills/skillforge" >/dev/null
python3 "$HOME/.codex/skills/skillforge/scripts/context_advisor.py" \
  checkpoint \
  --cwd "$HOME" \
  --text "Verify SkillForge workshop install" \
  --json >/dev/null

cat <<EOF

SkillForge is installed and verified.

Installed for:
  Claude Code: ~/.claude/skills/skillforge
  Codex:       ~/.codex/skills/skillforge
  Shared:      ~/.agents/skills/skillforge

Claude Code command:
  /skillforge

Next step:
  Restart Claude Code and Codex so the new skill loads.
EOF
