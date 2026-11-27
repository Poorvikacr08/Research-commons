"""Export near-duplicate candidates for human review.

Run in the backend container from the repository root:
    docker compose exec backend python -m app.export_duplicate_candidates

The CSV is written under backend/data so it is available on the host through
the Compose backend volume mount. Abstract text is included for review.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict

from sqlmodel import Session

from app.db import engine
from app.mining.duplicates import _normalize, find_near_duplicates, jaccard, shingles
from app.routers.intel import _paper_rows


FIELDS = [
    "paper_id_1", "title_1", "doi_1", "arxiv_id_1", "source_1",
    "abstract_length_1", "abstract_1",
    "paper_id_2", "title_2", "doi_2", "arxiv_id_2", "source_2",
    "abstract_length_2", "abstract_2",
    "match_reason", "title_jaccard", "abstracts_equal_normalized",
    "abstract_jaccard",
]


def _abstract_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return round(jaccard(shingles(left), shingles(right)), 4)


def _candidate_row(candidate: Dict[str, Any], papers: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    left = papers[str(candidate["paper_id_1"])]
    right = papers[str(candidate["paper_id_2"])]
    abstract_1 = str(left.get("abstract") or "")
    abstract_2 = str(right.get("abstract") or "")
    normalized_1 = _normalize(abstract_1)
    normalized_2 = _normalize(abstract_2)
    return {
        "paper_id_1": candidate["paper_id_1"],
        "title_1": left.get("title") or "",
        "doi_1": left.get("doi") or "",
        "arxiv_id_1": left.get("arxiv_id") or "",
        "source_1": left.get("source") or "",
        "abstract_length_1": len(abstract_1),
        "abstract_1": abstract_1,
        "paper_id_2": candidate["paper_id_2"],
        "title_2": right.get("title") or "",
        "doi_2": right.get("doi") or "",
        "arxiv_id_2": right.get("arxiv_id") or "",
        "source_2": right.get("source") or "",
        "abstract_length_2": len(abstract_2),
        "abstract_2": abstract_2,
        "match_reason": candidate.get("match_reason") or "",
        "title_jaccard": candidate.get("jaccard", 0.0),
        "abstracts_equal_normalized": bool(normalized_1 and normalized_1 == normalized_2),
        "abstract_jaccard": _abstract_similarity(abstract_1, abstract_2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=0.78)
    parser.add_argument("--output", type=Path, default=Path("data/duplicate_candidate_review.csv"))
    args = parser.parse_args()

    with Session(engine) as session:
        paper_rows = _paper_rows(session, deduplicate=False)

    papers = {str(paper["id"]): paper for paper in paper_rows}
    candidates = find_near_duplicates(paper_rows, threshold=args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(_candidate_row(candidate, papers) for candidate in candidates)

    print(f"Exported {len(candidates)} candidate pairs to {args.output}.")
    print("The CSV includes full abstracts, identifiers, and title/abstract comparison fields for review.")


if __name__ == "__main__":
    main()
