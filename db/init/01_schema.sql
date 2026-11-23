-- =====================================================================
-- Chanakya Research Commons - Application database (Member 1: F1-F3)
-- PostgreSQL 13+   |   UUID primary keys   |   timestamps in UTC
-- The `papers` table is owned by Member 2 (ingestion). This file only
-- references paper_id; the foreign keys to papers are at the bottom.
-- =====================================================================

-- ---------- F1: accounts and profiles ----------
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT        NOT NULL,
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    role          TEXT        NOT NULL DEFAULT 'student'
                  CHECK (role IN ('student', 'faculty', 'researcher', 'admin')),
    department    TEXT,
    bio           TEXT,
    links         TEXT,                       -- publications / personal page
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_interests (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (user_id, tag)
);

CREATE TABLE follow_users (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id),
    CHECK (follower_id <> followee_id)
);

CREATE TABLE follow_topics (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tag)
);

-- ---------- F2: posts and discussions ----------
CREATE TABLE posts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE post_tags (
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (post_id, tag)
);

CREATE TABLE post_papers (
    post_id  UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    paper_id UUID NOT NULL,                  -- FK to papers(id) at bottom
    PRIMARY KEY (post_id, paper_id)
);

CREATE TABLE comments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id  UUID REFERENCES comments(id) ON DELETE CASCADE,  -- NULL = top-level, else reply
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE upvotes (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id    UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, post_id)            -- one upvote per user per post
);

-- ---------- F3: library ----------
CREATE TABLE saves (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id UUID NOT NULL,                   -- FK to papers(id) at bottom
    saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, paper_id)                -- one save per user per paper
);

CREATE TABLE collections (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE collection_items (
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    paper_id      UUID NOT NULL,              -- FK to papers(id) at bottom
    note          TEXT,                       -- private note
    added_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (collection_id, paper_id)
);

-- "Saved by N members" for the Chanakya library
CREATE VIEW library_save_counts AS
SELECT paper_id, COUNT(*) AS save_count, MAX(saved_at) AS last_saved_at
FROM saves
GROUP BY paper_id;

-- ---------- Activity log (used by Member 2 analytics + Member 3 mining) ----------
CREATE TABLE events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    event_type  TEXT NOT NULL
                CHECK (event_type IN ('view', 'search', 'save', 'follow', 'post', 'comment', 'upvote')),
    target_type TEXT
                CHECK (target_type IN ('paper', 'post', 'user', 'topic')),
    target_id   UUID,                         -- paper/post/user id (NULL for topic or search)
    target_tag  TEXT,                         -- topic tag when target_type = 'topic'
    query_text  TEXT,                         -- search text when event_type = 'search'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Indexes for feeds, analytics and recommendations ----------
CREATE INDEX idx_posts_author_created   ON posts (author_id, created_at DESC);
CREATE INDEX idx_post_tags_tag          ON post_tags (tag);
CREATE INDEX idx_comments_post          ON comments (post_id, created_at);
CREATE INDEX idx_saves_paper            ON saves (paper_id);
CREATE INDEX idx_saves_user_time        ON saves (user_id, saved_at);
CREATE INDEX idx_user_interests_tag     ON user_interests (tag);
CREATE INDEX idx_follow_topics_tag      ON follow_topics (tag);
CREATE INDEX idx_events_time            ON events (created_at);
CREATE INDEX idx_events_type_time       ON events (event_type, created_at);
CREATE INDEX idx_events_user_time       ON events (user_id, created_at);

-- ---------- Read-only role for Member 2 (analytics) ----------
-- Change the password in your local .env; do not commit real passwords.
-- CREATE ROLE analytics_reader LOGIN PASSWORD 'change_me';
-- GRANT CONNECT ON DATABASE research_commons TO analytics_reader;
-- GRANT USAGE ON SCHEMA public TO analytics_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_reader;

-- ---------- Links to Member 2's papers table ----------
-- Added automatically by 03_paper_links.sql once papers exists.
