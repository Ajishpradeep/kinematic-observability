"""Hash the exact private sources and public pilot implementation used in analysis."""

import json
from pathlib import Path

from observability.assets import local_output, sha256


def record_pilot_provenance(
    private_manifest,
    samples,
    output=Path("local/pilot/source-provenance.json"),
):
    """Record content hashes under opaque identifiers without exporting source names."""
    root = Path(private_manifest["root"])
    manifest_by_take = {
        record["take_id"]: record for record in private_manifest["records"]
    }
    sources = []
    seen = set()
    for sample_name, sample in samples.items():
        for sample_record in sample["records"]:
            record = manifest_by_take[sample_record["take_id"]]
            candidates = [
                ("body_csv", record["body_csv"], None),
                ("calibration", record["calibration_candidates"][0], None),
            ]
            candidates.extend(
                ("video", video["path"], index)
                for index, video in enumerate(record["candidate_videos"])
            )
            for kind, relative, camera_index in candidates:
                key = (kind, relative)
                if key in seen:
                    continue
                seen.add(key)
                path = root / relative
                sources.append(
                    {
                        "sample": sample_name,
                        "take_id": record["take_id"] if kind != "calibration" else None,
                        "session_id": record["session_id"],
                        "kind": kind,
                        "camera_index": camera_index,
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
    pilot_root = Path("src/observability/pilot")
    implementation = {
        str(path): sha256(path)
        for path in sorted(pilot_root.glob("*.py"))
        if path.is_file()
    }
    result = {
        "schema": "expansion-pilot-provenance-v1",
        "sources": sources,
        "implementation_sha256": implementation,
        "source_names_exported": False,
    }
    output = local_output(Path(output))
    output.write_text(json.dumps(result, indent=2) + "\n")
    output.chmod(0o600)
    return result
