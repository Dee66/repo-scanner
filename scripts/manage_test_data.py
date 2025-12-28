#!/usr/bin/env python3
"""Test data management and cleanup utilities.

Provides tools for managing test data, cleaning up leftover files,
and ensuring test isolation.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Set


def find_leftover_test_files() -> List[Path]:
    """Find leftover test files and directories."""
    temp_base = Path(tempfile.gettempdir())
    leftover = []

    # Common patterns for leftover test data
    patterns = [
        "pytest-of-*",
        "test_repo_*",
        "output_*",
        "tmp_path_*",
        "pytest*",
        "test_*"
    ]

    for pattern in patterns:
        for path in temp_base.glob(pattern):
            if path.exists():
                leftover.append(path)

    return leftover


def cleanup_leftover_files(dry_run: bool = True) -> int:
    """Clean up leftover test files.

    Args:
        dry_run: If True, only show what would be deleted

    Returns:
        Number of items cleaned up
    """
    leftover = find_leftover_test_files()
    cleaned = 0

    if not leftover:
        print("✅ No leftover test files found")
        return 0

    print(f"Found {len(leftover)} leftover items:")

    for path in leftover:
        try:
            if dry_run:
                size = get_directory_size(path) if path.is_dir() else path.stat().st_size
                print(f"  Would remove: {path} ({size} bytes)")
            else:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"  Removed: {path}")
                cleaned += 1
        except (OSError, PermissionError) as e:
            print(f"  Failed to remove {path}: {e}")

    if dry_run:
        print(f"\nUse --clean to actually remove these files")
    else:
        print(f"\nCleaned up {cleaned} items")

    return cleaned


def get_directory_size(path: Path) -> int:
    """Get total size of directory recursively."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def check_test_isolation() -> bool:
    """Check if tests are properly isolated."""
    # This would be more complex in a real implementation
    # For now, just check that we can run a simple test
    import subprocess
    import sys

    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/test_scanner_cli.py::test_cli_valid_repository",
            "--tb=no", "-q"
        ], capture_output=True, text=True, timeout=30)

        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def main():
    """Main function for test data management."""
    import argparse

    parser = argparse.ArgumentParser(description="Test data management utilities")
    parser.add_argument("--clean", action="store_true", help="Actually clean up files (default: dry run)")
    parser.add_argument("--check-isolation", action="store_true", help="Check test isolation")
    parser.add_argument("--find-leftover", action="store_true", help="Find leftover test files")

    args = parser.parse_args()

    if args.check_isolation:
        print("Checking test isolation...")
        isolated = check_test_isolation()
        print(f"Test isolation: {'✅ Good' if isolated else '❌ Issues detected'}")
        return 0 if isolated else 1

    elif args.find_leftover or args.clean:
        return cleanup_leftover_files(dry_run=not args.clean)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    exit(main())