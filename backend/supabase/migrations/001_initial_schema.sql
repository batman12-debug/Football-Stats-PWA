-- GoalMind initial schema
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS teams (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    code        TEXT,
    logo        TEXT,
    country     TEXT,
    league_id   INTEGER NOT NULL,
    season      INTEGER NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_league_season ON teams (league_id, season);

CREATE TABLE IF NOT EXISTS fixtures (
    id              INTEGER PRIMARY KEY,
    league_id       INTEGER NOT NULL,
    season          INTEGER NOT NULL,
    date            TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'NS',
    status_long     TEXT,
    home_team_id    INTEGER NOT NULL REFERENCES teams (id),
    away_team_id    INTEGER NOT NULL REFERENCES teams (id),
    home_team_name  TEXT NOT NULL,
    away_team_name  TEXT NOT NULL,
    home_goals      INTEGER,
    away_goals      INTEGER,
    venue_name      TEXT,
    venue_city      TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fixtures_league_season ON fixtures (league_id, season);
CREATE INDEX IF NOT EXISTS idx_fixtures_date ON fixtures (date DESC);
CREATE INDEX IF NOT EXISTS idx_fixtures_status ON fixtures (status);
CREATE INDEX IF NOT EXISTS idx_fixtures_h2h ON fixtures (home_team_id, away_team_id);
