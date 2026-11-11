"""Read-only OptiTrack inventory for the private expansion decision pilot.

The summary contains opaque session ids and aggregate metadata, never source names.
Take pairing is deferred until format and synchronization gates are frozen.
"""

import csv
import os
import warnings
from collections import Counter, defaultdict
from pathlib import Path


def _head(path, limit=131072):
    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as stream:
        return stream.read(limit)


def classify_csv(path):
    """Classify supported exports by content rather than path, name, or file size."""
    text = _head(path)
    if "Device Name,Bertec" in text and "MocapFrame" in text and "Fz" in text:
        return "force"
    rows = list(csv.reader(text.splitlines()[:10]))
    flattened = " ".join(value for row in rows for value in row)
    if "Format Version" in flattened and ("Bone" in flattened or "Marker" in flattened):
        return "body"
    return "other"


def _body_metadata(path):
    rows = list(csv.reader(_head(path).splitlines()[:9]))
    if not rows:
        raise ValueError("empty body export")
    metadata = rows[0]
    pairs = {
        metadata[index].strip(): metadata[index + 1].strip()
        for index in range(0, len(metadata) - 1, 2)
    }
    frame_rate = float(pairs["Export Frame Rate"])
    frames = int(pairs.get("Total Exported Frames", pairs["Total Frames in Take"]))
    rotation = "quaternion" if "W" in rows[7] else "euler"
    return frame_rate, frames, rotation


def _force_metadata(path):
    rows = list(csv.reader(_head(path).splitlines()[:36]))
    pairs = {
        row[0].strip(): row[1].strip()
        for row in rows[:33]
        if len(row) > 1 and row[0].strip()
    }
    channels = [value.strip() for value in rows[34]] if len(rows) > 34 else []
    required = {"Fx", "Fy", "Fz", "Mx", "My", "Mz", "Cx", "Cy", "Cz"}
    if not required.issubset(channels):
        raise ValueError("force export lacks required channels")
    return float(pairs["Export Frame Rate"]), int(pairs["Total Exported Frames"])


def _c3d_metadata(path):
    try:
        import c3d
    except ImportError:
        return {"status": "reader_unavailable"}
    with Path(path).open("rb") as stream:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            reader = c3d.Reader(stream)
        labels = [str(value).strip() for value in reader.analog_labels]
        return {
            "status": "readable",
            "point_count": len(reader.point_labels),
            "analog_count": len(labels),
            "point_rate_hz": float(reader.point_rate),
            "analog_rate_hz": float(reader.analog_rate),
            "dual_force_channels": labels
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


def scan_optitrack(root):
    """Return an aggregate, outcome-neutral census with opaque session identifiers."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("OptiTrack root is not a directory")
    files = []
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory) / name
            if not path.is_symlink():
                files.append(path)
    top_levels = sorted(
        {
            path.relative_to(root).parts[0]
            for path in files
            if path.relative_to(root).parts
        }
    )
    sessions = defaultdict(lambda: {"extensions": Counter(), "bytes": 0})
    errors = Counter()
    body_signatures = Counter()
    force_signatures = Counter()
    c3d_signatures = Counter()
    for path in files:
        relative = path.relative_to(root)
        session = sessions[relative.parts[0]]
        suffix = path.suffix.lower() or "<none>"
        size = path.stat().st_size
        session["extensions"][suffix] += 1
        session["bytes"] += size
        try:
            if suffix == ".csv":
                kind = classify_csv(path)
                session[kind + "_csv"] = session.get(kind + "_csv", 0) + 1
                if kind == "body":
                    body_signatures[_body_metadata(path)] += 1
                elif kind == "force":
                    force_signatures[_force_metadata(path)] += 1
            elif suffix == ".c3d":
                signature = _c3d_metadata(path)
                c3d_signatures[tuple(sorted(signature.items()))] += 1
        except (OSError, UnicodeError, ValueError, KeyError) as error:
            errors[type(error).__name__] += 1
    capture_groups = [
        name
        for name in top_levels
        if sessions[name].get("body_csv", 0)
        or sessions[name].get("force_csv", 0)
        or any(
            sessions[name]["extensions"].get(suffix, 0)
            for suffix in (".avi", ".c3d", ".mcal")
        )
    ]
    opaque = {
        name: "S{:03d}".format(index + 1)
        for index, name in enumerate(sorted(capture_groups))
    }
    total = Counter()
    session_rows = []
    for source_group in sorted(capture_groups):
        row = sessions[source_group]
        total.update(row["extensions"])
        session_rows.append(
            {
                "session": opaque[source_group],
                "files_by_extension": dict(sorted(row["extensions"].items())),
                "bytes": row["bytes"],
                "body_csv": row.get("body_csv", 0),
                "force_csv": row.get("force_csv", 0),
                "other_csv": row.get("other_csv", 0),
            }
        )
    return {
        "schema": "optitrack-pilot-census-v1",
        "complete": not errors,
        "files_by_extension": dict(sorted(total.items())),
        "sessions": session_rows,
        "body_export_signatures": [
            {
                "export_rate_hz": key[0],
                "frames": key[1],
                "rotation": key[2],
                "files": count,
            }
            for key, count in sorted(body_signatures.items())
        ],
        "body_export_totals": {
            "files": sum(body_signatures.values()),
            "frames": sum(key[1] * count for key, count in body_signatures.items()),
        },
        "force_export_signatures": [
            {"export_rate_hz": key[0], "frames": key[1], "files": count}
            for key, count in sorted(force_signatures.items())
        ],
        "c3d_signatures": [
            {**dict(key), "files": count} for key, count in c3d_signatures.items()
        ],
        "errors": dict(sorted(errors.items())),
        "qualifications": [
            "This is a session-level census, not a take-level pairing manifest.",
            "Folder groups are not assumed to be independent participants.",
            "File presence proves neither synchronization nor publication permission.",
        ],
    }
