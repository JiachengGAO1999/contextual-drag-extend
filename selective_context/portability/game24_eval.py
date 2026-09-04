from __future__ import annotations

import argparse
import json
from pathlib import Path

from selective_context.official_compat import evaluate_game24_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight general-inference Game24 evaluator wrapper.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open("r", encoding="utf-8") as source, args.output.open("w", encoding="utf-8") as target:
        for line in source:
            if line.strip():
                target.write(json.dumps(evaluate_game24_record(json.loads(line))) + "\n")


if __name__ == "__main__":
    main()
