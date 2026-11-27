"""Rename existing synthetic accounts without changing IDs or activity."""

import os

import psycopg

from synthetic_names import SYNTHETIC_MEMBER_NAMES


def main():
    database_url = os.environ["DATABASE_URL"].replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    expected_emails = [f"synthetic_{i:02d}@researchcommons.demo" for i in range(1, 51)]

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        users = connection.execute(
            "SELECT id, email FROM users WHERE email LIKE %s ORDER BY email",
            ("synthetic_%@researchcommons.demo",),
        ).fetchall()
        by_email = {email: user_id for user_id, email in users}
        if set(by_email) != set(expected_emails):
            raise RuntimeError(
                f"Expected the 50 known synthetic accounts; found {len(by_email)}. No names were changed."
            )

        for email, name in zip(expected_emails, SYNTHETIC_MEMBER_NAMES):
            connection.execute(
                "UPDATE users SET name = %s WHERE id = %s AND email = %s",
                (name, by_email[email], email),
            )

    print("Renamed 50 synthetic accounts; IDs, emails, and activity were preserved.")


if __name__ == "__main__":
    main()
