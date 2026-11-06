"""Read-only inventory of configured external assets; export counts without filenames."""

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def local_output(path):
    """Keep machine-specific inventories and predictions under ignored local/."""
    path = path.resolve()
    if (Path.cwd() / "local").resolve() not in path.parents:
        raise ValueError("output must be under local/ in the working directory")
    return path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_asset(asset, scan=False):
    path = Path(asset["path"]).expanduser()
    result = dict(asset, exists=path.exists(), resolved=str(path.resolve()))
    if not scan or not path.is_dir():
        return result
    counts = Counter()
    sizes = Counter()
    errors = []
    for directory, _, files in os.walk(
        path, followlinks=False, onerror=lambda _: errors.append(1)
    ):
        for name in files:
            item = Path(directory) / name
            if item.is_symlink():
                continue
            try:
                size = item.stat().st_size
            except OSError:
                errors.append(1)
                continue
            suffix = item.suffix.lower() or "<none>"
            counts[suffix] += 1
            sizes[suffix] += size
    result.update(
        files_by_extension=dict(sorted(counts.items())),
        bytes_by_extension=dict(sorted(sizes.items())),
        scan_errors=len(errors),
        complete=not errors,
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Local JSON list of id/path/role records",
    )
    parser.add_argument(
        "--scan",
        nargs="*",
        default=[],
        help="Asset ids to count recursively; others only checked for existence",
    )
    parser.add_argument("--out", type=Path, default=Path("local/asset-audit.json"))
    args = parser.parse_args(argv)
    output = local_output(args.out)
    assets = json.loads(args.config.read_text())
    ids = [asset["id"] for asset in assets]
    if len(ids) != len(set(ids)) or set(args.scan) - set(ids):
        parser.error("asset ids must be unique and --scan must name configured ids")
    records = [inspect_asset(asset, asset["id"] in args.scan) for asset in assets]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "config_sha256": sha256(args.config),
                "assets": records,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"{len(records)} assets checked; {sum(r['exists'] for r in records)} present; saved {output}"
    )
