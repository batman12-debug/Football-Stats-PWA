-- Row Level Security for GoalMind tables
-- Run after 001_initial_schema.sql in Supabase SQL editor

ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE fixtures ENABLE ROW LEVEL SECURITY;

-- Deny all access via anon/authenticated roles; backend uses service role key.
CREATE POLICY "deny_public_teams" ON teams
    FOR ALL
    TO anon, authenticated
    USING (false)
    WITH CHECK (false);

CREATE POLICY "deny_public_fixtures" ON fixtures
    FOR ALL
    TO anon, authenticated
    USING (false)
    WITH CHECK (false);
