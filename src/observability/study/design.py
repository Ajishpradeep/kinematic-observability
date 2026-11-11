"""Freeze a retrospective, capture-group-held-out OptiTrack design."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from observability.assets import local_output, sha256
from observability.pilot.alignment import _direct_pair

DESIGN_VERSION = "wrist-transfer-v1"
FRACTIONS = (0.2, 0.5, 0.8)
OFFSET = 6
TOLERANCES = {"absolute": 100, "change": 50}
PILOT_INPUTS = (
    "state.json",
    "synthesis.json",
    "optitrack-census.json",
    "manifest-private.json",
    "manifest-summary.json",
    "input-validation-private.json",
    "input-validation-summary.json",
    "reference-audit.json",
    "source-provenance.json",
    "alignment/sample-private.json",
    "confirmation/sample-private.json",
    "alignment/score.json",
    "confirmation/score.json",
    "alignment/yolo26n/manifest.json",
    "confirmation/yolo26n/manifest.json",
    "triangulation.json",
    "confirmation/triangulation.json",
    "sam-repeatability.json",
    "force-validation.json",
)


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    path = local_output(Path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def schedule(frame_count):
    return [
        [centre - OFFSET, centre, centre + OFFSET]
        for centre in (round(fraction * (frame_count - 1)) for fraction in FRACTIONS)
    ]


def freeze(pilot, output):
    pilot = Path(pilot)
    source = read_json(pilot / "manifest-private.json")
    validation = read_json(pilot / "input-validation-private.json")
    samples = [
        read_json(pilot / f"{name}/sample-private.json")["records"]
        for name in ("alignment", "confirmation")
    ]
    known_pilot = {row["take_id"] for sample in samples for row in sample}
    if len(known_pilot) != 14:
        raise ValueError("expected 14 distinct pilot takes")
    marker_groups = {
        row["session_id"]
        for row in samples[0]
        if row["reference_source"] == "marker_constructed"
    }
    by_hash = sorted(
        marker_groups,
        key=lambda group: hashlib.sha256(
            f"{DESIGN_VERSION}/{group}".encode()
        ).hexdigest(),
    )
    development = set(by_hash[:3])
    validation_by_take = {row["take_id"]: row for row in validation["records"]}
    records = []
    for row in sorted(source["records"], key=lambda item: item["take_id"]):
        take = row["take_id"]
        validated = validation_by_take[take]
        direct = _direct_pair(validated)
        status = "scheduled"
        if not direct:
            status = "nominal_alignment_exclusion"
        elif take in known_pilot:
            status = "pilot_exclusion"
        record = {
            "take_id": take,
            "group": row["session_id"],
            "split": (
                "development" if row["session_id"] in development else "confirmation"
            ),
            "status": status,
            "body_frames": validated["body_frames"],
            "fps": validated["export_rate_hz"],
            "views_in_manifest": len(row["candidate_videos"]),
        }
        if status == "scheduled":
            record.update(
                body_csv=row["body_csv"],
                calibration=row["calibration_candidates"][0],
                views=sorted(
                    row["candidate_videos"], key=lambda view: view["camera_serial"]
                ),
                windows=schedule(validated["body_frames"]),
            )
        records.append(record)
    design = {
        "schema": DESIGN_VERSION,
        "pilot_inputs_sha256": {name: sha256(pilot / name) for name in PILOT_INPUTS},
        "root": source["root"],
        "split_rule": "three marker-alignment groups by versioned SHA-256 order; remaining groups held out",
        "counts": dict(Counter(row["status"] for row in records)),
        "policy": {
            "tolerances_mm": TOLERANCES,
            "max_accepted_failure": 0.2,
            "min_coverage": 0.1,
            "repeat_score_quantile": 0.8,
            "moved_reference_floor_mm": 10,
            "min_group_direction_pairs": 50,
        },
        "records": records,
    }
    path = Path(output)
    if path.exists():
        if read_json(path) != design:
            raise ValueError("existing frozen design differs")
    else:
        write_json(path, design)
    return design


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=Path("local/pilot"))
    parser.add_argument("--output", type=Path, default=Path("local/study/design.json"))
    args = parser.parse_args()
    print(freeze(args.pilot, args.output)["counts"])
