-- Links app tables to papers(id). Runs after 02_papers.sql.
-- Skips safely if the papers table does not exist yet.
DO $$
BEGIN
    IF to_regclass('public.papers') IS NOT NULL THEN
        ALTER TABLE saves            ADD CONSTRAINT fk_saves_paper FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
        ALTER TABLE post_papers      ADD CONSTRAINT fk_pp_paper    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
        ALTER TABLE collection_items ADD CONSTRAINT fk_ci_paper    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
    ELSE
        RAISE NOTICE 'papers table not found - paper foreign keys skipped';
    END IF;
END $$;
