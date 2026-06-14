"""Tournament bracket: stages, standings, and dynamic knockout resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.data_sources.openfootball import (
    fixture_id,
    parse_kickoff,
)
from app.services.data_sources.openfootball_scores import (
    parse_full_time_score,
    parse_goal_scorers,
)
from app.services.data_sources.team_flags import team_display_code, team_flag_url
from app.services.data_sources.team_names import stable_team_id

PLACEHOLDER_RANK = re.compile(r"^(\d)([A-L])$", re.I)
PLACEHOLDER_WINNER = re.compile(r"^W(\d+)$", re.I)
PLACEHOLDER_LOSER = re.compile(r"^L(\d+)$", re.I)
PLACEHOLDER_THIRD_POOL = re.compile(r"^3([A-L](/[A-L])+)$", re.I)

STAGE_ORDER: list[tuple[str, str]] = [
    ("group_stage", "Group Stage"),
    ("round_of_32", "Round of 32"),
    ("round_of_16", "Round of 16"),
    ("quarter_final", "Quarter-finals"),
    ("semi_final", "Semi-finals"),
    ("third_place", "Third Place Play-off"),
    ("final", "Final"),
]

STAGE_FROM_ROUND = {
    "Round of 32": "round_of_32",
    "Round of 16": "round_of_16",
    "Quarter-final": "quarter_final",
    "Semi-final": "semi_final",
    "Match for third place": "third_place",
    "Final": "final",
}


@dataclass
class StandingRow:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class MatchOutcome:
    fixture_id: int
    match_number: int | None
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    winner: str | None = None
    loser: str | None = None
    finished: bool = False


@dataclass
class ResolvedFixture:
    id: int
    date: datetime
    status: str
    stage: str
    stage_label: str
    round_name: str
    group: str | None
    match_number: int | None
    home_team: dict[str, Any]
    away_team: dict[str, Any]
    home_goals: int | None
    away_goals: int | None
    venue: str | None
    home_resolved: bool
    away_resolved: bool
    goal_scorers: list[dict[str, Any]] = field(default_factory=list)


def classify_stage(round_name: str) -> str:
    if round_name.startswith("Matchday"):
        return "group_stage"
    return STAGE_FROM_ROUND.get(round_name, "group_stage")


def _is_placeholder(name: str) -> bool:
    name = name.strip()
    if PLACEHOLDER_RANK.match(name):
        return True
    if PLACEHOLDER_WINNER.match(name):
        return True
    if PLACEHOLDER_LOSER.match(name):
        return True
    if name.upper().startswith("3") and "/" in name:
        return True
    return False


def _placeholder_label(name: str) -> str:
    rank = PLACEHOLDER_RANK.match(name)
    if rank:
        pos, grp = rank.groups()
        ordinals = {"1": "1st", "2": "2nd", "3": "3rd"}
        return f"{ordinals.get(pos, pos)} in Group {grp.upper()}"

    winner = PLACEHOLDER_WINNER.match(name)
    if winner:
        return f"Winner of Match {winner.group(1)}"

    loser = PLACEHOLDER_LOSER.match(name)
    if loser:
        return f"Loser of Match {loser.group(1)}"

    if name.upper().startswith("3") and "/" in name:
        groups = name.upper().replace("3", "").split("/")
        groups = [g for g in groups if g]
        return f"Best 3rd place ({'/'.join(groups)})"

    return name


def _team_dict(name: str, *, resolved: bool) -> dict[str, Any]:
    display = name if resolved else _placeholder_label(name)
    return {
        "id": stable_team_id(name) if resolved else 0,
        "name": display,
        "code": team_display_code(name) if resolved else None,
        "logo": team_flag_url(name) if resolved else None,
        "raw_name": name if not resolved else None,
        "is_placeholder": not resolved,
    }


def _match_result(
    raw: dict[str, Any],
    index: int,
    stored_results: dict[int, tuple[int, int]],
) -> tuple[int | None, int | None, str, list[dict[str, Any]]]:
    fid = fixture_id(raw, index)
    if fid in stored_results:
        h, a = stored_results[fid]
        return h, a, "FT", parse_goal_scorers(raw)

    home_goals, away_goals = parse_full_time_score(raw)
    if home_goals is not None and away_goals is not None:
        return home_goals, away_goals, "FT", parse_goal_scorers(raw)

    kickoff = parse_kickoff(raw["date"], raw.get("time", "12:00 UTC+0"))
    if kickoff > datetime.now(timezone.utc):
        return None, None, "NS", []
    return None, None, "NS", []


def _apply_result(row: StandingRow, gf: int, ga: int) -> None:
    row.played += 1
    row.goals_for += gf
    row.goals_against += ga
    if gf > ga:
        row.won += 1
    elif gf < ga:
        row.lost += 1
    else:
        row.drawn += 1


def _compute_group_standings(
    group_matches: list[tuple[dict[str, Any], int, tuple[int | None, int | None]]],
) -> list[StandingRow]:
    table: dict[str, StandingRow] = {}

    for raw, _idx, (hg, ag) in group_matches:
        if hg is None or ag is None:
            continue
        for team, gf, ga in (
            (raw["team1"], hg, ag),
            (raw["team2"], ag, hg),
        ):
            if team not in table:
                table[team] = StandingRow(team=team)
            _apply_result(table[team], gf, ga)

    return sorted(
        table.values(),
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team),
    )


def _third_place_candidates(
    standings_by_group: dict[str, list[StandingRow]],
    pool: str,
) -> list[StandingRow]:
    groups = pool.upper().replace("3", "").split("/")
    groups = [g.strip() for g in groups if g.strip()]
    candidates: list[StandingRow] = []

    for letter in groups:
        rows = standings_by_group.get(letter, [])
        if len(rows) >= 3:
            candidates.append(rows[2])
    return sorted(
        candidates,
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team),
    )


def _resolve_token(
    token: str,
    *,
    standings_by_group: dict[str, list[StandingRow]],
    outcomes_by_num: dict[int, MatchOutcome],
    used_third_place: set[str],
) -> tuple[str | None, bool]:
    token = token.strip()

    rank = PLACEHOLDER_RANK.match(token)
    if rank:
        pos, grp = int(rank.group(1)), rank.group(2).upper()
        rows = standings_by_group.get(grp, [])
        if len(rows) >= pos:
            return rows[pos - 1].team, True
        return None, False

    winner = PLACEHOLDER_WINNER.match(token)
    if winner:
        num = int(winner.group(1))
        outcome = outcomes_by_num.get(num)
        if outcome and outcome.winner:
            return outcome.winner, True
        return None, False

    loser = PLACEHOLDER_LOSER.match(token)
    if loser:
        num = int(loser.group(1))
        outcome = outcomes_by_num.get(num)
        if outcome and outcome.loser:
            return outcome.loser, True
        return None, False

    if token.upper().startswith("3") and "/" in token:
        for candidate in _third_place_candidates(standings_by_group, token):
            if candidate.team not in used_third_place:
                used_third_place.add(candidate.team)
                return candidate.team, True
        return None, False

    return token, True


async def build_tournament_bracket(
    raw_matches: list[dict[str, Any]],
    *,
    stored_results: dict[int, tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Build full bracket with stages, groups, and resolved teams."""
    indexed = [{**m, "_index": i} for i, m in enumerate(raw_matches)]
    results: dict[int, tuple[int, int]] = dict(stored_results or {})

    # Pass 1: collect results for all matches (sync — no per-match Redis)
    match_data: list[
        tuple[
            dict[str, Any],
            int,
            int,
            int | None,
            int | None,
            str,
            list[dict[str, Any]],
        ]
    ] = []
    for raw in indexed:
        idx = raw["_index"]
        fid = fixture_id(raw, idx)
        hg, ag, status, scorers = _match_result(raw, idx, results)
        if hg is not None and ag is not None:
            results[fid] = (hg, ag)
        match_data.append((raw, idx, fid, hg, ag, status, scorers))

    # Group standings
    group_buckets: dict[str, list[tuple[dict[str, Any], int, tuple[int | None, int | None]]]] = {}
    for raw, idx, _fid, hg, ag, _status, _scorers in match_data:
        if "group" not in raw:
            continue
        letter = raw["group"].replace("Group ", "").strip().upper()
        group_buckets.setdefault(letter, []).append((raw, idx, (hg, ag)))

    standings_by_group = {
        g: _compute_group_standings(matches) for g, matches in group_buckets.items()
    }

    # Match outcomes by number (for W/L resolution)
    outcomes_by_num: dict[int, MatchOutcome] = {}
    for raw, idx, fid, hg, ag, status, scorers in match_data:
        num = raw.get("num")
        home, away = raw["team1"], raw["team2"]
        outcome = MatchOutcome(
            fixture_id=fid,
            match_number=num,
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            finished=status == "FT" and hg is not None and ag is not None,
        )
        if outcome.finished and hg is not None and ag is not None:
            if hg > ag:
                outcome.winner, outcome.loser = home, away
            elif ag > hg:
                outcome.winner, outcome.loser = away, home
            else:
                outcome.winner = outcome.loser = None
        if num is not None:
            outcomes_by_num[int(num)] = outcome

    used_third_place: set[str] = set()
    resolved_fixtures: list[ResolvedFixture] = []

    # Group stage first (real team names)
    for raw, idx, fid, hg, ag, status, scorers in match_data:
        stage = classify_stage(raw.get("round", ""))
        if stage != "group_stage":
            continue
        stage_label = next(label for key, label in STAGE_ORDER if key == stage)
        resolved_fixtures.append(
            ResolvedFixture(
                id=fid,
                date=parse_kickoff(raw["date"], raw.get("time", "12:00 UTC+0")),
                status=status,
                stage=stage,
                stage_label=stage_label,
                round_name=raw.get("round", ""),
                group=raw.get("group"),
                match_number=raw.get("num"),
                home_team=_team_dict(raw["team1"], resolved=True),
                away_team=_team_dict(raw["team2"], resolved=True),
                home_goals=hg,
                away_goals=ag,
                venue=raw.get("ground"),
                home_resolved=True,
                away_resolved=True,
                goal_scorers=scorers,
            )
        )

    # Knockout: resolve in match-number order so winners feed forward
    knockout_rows = [
        (raw, idx, fid, hg, ag, status, scorers)
        for raw, idx, fid, hg, ag, status, scorers in match_data
        if classify_stage(raw.get("round", "")) != "group_stage"
    ]
    knockout_rows.sort(key=lambda row: row[0].get("num") or 999)

    for raw, idx, fid, hg, ag, status, scorers in knockout_rows:
        stage = classify_stage(raw.get("round", ""))
        stage_label = next(label for key, label in STAGE_ORDER if key == stage)
        home_token, away_token = raw["team1"], raw["team2"]

        home_name, home_ok = _resolve_token(
            home_token,
            standings_by_group=standings_by_group,
            outcomes_by_num=outcomes_by_num,
            used_third_place=used_third_place,
        )
        away_name, away_ok = _resolve_token(
            away_token,
            standings_by_group=standings_by_group,
            outcomes_by_num=outcomes_by_num,
            used_third_place=used_third_place,
        )
        if home_name is None:
            home_name, home_ok = home_token, False
        if away_name is None:
            away_name, away_ok = away_token, False

        # Update outcomes with resolved names for downstream W/L slots
        num = raw.get("num")
        if num is not None and num in outcomes_by_num:
            outcome = outcomes_by_num[int(num)]
            outcome.home_team = home_name if home_ok else home_token
            outcome.away_team = away_name if away_ok else away_token
            if outcome.finished and hg is not None and ag is not None:
                if hg > ag:
                    outcome.winner = outcome.home_team
                    outcome.loser = outcome.away_team
                elif ag > hg:
                    outcome.winner = outcome.away_team
                    outcome.loser = outcome.home_team

        resolved_fixtures.append(
            ResolvedFixture(
                id=fid,
                date=parse_kickoff(raw["date"], raw.get("time", "12:00 UTC+0")),
                status=status,
                stage=stage,
                stage_label=stage_label,
                round_name=raw.get("round", ""),
                group=raw.get("group"),
                match_number=raw.get("num"),
                home_team=_team_dict(home_name, resolved=home_ok),
                away_team=_team_dict(away_name, resolved=away_ok),
                home_goals=hg,
                away_goals=ag,
                venue=raw.get("ground"),
                home_resolved=home_ok,
                away_resolved=away_ok,
                goal_scorers=scorers,
            )
        )

    return _group_into_stages(resolved_fixtures, standings_by_group)


