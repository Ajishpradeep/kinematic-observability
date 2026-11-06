"""Regression checks for package entry points and run provenance."""

import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from observability.__main__ import main
from observability.verification import source_hashes


class WorkflowTests(unittest.TestCase):
    def test_run_outside_checkout_records_source_and_denominators(self):
        original = Path.cwd()
        expected_hashes = source_hashes()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with contextlib.redirect_stdout(io.StringIO()):
                    main(
                        [
                            "run",
                            "--out",
                            "run",
                            "--synthetic-n",
                            "4",
                            "--steps",
                            "1",
                            "--smoke",
                        ]
                    )
                manifest = json.loads(Path("run/manifest.json").read_text())
                with Path("run/aggregates.csv").open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
            finally:
                os.chdir(original)
        self.assertEqual(manifest["source_sha256"], expected_hashes)
        self.assertIn("src/observability/geometry.py", expected_hashes)
        self.assertEqual(manifest["seeds"], [17, 29, 43])
        self.assertEqual(manifest["row_count"], 42)
        self.assertEqual(len(rows), 42)
        self.assertTrue(all(int(row["n"]) == 4 for row in rows))
        self.assertEqual(
            {row["subject"] for row in rows}, {"seed17", "seed29", "seed43"}
        )

    def test_prepare_rejects_public_output_before_reading_cache(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "prepare",
                        "--cohort-root",
                        "/missing",
                        "--out",
                        "results/cohort.npz",
                    ]
                )
        self.assertEqual(raised.exception.code, 2)

    def test_invalid_run_budget_fails_before_execution(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["run", "--out", "local/invalid", "--batch", "0"])
        self.assertEqual(raised.exception.code, 2)

    def test_subcommand_help(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(["run", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--synthetic-n", output.getvalue())


if __name__ == "__main__":
    unittest.main()
