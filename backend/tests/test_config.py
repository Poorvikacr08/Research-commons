import unittest

from app.config import load_jwt_secret


class JwtSecretConfigurationTests(unittest.TestCase):
    def test_accepts_long_private_value(self):
        secret = "a" * 48
        self.assertEqual(secret, load_jwt_secret({"JWT_SECRET": secret}))

    def test_rejects_missing_value(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
            load_jwt_secret({})

    def test_rejects_known_development_default(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
            load_jwt_secret({"JWT_SECRET": "dev-only-secret-change-me"})

    def test_rejects_example_placeholder(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
            load_jwt_secret({"JWT_SECRET": "replace_with_a_long_random_secret"})

    def test_rejects_short_value(self):
        with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
            load_jwt_secret({"JWT_SECRET": "too-short"})


if __name__ == "__main__":
    unittest.main()
