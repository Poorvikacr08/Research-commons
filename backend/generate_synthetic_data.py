
import os
import json
import random
from datetime import datetime, timedelta, timezone

import bcrypt
import psycopg


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

random.seed(42)

DATABASE_URL = os.environ["DATABASE_URL"]
DATABASE_URL = DATABASE_URL.replace(
    "postgresql+psycopg://",
    "postgresql://",
    1
)

EMAIL_PREFIX = "synthetic_"
PASSWORD = "Demo@123"

DEPARTMENTS = [
    "Computer Science",
    "Information Technology",
    "Electronics",
    "Mechanical Engineering",
    "Business Management",
    "Mathematics"
]

TOPICS = [
    "artificial intelligence",
    "machine learning",
    "data science",
    "cybersecurity",
    "cloud computing",
    "software engineering",
    "blockchain",
    "computer networks",
    "deep learning",
    "natural language processing"
]

POST_TITLES = [
    "Research discussion on {}",
    "Latest developments in {}",
    "Challenges and opportunities in {}",
    "How can we improve {} research?",
    "Interesting findings about {}",
    "Looking for collaborators in {}",
    "A beginner's guide to {}",
    "Future scope of {}"
]

POST_BODIES = [
    "I am exploring this research area and would like to discuss recent developments and useful resources.",
    "What are the major challenges in this field? Share your thoughts and research experiences.",
    "I found this topic interesting and would like to connect with students working in this area.",
    "Can anyone suggest useful papers, datasets, or tools related to this topic?",
    "Let's discuss possible research applications and future directions in this area."
]

COMMENT_TEXTS = [
    "This is an interesting research direction.",
    "I agree. There is still a lot of scope for further study.",
    "Thanks for sharing this information.",
    "I would recommend exploring some recent research papers.",
    "This could be useful for our project.",
    "Can you share more details about your approach?",
    "I have worked on a similar topic.",
    "Good point. We should investigate this further.",
    "This is a useful resource for beginners.",
    "I would like to collaborate on this topic."
]

SEARCH_QUERIES = [
    "artificial intelligence research",
    "machine learning papers",
    "cybersecurity trends",
    "data science applications",
    "cloud computing research",
    "deep learning methods",
    "software engineering education",
    "natural language processing"
]


def random_date(start, end):
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, max(seconds, 1)))


