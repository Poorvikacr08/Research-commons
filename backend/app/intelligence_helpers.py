"""Small pure helpers for search result partitioning and grounded answers."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

MAX_ANSWER_EXCERPT = 320


def paper_member_ids(paper: Dict[str, Any]) -> List[str]:
    return [str(paper_id) for paper_id in (paper.get("_member_ids") or [paper["id"]])]


def is_catalog_description(paper: Dict[str, Any]) -> bool:
    """Identify obvious journal, proceedings, and publisher descriptions, not article abstracts."""
    abstract = " ".join(str(paper.get("abstract") or "").lower().split())
    patterns = (
        r"\bwelcomes papers and articles\b",
        r"\bwe are primarily interested in presenting\b",
        r"\bauthors are invited to contribute\b",
        r"\bsubmissions underwent\b.{0,100}\bpeer review\b",
        r"\bcall for papers\b",
        r"\b(?:open access|peer[- ]reviewed)?\s*journal\b.{0,80}\b(?:publishes|publication|aims|articles)\b",
        r"\bconference(?:s)?\b.{0,180}\b(?:attracted|brought together|collocated)\b",
        r"\bthis series is for people\b",
        r"\bfrom the publisher:",
    )
    return any(re.search(pattern, abstract) for pattern in patterns)


def partition_paper_results(
    ranked_papers: Sequence[Tuple[Dict[str, Any], float]],
    save_counts: Dict[str, int],
    limit: int,
) -> Tuple[List[Tuple[Dict[str, Any], float]], List[Tuple[Dict[str, Any], float]]]:
    """Put each deduplicated paper in either the public papers or library panel."""
    library, public = [], []
    for paper, score in ranked_papers:
        if any(paper_id in save_counts for paper_id in paper_member_ids(paper)):
            library.append((paper, score))
        else:
            public.append((paper, score))
    return public[:limit], library[:limit]


def select_evidence_findings(findings: Sequence[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    """Choose the strongest distinct retrieved sentences for the answer."""
    selected = []
    seen = set()
    for finding in sorted(findings, key=lambda row: float(row.get("score", 0)), reverse=True):
        sentence = " ".join(str(finding.get("text") or "").split())
        key = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
        if not sentence or not key or key in seen:
            continue
        seen.add(key)
        selected.append(finding)
        if len(selected) >= limit:
            break
    return selected


def compose_evidence_answer(findings: Sequence[Dict[str, Any]], limit: int = 3) -> str:
    """Format distinct retrieved sentences as concise, numbered evidence points."""
    selected = select_evidence_findings(findings, limit)
    if not selected:
        return "I couldn't find a relevant passage in the papers currently stored in the library. Try a more specific research question."
    lines = ["The most relevant papers point to these findings:"]
    for finding in selected:
        sentence = " ".join(str(finding["text"]).split())
        if len(sentence) > MAX_ANSWER_EXCERPT:
            sentence = sentence[:MAX_ANSWER_EXCERPT - 3].rsplit(" ", 1)[0] + "..."
        lines.append(f"• {sentence} [{finding['n']}]")
    return "\n\n".join(lines)
