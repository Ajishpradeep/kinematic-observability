"""Validate force-source timing and decide whether kinetics claims are supportable."""

import json
import warnings
from collections import Counter
from pathlib import Path

from observability.assets import local_output

from .inventory import _body_metadata, _force_metadata


def audit_force_sources(
    manifest,
    output=Path("local/pilot/force-validation.json"),
):
    """Check clock compatibility, then apply the predeclared force stop rule."""
    root = Path(manifest["root"])
    records = []
    errors = Counter()
    for record in manifest["records"]:
        if not record["candidate_force_csv"] and not record["candidate_c3d"]:
            continue
        body_rate, body_frames, _ = _body_metadata(root / record["body_csv"])
        row = {
            "take_id": record["take_id"],
            "session_id": record["session_id"],
            "body_rate_hz": body_rate,
            "body_frames": body_frames,
            "force_csv": [],
            "c3d": [],
        }
        for relative in record["candidate_force_csv"]:
            try:
                rate, frames = _force_metadata(root / relative)
                row["force_csv"].append(
                    {
                        "rate_hz": rate,
                        "frames": frames,
                        "rate_matches_body": abs(rate - body_rate) < 1e-6,
                        "frames_match_body": frames == body_frames,
                    }
                )
            except (OSError, ValueError, KeyError) as error:
                errors["force_csv_" + type(error).__name__] += 1
        for relative in record["candidate_c3d"]:
            try:
                import c3d

                with (root / relative).open("rb") as stream:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        reader = c3d.Reader(stream)
                    # python-c3d exposes last_frame as an exclusive bound.
                    frames = int(reader.last_frame - reader.first_frame)
                    labels = [str(label).strip() for label in reader.analog_labels]
                    row["c3d"].append(
                        {
                            "point_rate_hz": float(reader.point_rate),
                            "analog_rate_hz": float(reader.analog_rate),
                            "frames": frames,
                            "frames_match_body": frames == body_frames,
                            "point_rate_matches_body": bool(
                                abs(reader.point_rate - body_rate) < 1e-6
                            ),
                            "analog_rate_matches_body": bool(
                                abs(reader.analog_rate - body_rate) < 1e-6
                            ),
                            "dual_force_moment_channels": labels
                            == [
                                "Fx1",
                                "Fy1",
                                "Fz1",
                                "Mx1",
                                "My1",
                                "Mz1",
                                "Fx2",
                                "Fy2",
                                "Fz2",
                                "Mx2",
                                "My2",
                                "Mz2",
                            ],
                        }
                    )
            except (ImportError, OSError, ValueError, KeyError) as error:
                errors["c3d_" + type(error).__name__] += 1
        records.append(row)

    csv_rows = [item for row in records for item in row["force_csv"]]
    c3d_rows = [item for row in records for item in row["c3d"]]
    clocks_match = bool(
        not errors
        and all(
            item["rate_matches_body"] and item["frames_match_body"] for item in csv_rows
        )
        and all(
            item["frames_match_body"]
            and item["point_rate_matches_body"]
            and item["analog_rate_matches_body"]
            for item in c3d_rows
        )
    )
    result = {
        "schema": "optitrack-force-validation-v1",
        "force_takes": len(records),
        "separate_force_csv_exports": len(csv_rows),
        "c3d_exports": len(c3d_rows),
        "clock_and_frame_metadata_match": clocks_match,
        "dual_force_moment_c3d": sum(
            item["dual_force_moment_channels"] for item in c3d_rows
        ),
        "errors": dict(sorted(errors.items())),
        "records": records,
        "kinetics_requirements": {
            "subject_mass_or_quiet_stance_verified": False,
            "plate_geometry_and_world_transform_verified": False,
            "contact_assignment_verified": False,
            "implement_momentum_bounded": False,
        },
        "central_kinetics_branch_eligible": False,
        "decision": (
            "Close force as a central endpoint. Clock metadata can be audited, but "
            "mass, plate geometry, contact, and implement dynamics are not bounded."
        ),
        "allowed_future_use": (
            "Secondary falsification only after the missing physical requirements "
            "are independently established."
        ),
    }
    output = local_output(Path(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
