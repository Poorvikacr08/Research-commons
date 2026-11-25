import unittest

from app.mining.duplicates import find_near_duplicates


class DuplicateDetectionTests(unittest.TestCase):
    def test_exact_abstract_finds_title_variant_without_identifiers(self):
        abstract = (
            "This paper describes methods for academic writing in computer science. "
            "It reviews structure, evidence, citation practice, revision, and clarity. "
        ) * 5
        papers = [
            {
                "id": "original",
                "title": "Academic Writing in Computer Science",
                "abstract": abstract,
                "doi": None,
                "arxiv_id": None,
            },
            {
                "id": "copy",
                "title": "Academic Writing in Computer Science (duplicate evaluation copy)",
                "abstract": abstract,
                "doi": None,
                "arxiv_id": None,
            },
        ]

        matches = find_near_duplicates(papers)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["match_reason"], "exact_abstract")


if __name__ == "__main__":
    unittest.main()
