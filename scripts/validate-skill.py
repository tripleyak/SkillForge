#!/usr/bin/env python3
"""
validate-skill.py - Back-compat shim for validate_skill.py

The validator lives in validate_skill.py (importable module name). This shim
keeps the documented `python scripts/validate-skill.py <path>` command
working. It delegates to validate_skill.main(), which handles argparse CLI
parsing, exit codes, and the validation Result reporting.
"""

import sys
from pathlib import Path

try:
    from validate_skill import main
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_skill import main

if __name__ == "__main__":
    main()  # calls sys.exit() with the validation exit code