def main():
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=183)

    ground_truth = {
        "description": "Synthetic test data for Chanakya Research Commons",
        "generated_at": now.isoformat(),
        "synthetic_email_prefix": EMAIL_PREFIX,
        "test_password": PASSWORD,
        "spam_accounts": [],
        "topic_spikes": [
            {
                "topic": "artificial intelligence",
                "period": "last 14 days",
                "description": "Concentrated synthetic activity for trend detection testing"
            }
        ],
        "record_counts": {}
    }

    print("Connecting to PostgreSQL...")

    with psycopg.connect(DATABASE_URL) as conn:

        # --------------------------------------------------
        # 1. REMOVE ONLY OUR PREVIOUS SYNTHETIC DATA
        # --------------------------------------------------

        print("Cleaning previous synthetic records...")

        conn.execute(
            """
            DELETE FROM events
            WHERE user_id IN (
                SELECT id FROM users
                WHERE email LIKE %s
            )
            """,
            (EMAIL_PREFIX + "%",)
        )

        conn.execute(
            """
            DELETE FROM users
            WHERE email LIKE %s
            """,
            (EMAIL_PREFIX + "%",)
        )

        # Existing non-synthetic users and papers are untouched.

        # --------------------------------------------------
        # 2. CREATE 50 SYNTHETIC USERS
        # --------------------------------------------------

        print("Creating 50 synthetic members...")

        password_hash = bcrypt.hashpw(
            PASSWORD.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        users = []
        interests = []

        for i in range(1, 51):

            department = DEPARTMENTS[(i - 1) % len(DEPARTMENTS)]

            if i <= 5:
                role = "faculty"
            elif i <= 10:
                role = "researcher"
            else:
                role = "student"

            name = f"Demo Member {i:02d}"
            email = f"{EMAIL_PREFIX}{i:02d}@researchcommons.demo"

            bio = (
                f"Synthetic demo profile interested in "
                f"{department} research."
            )

            users.append((
                name,
                email,
                password_hash,
                role,
                department,
                bio,
                None
            ))

        user_ids = []

        for user in users:
            result = conn.execute(
                """
                INSERT INTO users
                (name, email, password_hash, role, department, bio, links)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                user
            )
            user_ids.append(result.fetchone()[0])

        for user_id in user_ids:
            selected_topics = random.sample(TOPICS, 3)

            for topic in selected_topics:
                interests.append((user_id, topic))

        conn.cursor().executemany(
            """
            INSERT INTO user_interests (user_id, tag)
            VALUES (%s, %s)
            """,
            interests
        )

        # Five accounts are marked as spam in the separate ground truth.
        for i in range(46, 51):
            ground_truth["spam_accounts"].append({
                "email": f"{EMAIL_PREFIX}{i:02d}@researchcommons.demo",
                "reason": "Synthetic spam test account"
            })

        print("50 users and their interests created.")

        # --------------------------------------------------
        # 3. CREATE 600 POSTS
        # --------------------------------------------------

        print("Creating 600 posts...")

        post_ids = []
        post_tag_records = []

        for i in range(600):

            user_id = random.choice(user_ids)
            topic = random.choice(TOPICS)

            title = random.choice(POST_TITLES).format(topic.title())
            body = random.choice(POST_BODIES)

            # Clearly identify synthetic records.
            title = "[SYNTHETIC] " + title

            created_at = random_date(six_months_ago, now)

            result = conn.execute(
                """
                INSERT INTO posts
                (author_id, title, body, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, title, body, created_at)
            )

            post_id = result.fetchone()[0]
            post_ids.append(post_id)

            post_tag_records.append((post_id, topic))

        conn.cursor().executemany(
            """
            INSERT INTO post_tags (post_id, tag)
            VALUES (%s, %s)
            """,
            post_tag_records
        )

        print("600 posts created.")

        # --------------------------------------------------
        # 4. CREATE 1600 COMMENTS
        # --------------------------------------------------

        print("Creating 1600 comments...")

        comment_ids = []

        for i in range(1600):

            post_id = random.choice(post_ids)
            author_id = random.choice(user_ids)
            body = random.choice(COMMENT_TEXTS)
            created_at = random_date(six_months_ago, now)

            parent_id = None

            # Some comments are replies to earlier comments.
            if comment_ids and random.random() < 0.15:
                parent_id = random.choice(comment_ids)

            result = conn.execute(
                """
                INSERT INTO comments
                (post_id, author_id, parent_id, body, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (post_id, author_id, parent_id, body, created_at)
            )

            comment_ids.append(result.fetchone()[0])

        print("1600 comments created.")

        # --------------------------------------------------
        # 5. CREATE 12000 ACTIVITY EVENTS
        # --------------------------------------------------

        print("Creating 12000 activity events...")

        paper_rows = conn.execute(
            "SELECT id FROM papers"
        ).fetchall()

        paper_ids = [row[0] for row in paper_rows]

        if not paper_ids:
            raise RuntimeError("No papers found in the database.")

        event_records = []

        event_types = [
            "view",
            "search",
            "save"
        ]

        for i in range(12000):

            user_id = random.choice(user_ids)
            event_type = random.choice(event_types)

            target_type = None
            target_id = None
            target_tag = None
            query_text = None

            if event_type == "view":
                target_type = random.choice(["paper", "post"])

                if target_type == "paper":
                    target_id = random.choice(paper_ids)
                else:
                    target_id = random.choice(post_ids)

            elif event_type == "search":
                target_type = "topic"
                target_tag = random.choice(TOPICS)
                query_text = random.choice(SEARCH_QUERIES)

            elif event_type == "save":
                target_type = "paper"
                target_id = random.choice(paper_ids)

            elif event_type == "follow":
                target_type = random.choice(["topic", "user"])

                if target_type == "topic":
                    target_tag = random.choice(TOPICS)
                else:
                    target_id = random.choice(user_ids)

            elif event_type in ["post", "comment", "upvote"]:
                target_type = "post"
                target_id = random.choice(post_ids)

            created_at = random_date(six_months_ago, now)

            event_records.append((
                user_id,
                event_type,
                target_type,
                target_id,
                target_tag,
                query_text,
                created_at
            ))

        # Add 700 concentrated AI topic events in the last 14 days.
        # This creates a deliberate topic spike for trend detection.
        for i in range(700):

            event_records.append((
                random.choice(user_ids),
                "search",
                "topic",
                None,
                "artificial intelligence",
                "artificial intelligence research",
                random_date(now - timedelta(days=14), now)
            ))

        conn.cursor().executemany(
            """
            INSERT INTO events
            (user_id, event_type, target_type, target_id,
             target_tag, query_text, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            event_records
        )

        print("12700 activity events created.")

        # --------------------------------------------------
        # 6. SAVE GROUND TRUTH
        # --------------------------------------------------

        ground_truth["record_counts"] = {
            "users": 50,
            "posts": 600,
            "comments": 1600,
            "events": 12700,
            "user_interests": len(interests),
            "post_tags": len(post_tag_records)
        }

        os.makedirs("data", exist_ok=True)

        with open(
            "data/synthetic_ground_truth.json",
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(ground_truth, file, indent=4)

        print("\nAll synthetic records inserted successfully!")

    print("\nGROUND TRUTH FILE:")
    print("data/synthetic_ground_truth.json")

    print("\nDEMO LOGIN:")
    print("Password for all synthetic accounts:", PASSWORD)

    print("\nExample accounts:")
    print("synthetic_01@researchcommons.demo")
    print("synthetic_02@researchcommons.demo")

    print("\nExisting research papers were preserved.")


if __name__ == "__main__":
    main()
