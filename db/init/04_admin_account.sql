-- Shared demo admin account for the whole team (local development and viva demo).
--   email:    admin@chanakya.edu
--   password: Demo@123
-- Runs automatically on a fresh database. On an existing database run it once:
--   Windows PowerShell:
--     Get-Content db/init/04_admin_account.sql | docker compose exec -T db psql -U rc_admin -d research_commons
--   Mac / Linux:
--     docker compose exec -T db psql -U rc_admin -d research_commons < db/init/04_admin_account.sql
-- This is a demo login only - change the password before any real deployment.
INSERT INTO users (name, email, password_hash, role, department)
VALUES ('Admin', 'admin@chanakya.edu', '$2b$12$2gYTCA8e/HvcMbBxAOuKWOiMiojvuaotw8zKhWg6jyTjdtXZ1dC32', 'admin', 'Administration')
ON CONFLICT (email) DO UPDATE SET role = 'admin';
