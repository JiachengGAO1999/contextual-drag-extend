"""Compatibility entry point for upstream's missing aggregate_data_minimal.py.

It intentionally delegates argument parsing and all behavior to the shipped script.
"""

import runpy


def main() -> None:
    runpy.run_module("data_generation.aggregate_data", run_name="__main__")


if __name__ == "__main__":
    main()
