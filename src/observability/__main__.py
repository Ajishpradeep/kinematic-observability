"""Command entry point for experiments, reporting and evidence verification."""

import argparse
import importlib
import sys

COMMANDS = {
    "run": ("experiment", "Run synthetic or authorized local-data experiments"),
    "report": ("reporting", "Generate tables and figures from aggregates"),
    "verify": ("verification", "Check recorded evidence and numerical guarantees"),
    "prepare": ("data", "Adapt an authorized local cohort cache"),
    "oracle": ("experiment", "Run the reference-projected pixel diagnostic"),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS, help="Analysis command")
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(argv[:1])
    rest = argv[1:]
    module = importlib.import_module("observability." + COMMANDS[args.command][0])
    handler = module.oracle_main if args.command == "oracle" else module.main
    handler(rest)


if __name__ == "__main__":
    main()