def _group_into_stages(
    fixtures: list[ResolvedFixture],
    standings_by_group: dict[str, list[StandingRow]],
) -> dict[str, Any]:
    stages_out: list[dict[str, Any]] = []

    for stage_key, stage_label in STAGE_ORDER:
        stage_fixtures = [f for f in fixtures if f.stage == stage_key]
        if not stage_fixtures:
            continue

        if stage_key == "group_stage":
            groups_out: list[dict[str, Any]] = []
            letters = sorted(
                {f.group.replace("Group ", "").strip() for f in stage_fixtures if f.group}
            )
            for letter in letters:
                group_name = f"Group {letter}"
                gf = [f for f in stage_fixtures if f.group == group_name]
                gf.sort(key=lambda f: (f.date, f.round_name))
                standings = standings_by_group.get(letter, [])
                groups_out.append(
                    {
                        "group": group_name,
                        "standings": [
                            {
                                "team": r.team,
                                "played": r.played,
                                "won": r.won,
                                "drawn": r.drawn,
                                "lost": r.lost,
                                "goals_for": r.goals_for,
                                "goals_against": r.goals_against,
                                "points": r.points,
                                "goal_diff": r.goal_diff,
                            }
                            for r in standings
                        ],
                        "fixtures": [_fixture_to_dict(f) for f in gf],
                    }
                )
            stages_out.append(
                {
                    "stage": stage_key,
                    "label": stage_label,
                    "groups": groups_out,
                    "fixtures": [],
                }
            )
        else:
            stage_fixtures.sort(key=lambda f: (f.date, f.match_number or 0))
            stages_out.append(
                {
                    "stage": stage_key,
                    "label": stage_label,
                    "groups": None,
                    "fixtures": [_fixture_to_dict(f) for f in stage_fixtures],
                }
            )

    return {
        "tournament": "FIFA World Cup 2026",
        "stages": stages_out,
    }


def _fixture_to_dict(f: ResolvedFixture) -> dict[str, Any]:
    return {
        "id": f.id,
        "date": f.date.isoformat(),
        "status": f.status,
        "stage": f.stage,
        "round_name": f.round_name,
        "group": f.group,
        "match_number": f.match_number,
        "home_team": f.home_team,
        "away_team": f.away_team,
        "home_goals": f.home_goals,
        "away_goals": f.away_goals,
        "venue": f.venue,
        "home_resolved": f.home_resolved,
        "away_resolved": f.away_resolved,
        "goal_scorers": f.goal_scorers,
    }
