"""Shared snake/regular draft pick-order math.

DraftEnv.get_pick_positions, GameState._calculate_pick_order, and
MCTSDraftEnv.get_current_player/_calculate_our_picks each reimplement this
slightly differently (list-of-our-picks vs. full pick_order array vs.
direct-index math). Rather than touch any of those three engines, this is
one new pure module the webapp's DraftSession depends on instead -- zero
regression risk to already-passing tests.

`pick_number` is always 1-indexed (overall pick across the whole draft).
Team ids are always 0-indexed.
"""


def team_for_pick(pick_number, num_teams, draft_style):
    """0-indexed team whose turn it is for a given 1-indexed overall pick."""
    round_num = (pick_number - 1) // num_teams  # 0-indexed round
    pick_in_round = (pick_number - 1) % num_teams

    if draft_style == "snake" and round_num % 2 == 1:
        return num_teams - pick_in_round - 1
    return pick_in_round


def round_for_pick(pick_number, num_teams):
    """1-indexed round for a given 1-indexed overall pick."""
    return (pick_number - 1) // num_teams + 1


def calculate_pick_order(num_teams, num_rounds, draft_style):
    """Full list of 0-indexed teams, one per overall pick, length
    num_teams * num_rounds -- index i is the team for pick i + 1.
    """
    return [
        team_for_pick(pick_number, num_teams, draft_style)
        for pick_number in range(1, num_teams * num_rounds + 1)
    ]


def our_pick_positions(initial_pick, num_teams, num_rounds, draft_style):
    """1-indexed overall pick numbers belonging to the team drafting from
    `initial_pick` (1-indexed draft slot).
    """
    our_team = initial_pick - 1
    return [
        pick_number
        for pick_number in range(1, num_teams * num_rounds + 1)
        if team_for_pick(pick_number, num_teams, draft_style) == our_team
    ]
