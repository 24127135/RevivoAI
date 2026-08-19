from collections.abc import Iterable
import csv
from pathlib import Path
from typing import Dict, List, Union

POSITIVE_WORDS: set[str] = {"growth", "profit", "improved", "strong", "exceeded"}
NEGATIVE_WORDS: set[str] = {"loss", "decline", "weak", "litigation", "restated"}


def load_lexicon_counts(report_text: str) -> dict[str, int]:
    tokens = report_text.lower().split()
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    return {"positive": pos, "negative": neg}


def sentiment_score(report_text: str) -> float:
    counts = load_lexicon_counts(report_text)
    total = counts["positive"] + counts["negative"]
    if total == 0:
        return 0.0
    return (counts["positive"] - counts["negative"]) / total


def score_filing_batch(filing_paths: Iterable[Union[str, Path]]) -> list[dict[str, Union[str, float]]]:
    rows: list[dict[str, Union[str, float]]] = []
    for path in filing_paths:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        rows.append({"path": str(path), "lm_score": sentiment_score(text)})
    return rows


def export_csv(rows: list[dict[str, Union[str, float]]], out_path: Union[str, Path]) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "lm_score"])
        writer.writeheader()
        writer.writerows(rows)
