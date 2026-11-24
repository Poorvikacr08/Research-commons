"""Near-duplicate paper detection with MinHash, LSH, and exact Jaccard checks."""
from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Sequence, Set, Tuple


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def shingles(text: str, width: int = 5) -> Set[str]:
    """Character shingles tolerate small edits, punctuation, and title variants."""
    normalized = _normalize(text)
    if not normalized:
        return set()
    padded = f"  {normalized}  "
    if len(padded) <= width:
        return {padded}
    return {padded[i:i + width] for i in range(len(padded) - width + 1)}


def jaccard(left: Set[str], right: Set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _signature(values: Set[str], num_perm: int) -> Tuple[int, ...]:
    if not values:
        return tuple([2**64 - 1] * num_perm)
    signature = []
    for seed in range(num_perm):
        min_hash = min(
            int.from_bytes(hashlib.blake2b(f"{seed}:{value}".encode("utf-8"), digest_size=8).digest(), "big")
            for value in values
        )
        signature.append(min_hash)
    return tuple(signature)


def find_near_duplicates(
    papers: Sequence[Dict[str, str]],
    threshold: float = 0.78,
    num_perm: int = 64,
    bands: int = 16,
) -> List[Dict[str, object]]:
    """Return candidate pairs whose exact title-shingle Jaccard meets threshold.

    LSH narrows the comparisons; exact Jaccard is always used for the final flag.
    The deterministic hash makes results reproducible across runs and machines.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if num_perm < 1 or bands < 1 or bands > num_perm or num_perm % bands:
        raise ValueError("num_perm must be positive and divisible by bands")
    prepared = []
    for paper in papers:
        title = str(paper.get("title") or "")
        text = f"{title} {title}"  # title weight reduces matches on generic short phrases
        prepared.append((str(paper.get("id", "")), title, shingles(text)))
    signatures = [_signature(item[2], num_perm) for item in prepared]
    rows_per_band = num_perm // bands
    buckets: Dict[Tuple[int, Tuple[int, ...]], List[int]] = {}
    candidates: Set[Tuple[int, int]] = set()
    for index, signature in enumerate(signatures):
        for band in range(bands):
            start = band * rows_per_band
            key = (band, signature[start:start + rows_per_band])
            for other in buckets.get(key, []):
                candidates.add((other, index))
            buckets.setdefault(key, []).append(index)

    results = []
    for left_index, right_index in sorted(candidates):
        left_id, left_title, left_shingles = prepared[left_index]
        right_id, right_title, right_shingles = prepared[right_index]
        if not left_id or not right_id or left_id == right_id:
            continue
        similarity = jaccard(left_shingles, right_shingles)
        if similarity >= threshold:
            results.append({
                "paper_id_1": left_id,
                "title_1": left_title,
                "paper_id_2": right_id,
                "title_2": right_title,
                "jaccard": round(similarity, 4),
            })
    return sorted(results, key=lambda item: float(item["jaccard"]), reverse=True)


def pair_metrics(predicted: Iterable[Tuple[str, str]], truth: Iterable[Tuple[str, str]]) -> Dict[str, float | int]:
    """Precision/recall/F1 for a predicted duplicate-pair set and labeled truth."""
    normalize = lambda pairs: {tuple(sorted((str(a), str(b)))) for a, b in pairs if str(a) != str(b)}
    predicted_set, truth_set = normalize(predicted), normalize(truth)
    true_positive = len(predicted_set & truth_set)
    precision = true_positive / len(predicted_set) if predicted_set else 0.0
    recall = true_positive / len(truth_set) if truth_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": true_positive,
        "false_positive": len(predicted_set - truth_set),
        "false_negative": len(truth_set - predicted_set),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }

