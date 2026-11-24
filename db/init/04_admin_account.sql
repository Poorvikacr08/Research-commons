-- Shared admin account for the whole team (local development and viva demo).
--   name:     C R Poorvika Shetty
--   email:    poorvika@chanakyauniversity.edu
--   password: Demo@123
-- Runs automatically on a fresh database. On an existing database run it once:
--   Windows PowerShell:
--     Get-Content db/init/04_admin_account.sql | docker compose exec -T db psql -U rc_admin -d research_commons
--   Mac / Linux:
--     docker compose exec -T db psql -U rc_admin -d research_commons < db/init/04_admin_account.sql
-- If the account already exists, this resets it to admin with the password Demo@123.
-- Demo login only - change the password before any real deployment.
INSERT INTO users (name, email, password_hash, role, department)
VALUES ('C R Poorvika Shetty', 'poorvika@chanakyauniversity.edu', '$2b$12$kys8Jpb6RYJ.1h.y2lK0aeRSn8tZJ09VIMit1sqMvrlnqQ/8o0nhm', 'admin', 'Computer Science')
ON CONFLICT (email) DO UPDATE
SET name = EXCLUDED.name, password_hash = EXCLUDED.password_hash, role = 'admin';
