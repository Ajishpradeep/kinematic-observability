"""Validate publication paths in the Git index and selected branch history."""

import argparse
import shutil
import subprocess
from pathlib import Path, PurePosixPath

ROOT_FILES = {
    ".gitignore",
    ".gitattributes",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CITATION.cff",
    "pyproject.toml",
    "requirements.txt",
    "MANIFEST.in",
}
HISTORICAL_ROOT_FILES = {
    "ADDENDUM.md",
    "NOTE.md",
    "PROTOCOL.md",
    "RELATED_WORK.md",
    "geometry.py",
    "oracle_control.py",
    "prepare_local.py",
    "report.py",
    "run.py",
    "test_geometry.py",
    "verify_release.py",
}

PUBLIC_DIRECTORIES = {
    "observability",
    "src",
    "tests",
    "reports",
    "results",
    "provenance",
    "scripts",
    ".github",
}
BINARY_SUFFIXES = {
    ".npz",
    ".pt",
    ".pth",
    ".ckpt",
    ".avi",
    ".mp4",
    ".mov",
    ".c3d",
    ".tak",
    ".mcal",
}


def git(*args):
    return subprocess.check_output(["git", *args])


def check_paths(paths, historical=False):
    for name in paths:
        path = PurePosixPath(name)
        directories = (
            PUBLIC_DIRECTORIES
            if historical
            else {"src", "tests", "reports", "results", ".github"}
        )
        allowed_files = ROOT_FILES | HISTORICAL_ROOT_FILES if historical else ROOT_FILES
        if name not in allowed_files and path.parts[0] not in directories:
            raise ValueError(f"Path outside publication structure: {name}")
        if path.suffix.lower() in BINARY_SUFFIXES or path.name.startswith(
            ("identity-map.", "participant-map.")
        ):
            raise ValueError(f"Restricted artifact: {name}")
        if (
            not historical
            and path.suffix.lower() in {".png", ".svg"}
            and not name.startswith("reports/figures/")
        ):
            raise ValueError(f"Figure outside reports/figures: {name}")


HOOKS = {
    "pre-commit": '#!/bin/sh\nset -eu\npython3 "$(dirname "$0")/check_repository.py"\n',
    "pre-push": '#!/bin/sh\nset -eu\nwhile read -r local_ref local_sha remote_ref remote_sha; do\n    case "$local_sha" in\n        0000000000000000000000000000000000000000) continue ;;\n    esac\n    python3 "$(dirname "$0")/check_repository.py" --history --revision "$local_sha"\ndone\n',
}


def install_hooks():
    hooks = Path(git("rev-parse", "--git-path", "hooks").decode().strip())
    hooks.mkdir(parents=True, exist_ok=True)
    for name, content in HOOKS.items():
        target = hooks / name
        if target.exists() and target.read_text() != content:
            raise RuntimeError(f"Existing hook requires manual integration: {target}")
    shutil.copy2(Path(__file__), hooks / "check_repository.py")
    for name, content in HOOKS.items():
        target = hooks / name
        target.write_text(content)
        target.chmod(0o755)
    print("Installed repository checks for this clone")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--install-hooks", action="store_true")
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    if args.install_hooks:
        install_hooks()
        return
    indexed = git("ls-files", "-z").decode().split("\0")
    check_paths(name for name in indexed if name)
    if args.history:
        commits = git("rev-list", args.revision).decode().splitlines()
        for commit in commits:
            names = (
                git("ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0")
            )
            check_paths((name for name in names if name), historical=True)
        print(f"Publication paths: index and {len(commits)} commits: PASS")
    else:
        print("Publication paths: index: PASS")


if __name__ == "__main__":
    main()
