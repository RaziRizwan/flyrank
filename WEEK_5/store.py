"""
store.py -- Stage 4 & 5. Writing the three output files. Nothing else in this project
touches output/ directly, so the file layout only has to be right in one place.
"""
import json
from pathlib import Path

OUTPUT_DIR = Path("output")


def write_books(records: list[dict]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "books.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def write_errors(errors: list[dict]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


def write_report(report: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
