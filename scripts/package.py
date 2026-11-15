"""Build the distributable plugin archive (implemented in Milestone 3)."""

from __future__ import annotations

import sys


def main() -> int:
    """Refuse packaging until the Milestone 3 implementation is complete."""
    sys.stderr.write("Packaging is implemented in Milestone 3.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
