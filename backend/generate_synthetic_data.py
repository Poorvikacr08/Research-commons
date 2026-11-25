
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
        "duplicate_ground_truth_complete": False,
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
                "reason": "Synthetic spam test account",
                "expected_burst_posts": 30,
                "burst_window_minutes": 60,
                "expected_burst_upvotes": 30,
                "expected_burst_user_follows": 10,
                "expected_burst_topic_follows": 5
            })
        print("50 users and their interests created.")

        # --------------------------------------------------
        # 3. CREATE 600 POSTS
        # --------------------------------------------------
        print("Creating 600 posts...")
        post_ids = []
        post_tag_records = []

        # Create 450 normal posts
        for i in range(450):
            user_id = random.choice(user_ids[:45])
            topic = random.choice(TOPICS)
            title = random.choice(POST_TITLES).format(topic.title())
            body = random.choice(POST_BODIES)
            title = "[SYNTHETIC] " + title
            created_at = random_date(six_months_ago, now)

            result = conn.execute("""
                INSERT INTO posts (author_id, title, body, created_at)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (user_id, title, body, created_at))

            post_id = result.fetchone()[0]
            post_ids.append(post_id)
            post_tag_records.append((post_id, topic))

        # Create 30 burst posts for each spam account
        spam_user_ids = user_ids[45:50]
        burst_start = now - timedelta(minutes=59)

        for spam_user_id in spam_user_ids:
            for i in range(30):
                topic = "artificial intelligence"
                title = "[SYNTHETIC] Urgent research opportunity - " + topic
                body = (
                    "Repeated promotional research opportunity. "
                    "Join now for artificial intelligence research. "
                    "More information: https://example.com/research-offer"
                )
                created_at = burst_start + timedelta(
                    seconds=random.randint(0, 3540)
                )

                result = conn.execute("""
                    INSERT INTO posts (author_id, title, body, created_at)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (spam_user_id, title, body, created_at))

                post_id = result.fetchone()[0]
                post_ids.append(post_id)
                post_tag_records.append((post_id, topic))

        print("450 normal posts and 150 spam burst posts created.")


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

        # --------------------------------------------------
        # 5. CREATE REAL INTERACTIONS AND MATCHING EVENTS
        # --------------------------------------------------

        print("Creating real interactions and activity events...")

        # Create repeatable duplicate-paper evaluation records
        print("Creating duplicate-paper evaluation data...")

        duplicate_sources = [
            (
                "dedup-001",
                "f94fed40-4ff4-42db-8a12-cc12dae4b8c3",
                "Mirolo, Claudio"
            ),
            (
                "dedup-002",
                "d204891d-5351-4efa-902d-834eed99024b",
                                "Melot, Hadrien"
            ),
            (
                "dedup-003",
                "22eea3d4-03f5-4ff6-9c48-9c40c8927506",
                "Bell, Tim"
            )
        ]

        ground_truth["duplicate_paper_pairs"] = []
        ground_truth["author_name_variants"] = []

        for label, original_id, author_variant in duplicate_sources:
            source_record_id = "synthetic-dedup-" + label

            existing = conn.execute(
                "SELECT id FROM papers WHERE source_record_id = %s",
                (source_record_id,)
            ).fetchone()

            if existing:
                duplicate_id = existing[0]
            else:
                result = conn.execute(
                    """
                    INSERT INTO papers (
                        title, abstract, keywords, doi, arxiv_id, url,
                        publication_year, published_at, venue, publisher,
                        source, source_record_id
                    )
                    SELECT
                        title || ' (duplicate evaluation copy)',
                        abstract, keywords, doi, arxiv_id, url,
                        publication_year, published_at, venue, publisher,
                        'synthetic_dedup_eval', %s
                    FROM papers
                    WHERE id = %s
                    RETURNING id
                    """,
                    (source_record_id, original_id)
                )
                duplicate_id = result.fetchone()[0]

            author_exists = conn.execute(
                """
                SELECT 1 FROM paper_authors
                WHERE paper_id = %s
                LIMIT 1
                """,
                (duplicate_id,)
            ).fetchone()

            if not author_exists:
                conn.execute(
                    """
                    INSERT INTO paper_authors (
                        paper_id, author_name, normalized_name,
                        orcid, affiliation, author_position
                    )
                    SELECT
                        %s,
                        CASE WHEN author_position = 1
                             THEN %s ELSE author_name END,
                        normalized_name, orcid, affiliation,
                        author_position
                    FROM paper_authors
                    WHERE paper_id = %s
                    """,
                    (duplicate_id, author_variant, original_id)
                )

            ground_truth["duplicate_paper_pairs"].append({
                "label": label,
                "original_paper_id": str(original_id),
                "duplicate_paper_id": str(duplicate_id)
            })

            ground_truth["author_name_variants"].append({
                "original_paper_id": str(original_id),
                "duplicate_paper_id": str(duplicate_id),
                "variant": author_variant
            })

        print("Three duplicate-paper pairs prepared.")

        paper_rows = conn.execute(
            "SELECT id FROM papers"
        ).fetchall()

        paper_ids = [row[0] for row in paper_rows]

        if not paper_ids:
            raise RuntimeError("No papers found in the database.")

        event_records = []

        # Create 300 unique saves
        save_records = []
        save_pairs = set()

        while len(save_records) < 300:
            user_id = random.choice(user_ids)
            paper_id = random.choice(paper_ids)
            pair = (user_id, paper_id)

            if pair not in save_pairs:
                save_pairs.add(pair)
                created_at = random_date(six_months_ago, now)
                save_records.append((user_id, paper_id, created_at))

                event_records.append((
                    user_id, "save", "paper", paper_id,
                    None, None, created_at
                ))

        # Create 600 unique upvotes
        upvote_records = []
        upvote_pairs = set()

        while len(upvote_records) < 600:
            user_id = random.choice(user_ids)
            post_id = random.choice(post_ids)
            pair = (user_id, post_id)

            if pair not in upvote_pairs:
                upvote_pairs.add(pair)
                created_at = random_date(six_months_ago, now)
                upvote_records.append((user_id, post_id, created_at))

                event_records.append((
                    user_id, "upvote", "post", post_id,
                    None, None, created_at
                ))

        # Create 100 unique user follows
        follow_user_records = []
        follow_user_pairs = set()

        while len(follow_user_records) < 100:
            follower_id = random.choice(user_ids)
            followee_id = random.choice(user_ids)
            pair = (follower_id, followee_id)

            if follower_id != followee_id and pair not in follow_user_pairs:
                follow_user_pairs.add(pair)
                created_at = random_date(six_months_ago, now)
                follow_user_records.append((
                    follower_id, followee_id, created_at
                ))

                event_records.append((
                    follower_id, "follow", "user", followee_id,
                    None, None, created_at
                ))

        # Create 150 unique topic follows
        follow_topic_records = []
        follow_topic_pairs = set()

        while len(follow_topic_records) < 150:
            user_id = random.choice(user_ids)
            tag = random.choice(TOPICS)
            pair = (user_id, tag)

            if pair not in follow_topic_pairs:
                follow_topic_pairs.add(pair)
                created_at = random_date(six_months_ago, now)
                follow_topic_records.append((user_id, tag, created_at))

                event_records.append((
                    user_id, "follow", "topic", None,
                    tag, None, created_at
                ))
          # Create burst activity for spam accounts 46-50
        print("Creating burst interactions for spam accounts...")

        spam_user_ids = user_ids[45:50]
        burst_start = now - timedelta(minutes=59)

        for spam_user_id in spam_user_ids:

            # Exactly 30 unique upvotes within one hour
            created_count = 0
            while created_count < 30:
                post_id = random.choice(post_ids)
                pair = (spam_user_id, post_id)

                if pair not in upvote_pairs:
                    upvote_pairs.add(pair)
                    created_at = burst_start + timedelta(
                        seconds=random.randint(0, 3540)
                    )
                    upvote_records.append((
                        spam_user_id, post_id, created_at
                    ))
                    event_records.append((
                        spam_user_id, "upvote", "post", post_id,
                        None, None, created_at
                    ))
                    created_count += 1

            # Exactly 10 unique user follows within one hour
            created_count = 0
            while created_count < 10:
                followee_id = random.choice(user_ids[:45])
                pair = (spam_user_id, followee_id)

                if pair not in follow_user_pairs:
                    follow_user_pairs.add(pair)
                    created_at = burst_start + timedelta(
                        seconds=random.randint(0, 3540)
                    )
                    follow_user_records.append((
                        spam_user_id, followee_id, created_at
                    ))
                    event_records.append((
                        spam_user_id, "follow", "user", followee_id,
                        None, None, created_at
                    ))
                    created_count += 1

            # Exactly 5 unique topic follows within one hour
            created_count = 0
            while created_count < 5:
                tag = random.choice(TOPICS)
                pair = (spam_user_id, tag)

                if pair not in follow_topic_pairs:
                    follow_topic_pairs.add(pair)
                    created_at = burst_start + timedelta(
                        seconds=random.randint(0, 3540)
                    )
                    follow_topic_records.append((
                        spam_user_id, tag, created_at
                    ))
                    event_records.append((
                        spam_user_id, "follow", "topic", None,
                        tag, None, created_at
                    ))
                    created_count += 1
        # Insert actual interaction records
        conn.cursor().executemany(
            """
            INSERT INTO saves (user_id, paper_id, saved_at)
            VALUES (%s, %s, %s)
            """,
            save_records
        )

        conn.cursor().executemany(
            """
            INSERT INTO upvotes (user_id, post_id, created_at)
            VALUES (%s, %s, %s)
            """,
            upvote_records
        )

        conn.cursor().executemany(
            """
            INSERT INTO follow_users (follower_id, followee_id, created_at)
            VALUES (%s, %s, %s)
            """,
            follow_user_records
        )

        conn.cursor().executemany(
            """
            INSERT INTO follow_topics (user_id, tag, created_at)
            VALUES (%s, %s, %s)
            """,
            follow_topic_records
        )

        print(
            f"{len(save_records)} saves, "
            f"{len(upvote_records)} upvotes, "
            f"{len(follow_user_records)} user follows and "
            f"{len(follow_topic_records)} topic follows created."
        )
        # Create 12000 normal view/search events
        print("Creating 12000 activity events...")

        for i in range(12000):
            user_id = random.choice(user_ids)
            event_type = random.choice(["view", "search"])

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

            else:
                target_type = "topic"
                target_tag = random.choice(TOPICS)
                query_text = random.choice(SEARCH_QUERIES)

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

        # Add a concentrated AI topic spike
        latest_7_days_start = now - timedelta(days=7)
        previous_7_days_start = now - timedelta(days=14)

        # 700 AI searches in the latest 7 days
        for i in range(700):
            event_records.append((
                random.choice(user_ids),
                "search",
                "topic",
                None,
                "artificial intelligence",
                "artificial intelligence research",
                random_date(latest_7_days_start, now)
            ))

        # 50 AI searches in the previous 7 days
        for i in range(50):
            event_records.append((
                random.choice(user_ids),
                "search",
                "topic",
                None,
                "artificial intelligence",
                "artificial intelligence research",
                random_date(previous_7_days_start, latest_7_days_start)
            ))
        # Insert all events, including matching interaction events
        conn.cursor().executemany(
            """
            INSERT INTO events
            (user_id, event_type, target_type, target_id,
             target_tag, query_text, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            event_records
        )

        print(f"{len(event_records)} activity events created.")


        # --------------------------------------------------
        # 6. SAVE GROUND TRUTH
        # --------------------------------------------------

        # Add query-specific search relevance evaluation labels
        relevance_queries = [
            ("Abstraction in Computer Science Education", 0),
            ("Academic Writing in Computer Science", 1),
            ("A Case Study of the Introduction of Computer Science in NZ Schools", 2)
        ]

        ground_truth["search_relevance_labels"] = []

        for query, relevant_index in relevance_queries:
            documents = []

            for index, pair in enumerate(
                ground_truth["duplicate_paper_pairs"]
            ):
                score = 2 if index == relevant_index else 0

                documents.append({
                    "paper_id": pair["original_paper_id"],
                    "relevance": score
                })

                documents.append({
                    "paper_id": pair["duplicate_paper_id"],
                    "relevance": score
                })

            ground_truth["search_relevance_labels"].append({
                "query": query,
                "relevant_documents": documents
            })
        # Record the known AI topic spike for trend evaluation
        ground_truth["topic_spikes"] = [
            {
                "topic": "artificial intelligence",
                "comparison": "latest 7 days vs previous 7 days",
                "latest_7_days_injected_events": 700,
                "previous_7_days_injected_events": 50,
                "expected_increase_ratio": 14,
                "description": "Synthetic AI search activity concentrated in the latest 7 days"
            }
        ]

        ground_truth["record_counts"] = {
            "users": 50,
            "posts": 600,
            "comments": 1600,
            "events": len(event_records),
            "user_interests": len(interests),
            "post_tags": len(post_tag_records),
            "saves": len(save_records),
            "upvotes": len(upvote_records),
            "follow_users": len(follow_user_records),
            "follow_topics": len(follow_topic_records)
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
