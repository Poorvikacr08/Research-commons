-- =====================================================================
-- Papers table - OWNED BY MEMBER 2 (ingestion)
-- Member 2: replace this placeholder with your real papers DDL.
-- Rule: keep `id UUID PRIMARY KEY` so the app tables can link to it.
-- =====================================================================

CREATE TABLE IF NOT EXISTS papers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      TEXT NOT NULL,
    abstract   TEXT,
    doi        TEXT,
    arxiv_id   TEXT,
    url        TEXT,
    year       INT,
    authors    TEXT,
    source     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
