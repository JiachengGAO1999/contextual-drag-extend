from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, Iterator


def normalize_rows(rows: Iterable[Dict[str, object]], source: str, revision: str) -> Iterator[Dict[str, object]]:
    for index, row in enumerate(rows):
        raw = row.get("numbers", row.get("answer", row.get("Puzzles", row.get("puzzle", row.get("problem")))))
        if isinstance(raw, str):
            numbers = [int(value) for value in raw.replace(",", " ").split()]
        elif isinstance(raw, (list, tuple)):
            numbers = [int(value) for value in raw]
        else:
            raise ValueError(f"row {index} has no recognizable numbers")
        if len(numbers) != 4:
            raise ValueError(f"row {index} does not contain four numbers")
        yield {
            "id": str(row.get("id", index)),
            "problem": str(row.get("problem", f"Use {numbers} exactly once to make 24.")),
            "answer": numbers,
            "dataset_provenance": {"source": source, "revision": revision, "source_row": index},
        }


def read_rows(path: Path) -> Iterator[Dict[str, object]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)
    else:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build official-compatible Game24 JSONL from a local source; never downloads implicitly.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in normalize_rows(read_rows(args.input), args.source, args.revision):
            handle.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
