#!/usr/bin/env python3
"""Install the playbook using a guided, automatically reused profile."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Sequence


TOOLS_DIR = Path(__file__).resolve().parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

# Keep the public entrypoint policy-free and its CLI small. Profile reuse,
# required datasets, and update safety live in the installer implementation.
from install_skills import main as installer_main  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    return installer_main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
