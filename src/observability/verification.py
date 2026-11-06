"""Verify archived source hashes, evidence integrity and aggregate invariants."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

METRICS = (
    "joint_mm",
    "distal_mm",
    "distal_depth_mm",
    "bend_deg",
    "reprojection_px",
    "length_reference_mm",
    "length_constraint_mm",
)


def source_hashes():
    """Return repository-relative hashes, or package hashes in an installed wheel."""
    package = Path(__file__).resolve().parent
    root = package.parent.parent
    paths = sorted(package.glob("*.py"))
    if (root / "pyproject.toml").is_file():
        paths += [root / "pyproject.toml", root / "reports/README.md"]
        paths += sorted((root / "tests").glob("*.py"))
    else:
        root = package.parent
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def verify(root):
    artifacts = json.loads((root / "results/artifacts.json").read_text())
    for name, expected in artifacts.items():
        require(
            hashlib.sha256((root / name).read_bytes()).hexdigest() == expected,
            f"Changed recorded artifact: {name}",
        )
    for folder in ("synthetic", "optitrack", "optitrack_400", "oracle_pixels"):
        directory = root / "results" / folder
        with (directory / "aggregates.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        manifest = json.loads((directory / "manifest.json").read_text())
        for name, expected in manifest["source_sha256"].items():
            with ZipFile(root / "results/baseline-source.zip") as archive:
                source = archive.read(name)
            require(
                hashlib.sha256(source).hexdigest() == expected,
                f"{folder}: source hash mismatch: {name}",
            )
        require(bool(rows), f"{folder}: empty aggregates")
        if "row_count" in manifest:
            require(len(rows) == manifest["row_count"], f"{folder}: row count mismatch")
        counts = {}
        keys = set()
        for row in rows:
            for metric in METRICS:
                value = float(row[metric])
                require(
                    math.isfinite(value) and value >= 0, f"{folder}: invalid {metric}"
                )
            if row["method"].startswith("fk") or row["method"] == "length_project":
                require(
                    float(row["length_constraint_mm"]) < 1e-6,
                    f"{folder}: fixed-length guarantee failed",
                )
            if row["method"] == "fk_hard":
                require(
                    float(row["cap_violation_fraction"]) == 0,
                    f"{folder}: hard bound failed",
                )
            key = (row["subject"], row["view"])
            n = int(row["n"])
            counts.setdefault(key, n)
            require(n > 0 and counts[key] == n, f"{folder}: unequal comparison counts")
            full_key = tuple(
                row[k]
                for k in (
                    "subject",
                    "view",
                    "lengths",
                    "observations",
                    "cap_deg",
                    "method",
                )
            )
            require(full_key not in keys, f"{folder}: duplicate comparison")
            keys.add(full_key)
        print(f"{folder}: {len(rows)} aggregate rows: PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing results and provenance",
    )
    verify(parser.parse_args(argv).root)
