
-- Member 2: Research papers and ingestion tables

CREATE TABLE IF NOT EXISTS papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    abstract TEXT,
    keywords TEXT[],
    doi TEXT,
    arxiv_id TEXT,
    url TEXT,
    publication_year INTEGER,
    published_at DATE,
    venue TEXT,
    publisher TEXT,
    source TEXT,
    source_record_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    normalized_name TEXT,
    orcid TEXT,
    affiliation TEXT,
    author_position INTEGER
);

CREATE TABLE IF NOT EXISTS paper_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    source_url TEXT,
    raw_metadata JSONB,
    fetched_at TIMESTAMPTZ DEFAULT now()
);
