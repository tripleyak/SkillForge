#!/usr/bin/env bash
set -euo pipefail

# Workshop installer for SkillForge.
#
# Safe by design:
#   - never loads launchd agents (the advisor is delivered via Claude Code
#     hooks, registered separately and only with explicit consent)
#   - never appends to ~/.claude/CLAUDE.md or ~/AGENTS.md
#   - never enables Personal Context scanning
#   - prompts before overwriting an existing install (--force skips)
#   - prints a post-install summary of exactly what was touched
#
# Works non-interactively when piped (curl | bash): defaults to safe choices,
# meaning no hooks, no personal context, and no overwrite of an existing
# install unless --force is passed.

REPO_URL="https://github.com/tripleyak/SkillForge.git"
LEVEL="balanced"
SOURCE_DIR=""
FORCE=0

usage() {
  cat <<'EOF'
Install SkillForge for the AI for Ecommerce workshop.

Usage:
  bash scripts/install_workshop.sh [options]

Options:
  --level LEVEL    Proactivity level: off, quiet, balanced, active (default: balanced)
  --source PATH    Install from an existing SkillForge checkout instead of GitHub
  --force          Overwrite an existing install without prompting
  -h, --help       Show this help

This installer does NOT register Claude Code hooks and does NOT enable
Personal Context scanning. To opt in to either, run afterwards:
  python3 ~/.claude/skills/skillforge/scripts/install_skillforge.py
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --level)
      LEVEL="${2:-}"
      shift 2
      ;;
    --source)
      SOURCE_DIR="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --no-schedule)
      # Deprecated: there is no background schedule anymore.
      echo "Note: --no-schedule is deprecated and has no effect (no schedule is ever installed)." >&2
      shift
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

INTERACTIVE=0
if [[ -t 0 ]]; then
  INTERACTIVE=1
fi

TOUCHED=()

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

confirm_overwrite() {
  local dest="$1"
  if [[ ! -e "$dest" ]]; then
    return 0
  fi
  if [[ "$FORCE" -eq 1 ]]; then
    return 0
  fi
  if [[ "$INTERACTIVE" -eq 1 ]]; then
    local answer
    read -r -p "Existing install found at $dest. Overwrite it? [y/N] " answer
    case "$answer" in
      y|Y|yes|YES) return 0 ;;
      *) return 1 ;;
    esac
  fi
  echo "Existing install found at $dest. Rerun with --force to overwrite it (non-interactive run)." >&2
  return 1
}

install_skill_copy() {
  local dest="$1"
  if ! confirm_overwrite "$dest"; then
    echo "Skipped $dest (existing install kept)."
    TOUCHED+=("Skipped (kept existing): $dest")
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  mkdir -p "$dest"
  rsync -a --delete --delete-excluded --exclude-from="$SOURCE_DIR/.skillignore" "$SOURCE_DIR/" "$dest/"
  TOUCHED+=("Installed skill copy: $dest")
}

echo "Installing SkillForge skill copies..."
install_skill_copy "$HOME/.claude/skills/skillforge"
install_skill_copy "$HOME/.codex/skills/skillforge"
install_skill_copy "$HOME/.agents/skills/skillforge"

if [[ ! -f "$HOME/.claude/skills/skillforge/SKILL.md" ]]; then
  echo "No usable Claude Code install present; aborting configuration." >&2
  exit 1
fi

echo "Installing Claude Code /skillforge command..."
if confirm_overwrite "$HOME/.claude/commands/skillforge.md"; then
  mkdir -p "$HOME/.claude/commands"
  cp "$SOURCE_DIR/commands/skillforge.md" "$HOME/.claude/commands/skillforge.md"
  TOUCHED+=("Installed command: $HOME/.claude/commands/skillforge.md")
else
  TOUCHED+=("Skipped (kept existing): $HOME/.claude/commands/skillforge.md")
fi

echo "Configuring SkillForge proactivity level: $LEVEL"
# Safe choices: no hooks, no personal context, no agent-file writes.
python3 "$HOME/.claude/skills/skillforge/scripts/install_skillforge.py" \
  --non-interactive \
  --no-hooks \
  --proactivity-level "$LEVEL" >/dev/null
TOUCHED+=("Wrote advisor config (level: $LEVEL): $HOME/.config/skillforge/config.json")
TOUCHED+=("Removed any obsolete SkillForge launchd agents (if present)")

echo "Verifying install..."
python3 "$HOME/.claude/skills/skillforge/scripts/quick_validate.py" "$HOME/.claude/skills/skillforge" >/dev/null
if [[ -f "$HOME/.codex/skills/skillforge/SKILL.md" ]]; then
  python3 "$HOME/.codex/skills/skillforge/scripts/quick_validate.py" "$HOME/.codex/skills/skillforge" >/dev/null
fi
python3 "$HOME/.claude/skills/skillforge/scripts/context_advisor.py" \
  checkpoint \
  --cwd "$HOME" \
  --text "Verify SkillForge workshop install" \
  --json >/dev/null

cat <<EOF

SkillForge is installed and verified.

What this installer touched:
EOF
for line in "${TOUCHED[@]}"; do
  echo "  - $line"
done

cat <<EOF

What it did NOT touch (all opt-in):
  - Claude Code hooks (register with: python3 ~/.claude/skills/skillforge/scripts/install_skillforge.py)
  - Personal Context scanning (same installer, or --personal-paths/--github-owners)
  - ~/.claude/CLAUDE.md, ~/AGENTS.md, launchd agents (none installed)

Claude Code command:
  /skillforge

Next step:
  Restart Claude Code and Codex so the new skill loads.
EOF
