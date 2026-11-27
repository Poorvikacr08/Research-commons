import unittest

from synthetic_names import SYNTHETIC_MEMBER_NAMES


class SyntheticMemberNamesTests(unittest.TestCase):
    def test_has_50_unique_names(self):
        self.assertEqual(50, len(SYNTHETIC_MEMBER_NAMES))
        self.assertEqual(50, len(set(SYNTHETIC_MEMBER_NAMES)))

    def test_no_placeholder_demo_member_names_remain(self):
        self.assertTrue(all("Demo Member" not in name for name in SYNTHETIC_MEMBER_NAMES))


if __name__ == "__main__":
    unittest.main()
