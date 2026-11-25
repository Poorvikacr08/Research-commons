import json
import unittest
from pathlib import Path

from app.evaluation_labels import normalize_ground_truth


class GroundTruthNormalizationTests(unittest.TestCase):
    def test_member_two_synthetic_labels_are_adapted(self):
        path = Path(__file__).resolve().parents[1] / "data" / "synthetic_ground_truth.json"
        ground_truth = json.loads(path.read_text(encoding="utf-8"))
        qrels, pairs = normalize_ground_truth(ground_truth)

        self.assertEqual(len(pairs), len(ground_truth["duplicate_paper_pairs"]))
        self.assertEqual(len(qrels), len(ground_truth["search_relevance_labels"]))
        self.assertTrue(all(len(pair) == 2 for pair in pairs))
        self.assertTrue(all(row["relevant_paper_ids"] for row in qrels))

    def test_graded_relevance_keeps_only_positive_labels(self):
        qrels, pairs = normalize_ground_truth({
            "search_relevance_labels": [{
                "query": "graphs",
                "relevant_documents": [
                    {"paper_id": "paper-a", "relevance": 2},
                    {"paper_id": "paper-b", "relevance": 0},
                ],
            }],
            "duplicate_paper_pairs": [{"original_paper_id": "a", "duplicate_paper_id": "b"}],
        })

        self.assertEqual(qrels, [{"query": "graphs", "relevant_paper_ids": ["paper-a"]}])
        self.assertEqual(pairs, [("a", "b")])

    def test_evaluator_example_schema_stays_supported(self):
        qrels, pairs = normalize_ground_truth({
            "search_qrels": [{"query": "graphs", "relevant_paper_ids": ["a"]}],
            "duplicate_pairs": [["a", "b"]],
        })
        self.assertEqual(qrels[0]["relevant_paper_ids"], ["a"])
        self.assertEqual(pairs, [("a", "b")])


if __name__ == "__main__":
    unittest.main()
