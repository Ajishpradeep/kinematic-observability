"""Audit marker-reference availability and disagreement with fitted origins."""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from observability.assets import local_output

from .motive import load_positions, read_schema
from .references import (
    FITTED_REFERENCE_SPECS,
    MARKER_REFERENCE_SPECS,
    fitted_joint_references,
    marker_joint_references,
)

SCHEMA_COVERAGE_THRESHOLD = 0.70
FRAME_COVERAGE_THRESHOLD = 0.80


def _summary(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return {"n": 0, "median": None, "p90": None, "mean": None}
    return {
        "n": int(len(values)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
        "mean": float(np.mean(values)),
    }


def audit_references(
    manifest,
    alignment_sample,
    output=Path("local/pilot/reference-audit.json"),
):
    """Evaluate schema coverage, frame availability, and reference disagreement."""
    root = Path(manifest["root"])
    schema_presence = defaultdict(int)
    schema_errors = 0
    for record in manifest["records"]:
        try:
            schema = read_schema(root / record["body_csv"])
        except (OSError, ValueError):
            schema_errors += 1
            continue
        marker_names = {
            block["semantic_name"]
            for block in schema["blocks"]
            if block["entity_type"] == "Marker"
        }
        for name, _, required in MARKER_REFERENCE_SPECS:
            if set(required).issubset(marker_names):
                schema_presence[name] += 1

    marker_names = sorted(
        {marker for _, _, required in MARKER_REFERENCE_SPECS for marker in required}
    )
    fitted_names = [name for _, _, name in FITTED_REFERENCE_SPECS]
    per_take = []
    disagreement = defaultdict(list)
    frame_coverage = defaultdict(list)
    evaluation_errors = 0
    for source in manifest["records"]:
        try:
            combined = load_positions(
                root / source["body_csv"],
                semantic_names=marker_names + fitted_names,
            )
        except (OSError, ValueError):
            evaluation_errors += 1
            continue
        entity_types = np.asarray(combined["entity_types"])
        semantic_names = np.asarray(combined["semantic_names"])
        marker_mask = entity_types == "Marker"
        fitted_mask = entity_types == "Bone"
        marker = marker_joint_references(
            combined["positions"][:, marker_mask], semantic_names[marker_mask].tolist()
        )
        try:
            fitted = fitted_joint_references(
                combined["positions"][:, fitted_mask],
                semantic_names[fitted_mask].tolist(),
            )
        except ValueError:
            evaluation_errors += 1
            continue
        take_row = {
            "take_id": source["take_id"],
            "session_id": source["session_id"],
            "joints": {},
        }
        for index, name in enumerate(marker["names"]):
            marker_valid = marker["valid"][:, index]
            fitted_valid = fitted["valid"][:, index]
            common = marker_valid & fitted_valid
            distance = np.linalg.norm(
                marker["xyz"][common, index] - fitted["xyz"][common, index],
                axis=1,
            )
            coverage = float(np.mean(marker_valid))
            frame_coverage[name].append(coverage)
            if len(distance):
                disagreement[name].append(float(np.median(distance)))
            take_row["joints"][name] = {
                "marker_frame_coverage": coverage,
                "fitted_frame_coverage": float(np.mean(fitted_valid)),
                "disagreement_mm": _summary(distance),
            }
        per_take.append(take_row)

    total_takes = len(manifest["records"])
    joint_summary = {}
    for name, _, _ in MARKER_REFERENCE_SPECS:
        schema_fraction = schema_presence[name] / total_takes
        coverage_values = frame_coverage[name]
        median_coverage = float(np.median(coverage_values)) if coverage_values else None
        eligible = bool(
            schema_fraction >= SCHEMA_COVERAGE_THRESHOLD
            and median_coverage is not None
            and median_coverage >= FRAME_COVERAGE_THRESHOLD
        )
        joint_summary[name] = {
            "schema_takes": schema_presence[name],
            "schema_fraction": schema_fraction,
            "take_frame_coverage": _summary(coverage_values),
            "take_median_marker_vs_fitted_disagreement_mm": _summary(
                disagreement[name]
            ),
            "eligible_as_primary_marker_endpoint": eligible,
        }
    result = {
        "schema": "optitrack-reference-audit-v1",
        "frozen_thresholds": {
            "minimum_schema_fraction": SCHEMA_COVERAGE_THRESHOLD,
            "minimum_median_frame_coverage": FRAME_COVERAGE_THRESHOLD,
        },
        "schema_takes": total_takes,
        "schema_errors": schema_errors,
        "evaluated_takes": len(per_take),
        "evaluation_errors": evaluation_errors,
        "joints": joint_summary,
        "per_take": per_take,
        "qualifications": [
            "Marker midpoint and Motive fitted origin are distinct imperfect references.",
            "Frame coverage is measured across every parseable admitted body take.",
            "Disagreement aggregates take-level medians rather than treating frames as independent.",
            "Eligibility is a pilot endpoint rule, not anatomical truth validation.",
        ],
    }
    output = local_output(Path(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
