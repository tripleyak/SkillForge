#!/usr/bin/env python3
"""
package_skill.py - Creates a distributable .skill file

Validates a skill using quick_validate.py, then packages it into a .skill
file (zip format) for distribution.

Usage:
    python package_skill.py <path/to/skill-folder> [output-directory]

Example:
    python package_skill.py ~/.claude/skills/my-skill
    python package_skill.py ~/.claude/skills/my-skill ./dist
"""

import sys
import zipfile
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PackageResult:
    """Result of packaging a skill."""
    success: bool
    message: str
    output_path: Optional[Path] = None


def load_skillignore(skill_path: Path) -> list[str]:
    """Load .skillignore patterns from a skill directory."""
    ignore_file = skill_path / ".skillignore"
    if not ignore_file.exists():
        return []

    patterns: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def is_ignored(file_path: Path, skill_path: Path, patterns: list[str]) -> bool:
    """Check whether a file should be excluded by .skillignore."""
    rel_path = str(file_path.relative_to(skill_path))
    name = file_path.name

    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Handle directory-style patterns like "assets/images"
        if rel_path.startswith(pattern + "/") or rel_path == pattern:
            return True
    return False

# Import validation from quick_validate
try:
    from quick_validate import validate_skill
except ImportError:
    # If running from different directory, try relative import
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from quick_validate import validate_skill


def package_skill(skill_path, output_dir=None) -> PackageResult:
    """
    Package a skill folder into a .skill file.

    Args:
        skill_path: Path to the skill folder
        output_dir: Optional output directory for the .skill file (defaults to current directory)

    Returns:
        PackageResult with success status, message, and output path
    """
    skill_path = Path(skill_path).resolve()

    # Validate skill folder exists
    if not skill_path.exists():
        return PackageResult(False, f"Skill folder not found: {skill_path}")

    if not skill_path.is_dir():
        return PackageResult(False, f"Path is not a directory: {skill_path}")

    # Validate SKILL.md exists
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return PackageResult(False, f"SKILL.md not found in {skill_path}")

    # Run validation before packaging
    print("🔍 Validating skill...")
    valid, message = validate_skill(skill_path)
    if not valid:
        return PackageResult(False, f"Validation failed: {message}")
    print(f"✅ {message}\n")

    # Determine output location
    skill_name = skill_path.name
    if output_dir:
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd()

    skill_filename = output_path / f"{skill_name}.skill"
    ignore_patterns = load_skillignore(skill_path)

    # Create the .skill file (zip format)
    try:
        with zipfile.ZipFile(skill_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the skill directory
            for file_path in skill_path.rglob('*'):
                if file_path.is_file():
                    # Skip common exclusions
                    if file_path.name.startswith('.') or '__pycache__' in str(file_path):
                        continue
                    # Apply explicit .skillignore patterns
                    if is_ignored(file_path, skill_path, ignore_patterns):
                        continue
                    # Calculate the relative path within the zip
                    arcname = file_path.relative_to(skill_path.parent)
                    zipf.write(file_path, arcname)
                    print(f"  Added: {arcname}")

        return PackageResult(True, f"Successfully packaged skill to: {skill_filename}", skill_filename)

    except Exception as e:
        return PackageResult(False, f"Error creating .skill file: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python package_skill.py <path/to/skill-folder> [output-directory]")
        print("\nExample:")
        print("  python package_skill.py ~/.claude/skills/my-skill")
        print("  python package_skill.py ~/.claude/skills/my-skill ./dist")
        sys.exit(1)

    skill_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"📦 Packaging skill: {skill_path}")
    if output_dir:
        print(f"   Output directory: {output_dir}")
    print()

    result = package_skill(skill_path, output_dir)

    if result.success:
        print(f"\n✅ {result.message}")
        sys.exit(0)
    else:
        print(f"❌ {result.message}")
        print("   Please fix the errors before packaging.")
        sys.exit(1)


if __name__ == "__main__":
    main()
