"""Normalize the evaluation label formats accepted by the project."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def normalize_ground_truth(ground_truth: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """Return evaluator-format query relevance rows and duplicate ID pairs.

    Supports the evaluator example schema as well as Member 2's synthetic
    generator schema. Positive graded relevance values count as relevant for
    Precision@10 and MRR.
    """
    qrels = ground_truth.get("search_qrels") or []
    if not qrels:
        qrels = []
        for row in ground_truth.get("search_relevance_labels") or []:
            relevant_ids = []
            for document in row.get("relevant_documents") or []:
                if isinstance(document, dict):
                    if float(document.get("relevance", 0) or 0) > 0 and document.get("paper_id"):
                        relevant_ids.append(str(document["paper_id"]))
                elif document:
                    relevant_ids.append(str(document))
            if row.get("query") and relevant_ids:
                qrels.append({"query": str(row["query"]), "relevant_paper_ids": relevant_ids})

    pairs = ground_truth.get("duplicate_pairs") or []
    if not pairs:
        pairs = [
            (str(row["original_paper_id"]), str(row["duplicate_paper_id"]))
            for row in ground_truth.get("duplicate_paper_pairs") or []
            if row.get("original_paper_id") and row.get("duplicate_paper_id")
        ]
    else:
        pairs = [tuple(map(str, pair)) for pair in pairs if len(pair) == 2]

    return list(qrels), list(pairs)
