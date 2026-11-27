import unittest

from app.intelligence_helpers import compose_evidence_answer, is_catalog_description, partition_paper_results, select_evidence_findings


class SearchPanelPartitionTests(unittest.TestCase):
    def test_saved_and_unsaved_papers_appear_in_only_one_panel(self):
        saved = {"id": "canonical", "_member_ids": ["canonical", "duplicate"]}
        unsaved = {"id": "other", "_member_ids": ["other"]}

        public, library = partition_paper_results(
            [(saved, 0.9), (unsaved, 0.8)], {"duplicate": 2}, limit=10
        )

        self.assertEqual([paper["id"] for paper, _ in public], ["other"])
        self.assertEqual([paper["id"] for paper, _ in library], ["canonical"])

    def test_each_panel_obeys_its_own_limit(self):
        ranked = [({"id": f"p{i}"}, 1 - i / 10) for i in range(4)]
        public, library = partition_paper_results(ranked, {"p1": 1, "p3": 2}, limit=1)

        self.assertEqual([paper["id"] for paper, _ in public], ["p0"])
        self.assertEqual([paper["id"] for paper, _ in library], ["p1"])


class EvidenceAnswerTests(unittest.TestCase):
    def test_journal_and_proceedings_descriptions_are_excluded_from_ask(self):
        self.assertTrue(is_catalog_description({
            "abstract": "The journal publishes original research articles in computer science."
        }))
        self.assertTrue(is_catalog_description({
            "abstract": "The conferences attracted many local and international delegates."
        }))
        self.assertTrue(is_catalog_description({
            "abstract": "We are primarily interested in presenting theoretical research papers."
        }))
        self.assertFalse(is_catalog_description({
            "abstract": "We present a machine learning method and evaluate it on three datasets."
        }))

    def test_answer_is_readable_and_deduplicates_repeated_passages(self):
        answer = compose_evidence_answer([
            {"n": 1, "text": "Machine learning supports useful models.", "score": 0.8},
            {"n": 2, "text": "Machine learning supports useful models.", "score": 0.7},
            {"n": 3, "text": "A second paper describes a related method.", "score": 0.6},
        ])

        self.assertIn("The most relevant papers point to these findings:", answer)
        self.assertIn("• Machine learning supports useful models. [1]", answer)
        self.assertIn("• A second paper describes a related method. [3]", answer)
        self.assertEqual(answer.count("Machine learning supports useful models."), 1)

    def test_selected_findings_are_distinct_and_capped(self):
        selected = select_evidence_findings([
            {"n": 1, "text": "First finding is supported by a source.", "score": 0.9},
            {"n": 2, "text": "Second finding is supported by another source.", "score": 0.8},
            {"n": 3, "text": "Third finding is also relevant to this question.", "score": 0.7},
            {"n": 4, "text": "Fourth finding is also relevant to this question.", "score": 0.6},
        ], limit=3)
        self.assertEqual([row["n"] for row in selected], [1, 2, 3])

    def test_long_abstract_sentence_is_shortened_in_answer(self):
        long_sentence = "A relevant result " + ("with supporting detail " * 30)
        answer = compose_evidence_answer([{"n": 1, "text": long_sentence, "score": 0.9}])

        self.assertLessEqual(len(answer.split("• ", 1)[1].rsplit(" [1]", 1)[0]), 320)
        self.assertTrue(answer.endswith("... [1]"))

    def test_empty_evidence_returns_a_limited_library_message(self):
        self.assertIn("couldn't find a relevant passage", compose_evidence_answer([]))


if __name__ == "__main__":
    unittest.main()
