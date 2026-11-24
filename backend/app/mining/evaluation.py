"""Ranking metrics for the Member 3 evaluation notebook/script."""
from typing import Dict, Iterable, Mapping, Sequence, Set


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int = 10) -> float:
    relevant: Set[str] = {str(x) for x in relevant_ids}
    top = [str(x) for x in ranked_ids[:max(1, k)]]
    return sum(item in relevant for item in top) / len(top) if top else 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int = 10) -> float:
    relevant: Set[str] = {str(x) for x in relevant_ids}
    if not relevant:
        return 0.0
    top = {str(x) for x in ranked_ids[:max(1, k)]}
    return len(top & relevant) / len(relevant)


def mean_reciprocal_rank(rankings: Mapping[str, Sequence[str]], qrels: Mapping[str, Iterable[str]]) -> float:
    """Mean reciprocal rank across query -> ranked IDs and query -> relevant IDs."""
    reciprocal_ranks = []
    for query, ranked_ids in rankings.items():
        relevant = {str(x) for x in qrels.get(query, [])}
        reciprocal = 0.0
        for rank, item_id in enumerate(ranked_ids, start=1):
            if str(item_id) in relevant:
                reciprocal = 1.0 / rank
                break
        reciprocal_ranks.append(reciprocal)
    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
