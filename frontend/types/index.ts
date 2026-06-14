/** Shared TypeScript types aligned with the GoalMind backend API. */

export interface TeamSummary {
  id: number;
  name: string;
  code: string | null;
  logo: string | null;
  is_placeholder?: boolean;
  raw_name?: string | null;
}

export interface GroupStandingRow {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  points: number;
  goal_diff: number;
}

export interface GoalScorer {
  player_name: string;
  minute: string;
  team: string;
  is_own_goal: boolean;
}

export interface FixtureSummary {
  id: number;
  date: string;
  status: string;
  home_team: TeamSummary;
  away_team: TeamSummary;
  home_goals: number | null;
  away_goals: number | null;
  venue: string | null;
  match_number?: number | null;
  goal_scorers?: GoalScorer[];
}

export interface BracketFixture extends FixtureSummary {
  stage: string;
  round_name: string;
  group: string | null;
  match_number: number | null;
  home_resolved: boolean;
  away_resolved: boolean;
}

export interface TournamentGroupSection {
  group: string;
  standings: GroupStandingRow[];
  fixtures: BracketFixture[];
}

export interface TournamentStageSection {
  stage: string;
  label: string;
  groups: TournamentGroupSection[] | null;
  fixtures: BracketFixture[];
}

export interface TournamentBracket {
  tournament: string;
  stages: TournamentStageSection[];
}

export interface TeamStats {
  team_id: number;
  name: string;
  code: string | null;
  logo: string | null;
  recent_form: number;
  avg_goals_scored: number;
  avg_goals_conceded: number;
  possession_avg: number;
  form_string: string | null;
  matches_played: number;
}

export type SquadCategory = "starting" | "substitute" | "reserve" | "injured";

export interface PlayerSummary {
  id: number;
  name: string;
  number: number | null;
  position: string | null;
  age: number | null;
  photo: string | null;
  category: SquadCategory;
  injury_reason: string | null;
}

export interface TeamSquad {
  team_id: number;
  team_name: string;
  source: string;
  is_live_lineup: boolean;
  live_minute: number | null;
  live_fixture_id: number | null;
  lineup_confirmed: boolean;
  all_players: PlayerSummary[];
  starting_xi: PlayerSummary[];
  substitutes: PlayerSummary[];
  reserves: PlayerSummary[];
  injured: PlayerSummary[];
}

export interface TransferItem {
  id: string;
  player_name: string;
  from_club: string | null;
  to_club: string | null;
  fee: string | null;
  transfer_type: string | null;
  date: string;
  source: string;
  url: string;
  summary: string | null;
  image_url: string | null;
}

export interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  category: string;
  published_at: string;
  image_url: string | null;
}

export interface NewsFeedResponse {
  articles: NewsArticle[];
  transfers: TransferItem[];
  categories: string[];
}

export interface FixtureDetail extends FixtureSummary {
  home_stats: TeamStats;
  away_stats: TeamStats;
}

export interface Prediction {
  fixture_id: number;
  home_win_probability: number;
  away_win_probability: number;
  draw_probability: number;
  home_expected_goals: number;
  away_expected_goals: number;
  confidence_score: number;
  prediction_label: string;
}

export interface MatchWithPrediction extends FixtureSummary {
  prediction: Prediction | null;
}

export type ConfidenceLevel = "low" | "medium" | "high";

export interface LiveTeamStats {
  shots: number;
  shots_on_target: number;
  possession: number;
  passes: number;
  pass_accuracy: number;
  fouls: number;
  yellow_cards: number;
  red_cards: number;
  offsides: number;
  corners: number;
}

export interface LiveMatchStats {
  fixture_id: number;
  is_live: boolean;
  status: string;
  minute: number;
  home_team: string;
  away_team: string;
  home_goals: number | null;
  away_goals: number | null;
  home: LiveTeamStats;
  away: LiveTeamStats;
}
