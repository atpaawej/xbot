#!/usr/bin/env python3
"""Build script for compiling xbot into a standalone single-binary executable."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build standalone xbot binary using PyInstaller")
    parser.add_argument("--clean", action="store_true", help="Clean build and dist directories before compiling")
    parser.add_argument("--no-test", action="store_true", help="Skip binary smoke test after build")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    spec_file = repo_root / "packaging" / "xbot.spec"
    if not spec_file.is_file():
        print(f"Error: Spec file not found at {spec_file}", file=sys.stderr)
        sys.exit(1)

    if args.clean:
        print("Cleaning previous build artifacts...")
        shutil.rmtree(repo_root / "build", ignore_errors=True)
        shutil.rmtree(repo_root / "dist", ignore_errors=True)

    print("Building xbot standalone binary with PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(spec_file),
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Error: PyInstaller build failed.", file=sys.stderr)
        sys.exit(result.returncode)

    ext = ".exe" if sys.platform.startswith("win") else ""
    binary_path = repo_root / "dist" / f"xbot{ext}"

    if not binary_path.is_file():
        print(f"Error: Expected binary not found at {binary_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure executable permissions on Unix systems
    if not sys.platform.startswith("win"):
        binary_path.chmod(binary_path.stat().st_mode | 0o755)

    size_mb = binary_path.stat().st_size / (1024 * 1024)
    print(f"\nSuccessfully built binary: {binary_path} ({size_mb:.2f} MB)")

    if not args.no_test:
        print("\nRunning smoke test (xbot --version)...")
        test_run = subprocess.run([str(binary_path), "--version"], capture_output=True, text=True)
        print(f"Exit code: {test_run.returncode}")
        print(f"Output: {test_run.stdout.strip() or test_run.stderr.strip()}")
        if test_run.returncode != 0:
            print("Warning: Smoke test returned non-zero exit code!", file=sys.stderr)
            sys.exit(test_run.returncode)
        print("Smoke test passed successfully!")


if __name__ == "__main__":
    main()
