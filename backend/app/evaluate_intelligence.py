"""Print reproducible search, duplicate, and recommendation evaluation metrics.

Run from the backend container after importing papers and synthetic activity:
    python -m app.evaluate_intelligence --labels data/evaluation_ground_truth.json

Search qrels and duplicate pairs must be supplied by the project ground truth;
the script deliberately does not invent relevance labels.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from sqlmodel import Session
from sqlalchemy import text

from app.db import engine
from app.mining.duplicates import find_near_duplicates, pair_metrics
from app.mining.evaluation import mean_reciprocal_rank, precision_at_k
from app.routers.intel import _deduplicate_papers, _paper_rows, _tfidf_scores


def _paper_text(paper: Dict[str, Any]) -> str:
    keywords = paper.get("keywords") or ""
    if isinstance(keywords, (list, tuple)):
        keywords = " ".join(keywords)
    return " ".join(str(paper.get(key) or "") for key in ("title", "abstract", "authors")) + " " + str(keywords)


def _rank(query: str, papers: Sequence[Dict[str, Any]], expand: bool) -> List[str]:
    scores = _tfidf_scores(query, [_paper_text(paper) for paper in papers], expand=expand)
    return [str(paper["id"]) for paper, score in sorted(zip(papers, scores), key=lambda row: row[1], reverse=True)]


def _search_metrics(papers: Sequence[Dict[str, Any]], qrels_rows: Sequence[Dict[str, Any]],
                    canonical_for_id: Dict[str, str]) -> Dict[str, Dict[str, float]]:
    qrels = {
        str(row["query"]): [canonical_for_id.get(str(pid), str(pid)) for pid in row.get("relevant_paper_ids", [])]
        for row in qrels_rows
    }
    expanded: Dict[str, List[str]] = {}
    lexical: Dict[str, List[str]] = {}
    for query in qrels:
        expanded[query] = _rank(query, papers, expand=True)
        lexical[query] = _rank(query, papers, expand=False)
    result = {}
    for name, rankings in (("TF-IDF + aliases", expanded), ("TF-IDF lexical baseline", lexical)):
        result[name] = {
            "Precision@10": round(sum(precision_at_k(ranked, qrels[q], 10) for q, ranked in rankings.items()) / len(qrels), 4),
            "MRR": round(mean_reciprocal_rank(rankings, qrels), 4),
        }
    return result


def _recommendation_hit_rates(session: Session, raw_papers: Sequence[Dict[str, Any]], k: int = 10) -> Dict[str, Any]:
    papers = _deduplicate_papers(raw_papers)
    canonical_for_id: Dict[str, str] = {}
    for paper in papers:
        for member_id in paper.get("_member_ids", [str(paper["id"])]):
            canonical_for_id[str(member_id)] = str(paper["id"])
    rows = session.exec(text("SELECT user_id, paper_id, saved_at FROM saves ORDER BY saved_at, id")).all()
    by_user: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        canonical = canonical_for_id.get(str(row.paper_id))
        if canonical:
            by_user[str(row.user_id)].append(canonical)
    train: Dict[str, set[str]] = {}
    held_out: Dict[str, str] = {}
    for user_id, saved in by_user.items():
        unique = list(dict.fromkeys(saved))
        if len(unique) >= 2:
            train[user_id] = set(unique[:-1])
            held_out[user_id] = unique[-1]
    if not held_out:
        return {"co-save hit@10": None, "popular hit@10": None, "users_evaluated": 0,
                "note": "Need at least two distinct saved papers per user."}

    popular = Counter(paper_id for saved in train.values() for paper_id in saved)
    candidates = {str(paper["id"]) for paper in papers}
    co_save_hits = popular_hits = 0
    for user_id, target in held_out.items():
        own = train[user_id]
        support: Counter[str] = Counter()
        for neighbor_id, neighbor_saved in train.items():
            if neighbor_id == user_id or not own.intersection(neighbor_saved):
                continue
            support.update(neighbor_saved - own)
        co_save_ranked = sorted(candidates - own, key=lambda pid: (support[pid], popular[pid]), reverse=True)[:k]
        popular_ranked = sorted(candidates - own, key=lambda pid: popular[pid], reverse=True)[:k]
        co_save_hits += target in co_save_ranked
        popular_hits += target in popular_ranked
    n = len(held_out)
    return {"co-save hit@10": round(co_save_hits / n, 4), "popular hit@10": round(popular_hits / n, 4), "users_evaluated": n}


def _print_table(rows: Iterable[tuple[str, Dict[str, Any]]]) -> None:
    print("Metric | Result")
    print("--- | ---")
    for label, values in rows:
        if "Precision@10" in values:
            for metric, value in values.items():
                print(f"{label} {metric} | {value}")
        else:
            for metric, value in values.items():
                print(f"{label} {metric} | {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=Path("data/evaluation_ground_truth.json"))
    parser.add_argument("--duplicate-threshold", type=float, default=0.78)
    args = parser.parse_args()
    if not args.labels.exists():
        raise SystemExit(f"Missing labels file: {args.labels}. Copy data/evaluation_ground_truth.example.json and fill labels.")
    ground_truth = json.loads(args.labels.read_text(encoding="utf-8"))
    with Session(engine) as session:
        raw_papers = _paper_rows(session, deduplicate=False)
        merged_papers = _deduplicate_papers(raw_papers)
        canonical_for_id = {
            str(member_id): str(paper["id"])
            for paper in merged_papers
            for member_id in paper.get("_member_ids", [str(paper["id"])])
        }
        output = []
        qrels = ground_truth.get("search_qrels", [])
        if qrels:
            output.extend(_search_metrics(merged_papers, qrels, canonical_for_id).items())
        else:
            print("Search metrics skipped: search_qrels is empty.")

        duplicate_pairs = [tuple(map(str, pair)) for pair in ground_truth.get("duplicate_pairs", [])]
        if duplicate_pairs:
            detected = find_near_duplicates(raw_papers, threshold=args.duplicate_threshold)
            predicted = [(str(pair["paper_id_1"]), str(pair["paper_id_2"])) for pair in detected]
            output.append(("Near-duplicate detector", pair_metrics(predicted, duplicate_pairs)))
        else:
            print("Duplicate metrics skipped: duplicate_pairs is empty.")

        output.append(("Leave-one-out recommendations", _recommendation_hit_rates(session, raw_papers)))
        _print_table(output)


if __name__ == "__main__":
    main()
