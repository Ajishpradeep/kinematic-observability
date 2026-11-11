"""Semantic Motive CSV parsing with explicit frames and missingness."""

import csv
from pathlib import Path

import numpy as np


def _rows_until_frame(path):
    rows = []
    with Path(path).open(
        "r", encoding="utf-8-sig", errors="replace", newline=""
    ) as stream:
        for index, row in enumerate(csv.reader(stream)):
            rows.append(row)
            if row and row[0].strip() == "Frame":
                return rows, index
            if index > 30:
                break
    raise ValueError("could not locate Motive Frame header")


def read_schema(path):
    """Return metadata and semantic XYZ column blocks."""
    rows, frame_row_index = _rows_until_frame(path)
    metadata = {
        rows[0][index].strip(): rows[0][index + 1].strip()
        for index in range(0, len(rows[0]) - 1, 2)
    }
    frame_row = rows[frame_row_index]
    width = len(frame_row)
    padded = [row + [""] * (width - len(row)) for row in rows]
    type_row = next(
        (
            row
            for row in padded[:frame_row_index]
            if len(row) > 1 and row[1].strip() == "Type"
        ),
        None,
    )
    if type_row is None:
        raise ValueError("could not locate Motive Type row")
    type_index = padded.index(type_row)
    name_row = padded[type_index + 1]
    component_row = max(
        padded[type_index + 1 : frame_row_index],
        key=lambda row: sum(value.strip() in {"Position", "Rotation"} for value in row),
    )
    blocks = []
    current = None
    for column in range(2, width):
        dimension = frame_row[column].strip()
        if dimension == "X":
            raw_name = name_row[column].strip()
            current = {
                "entity_type": type_row[column].strip(),
                "name": raw_name,
                "semantic_name": raw_name.split(":")[-1],
                "component": component_row[column].strip(),
                "columns": {"X": column},
            }
            blocks.append(current)
        elif dimension in {"Y", "Z"} and current is not None:
            current["columns"][dimension] = column
    blocks = [
        block
        for block in blocks
        if block["component"] == "Position" and set(block["columns"]) == {"X", "Y", "Z"}
    ]
    if not blocks:
        raise ValueError("Motive export has no complete XYZ position blocks")
    return {
        "metadata": metadata,
        "frame_row_index": frame_row_index,
        "blocks": blocks,
    }


def load_positions(path, entity_type=None, semantic_names=None):
    """Load selected positions indexed by explicit Motive frame number."""
    schema = read_schema(path)
    blocks = schema["blocks"]
    if entity_type is not None:
        blocks = [block for block in blocks if block["entity_type"] == entity_type]
    if semantic_names is not None:
        requested = set(semantic_names)
        blocks = [block for block in blocks if block["semantic_name"] in requested]
    if not blocks:
        raise ValueError("no position blocks match the requested semantics")

    frames = []
    values = []
    with Path(path).open(
        "r", encoding="utf-8-sig", errors="replace", newline=""
    ) as stream:
        reader = csv.reader(stream)
        for _ in range(schema["frame_row_index"] + 1):
            next(reader)
        for row in reader:
            if not row or not row[0].strip().isdigit():
                continue
            frames.append(int(row[0]))
            frame_values = []
            for block in blocks:
                coordinates = []
                for dimension in ("X", "Y", "Z"):
                    column = block["columns"][dimension]
                    try:
                        coordinates.append(float(row[column]))
                    except (IndexError, ValueError):
                        coordinates.append(float("nan"))
                frame_values.append(coordinates)
            values.append(frame_values)
    if not frames:
        raise ValueError("Motive export has no numbered data frames")
    output = np.full((max(frames) + 1, len(blocks), 3), np.nan, dtype=np.float32)
    output[np.asarray(frames, dtype=int)] = np.asarray(values, dtype=np.float32)
    return {
        "positions": output,
        "semantic_names": [block["semantic_name"] for block in blocks],
        "entity_types": [block["entity_type"] for block in blocks],
        "metadata": schema["metadata"],
    }
