"""Private take-candidate manifest with a publication-safe aggregate summary."""

import hashlib
import hmac
import json
import os
import secrets
from collections import Counter, defaultdict
from pathlib import Path

from observability.assets import local_output

from .inventory import classify_csv
from .video import camera_serial, video_take_stem


def _opaque(salt, kind, value):
    payload = "{}:{}".format(kind, value).encode("utf-8")
    return "{}-{}".format(
        kind.upper(), hmac.new(salt, payload, hashlib.sha256).hexdigest()[:12]
    )


def _load_or_create_salt(path):
    if path.exists():
        salt = path.read_bytes()
        if len(salt) < 32:
            raise ValueError("existing identifier salt is too short")
        return salt
    salt = secrets.token_bytes(32)
    path.write_bytes(salt)
    path.chmod(0o600)
    return salt


def _assign_by_longest_anchor(anchors, candidates):
    assigned = defaultdict(list)
    unmatched = []
    ambiguous = []
    for candidate in candidates:
        candidate_stem = candidate.stem.casefold()
        matches = [
            anchor for anchor in anchors if anchor.stem.casefold() in candidate_stem
        ]
        if not matches:
            unmatched.append(candidate)
            continue
        longest = max(len(anchor.stem) for anchor in matches)
        winners = [anchor for anchor in matches if len(anchor.stem) == longest]
        if len(winners) != 1:
            ambiguous.append(candidate)
            continue
        assigned[winners[0]].append(candidate)
    return assigned, unmatched, ambiguous


def _assign_videos(anchors, candidates):
    by_stem = defaultdict(list)
    for anchor in anchors:
        by_stem[anchor.stem.casefold()].append(anchor)
    assigned = defaultdict(list)
    unmatched = []
    ambiguous = []
    for candidate in candidates:
        matches = by_stem[video_take_stem(candidate).casefold()]
        if not matches:
            unmatched.append(candidate)
        elif len(matches) > 1:
            ambiguous.append(candidate)
        else:
            assigned[matches[0]].append(candidate)
    return assigned, unmatched, ambiguous


def _relative_strings(paths, root):
    return [str(path.relative_to(root)) for path in sorted(paths)]


def build_manifest(root, output_dir=Path("local/pilot")):
    """Write a private candidate map and a name-free summary.

    Filename matching creates candidates only. It does not establish camera identity,
    synchronization, or scientific validity.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("OptiTrack root is not a directory")
    output_dir = local_output(Path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    salt_path = local_output(output_dir / "id-salt.bin")
    salt = _load_or_create_salt(salt_path)

    groups = defaultdict(lambda: defaultdict(list))
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root)
            if len(relative.parts) < 2:
                continue
            suffix = path.suffix.lower()
            if suffix == ".csv":
                kind = classify_csv(path)
                if kind in {"body", "force"}:
                    groups[relative.parts[0]][kind].append(path)
            elif suffix in {".avi", ".c3d", ".mcal"}:
                groups[relative.parts[0]][suffix[1:]].append(path)

    records = []
    group_summaries = []
    unmatched_totals = Counter()
    for group_name in sorted(groups):
        group = groups[group_name]
        bodies = sorted(group["body"])
        if not bodies:
            continue
        assignments = {}
        for kind in ("avi", "force", "c3d"):
            assigner = _assign_videos if kind == "avi" else _assign_by_longest_anchor
            assigned, unmatched, ambiguous = assigner(bodies, group[kind])
            assignments[kind] = assigned
            unmatched_totals[kind] += len(unmatched)
            unmatched_totals[kind + "_ambiguous"] += len(ambiguous)

        session_id = _opaque(salt, "session", group_name)
        for body in bodies:
            record = {
                "take_id": _opaque(salt, "take", str(body.relative_to(root))),
                "session_id": session_id,
                "body_csv": str(body.relative_to(root)),
                "candidate_videos": [
                    {
                        "path": str(path.relative_to(root)),
                        "camera_serial": camera_serial(path),
                    }
                    for path in sorted(assignments["avi"].get(body, []))
                ],
                "candidate_force_csv": _relative_strings(
                    assignments["force"].get(body, []), root
                ),
                "candidate_c3d": _relative_strings(
                    assignments["c3d"].get(body, []), root
                ),
                "calibration_candidates": _relative_strings(group["mcal"], root),
                "pairing_method": "unique-longest-anchor-substring",
                "camera_identity_verified": False,
                "synchronization_verified": False,
                "reference_semantics_verified": False,
            }
            records.append(record)
        group_summaries.append(
            {
                "session_id": session_id,
                "takes": len(bodies),
                "calibration_candidates": len(group["mcal"]),
            }
        )

    video_counts = Counter(len(record["candidate_videos"]) for record in records)
    force_counts = Counter(len(record["candidate_force_csv"]) for record in records)
    c3d_counts = Counter(len(record["candidate_c3d"]) for record in records)
    force_evidence = Counter()
    for record in records:
        csv_count = len(record["candidate_force_csv"])
        c3d_count = len(record["candidate_c3d"])
        if csv_count == 2 and c3d_count == 0:
            force_evidence["paired_csv_candidates"] += 1
        elif csv_count == 0 and c3d_count == 1:
            force_evidence["c3d_candidate"] += 1
        elif csv_count == 0 and c3d_count == 0:
            force_evidence["none_found"] += 1
        else:
            force_evidence["irregular_or_overlapping"] += 1
    summary = {
        "schema": "optitrack-pilot-manifest-summary-v1",
        "takes": len(records),
        "sessions": group_summaries,
        "candidate_videos_per_take": dict(sorted(video_counts.items())),
        "candidate_force_csv_per_take": dict(sorted(force_counts.items())),
        "candidate_c3d_per_take": dict(sorted(c3d_counts.items())),
        "force_evidence_per_take": dict(sorted(force_evidence.items())),
        "unmatched_candidates": dict(sorted(unmatched_totals.items())),
        "pairing_complete": False,
        "qualifications": [
            "Source paths exist only in the ignored private manifest.",
            "Filename candidates do not establish camera identity or synchronization.",
            "Independent participant and session units remain unresolved.",
        ],
    }
    private = {
        "schema": "optitrack-pilot-private-manifest-v1",
        "root": str(root),
        "records": records,
    }
    private_path = local_output(output_dir / "manifest-private.json")
    summary_path = local_output(output_dir / "manifest-summary.json")
    private_path.write_text(json.dumps(private, indent=2) + "\n")
    private_path.chmod(0o600)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return {
        "private": private,
        "summary": summary,
        "private_path": private_path,
        "summary_path": summary_path,
    }
