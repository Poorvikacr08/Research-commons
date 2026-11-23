"""
Password hashing for Chanakya Research Commons.

Used by the app (register / login) and by Member 2's synthetic data
generator, so fake users can log in with a known demo password.

Install:  pip install bcrypt
"""
import bcrypt


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash to store in users.password_hash."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a login password against the stored hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


if __name__ == "__main__":
    h = hash_password("Demo@123")
    print("hash:", h)
    print("correct password ->", verify_password("Demo@123", h))
    print("wrong password   ->", verify_password("wrong", h))
