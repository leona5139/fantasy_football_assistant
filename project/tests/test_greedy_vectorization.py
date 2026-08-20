import pytest

from project.draft.config import LeagueConfig
from project.draft.greedy import GreedyDraftAssistant


def test_vectorized_matches_iterrows_best_player(sample_player_pool):
    assistant = GreedyDraftAssistant(sample_player_pool, LeagueConfig())

    for round_num in (1, 7, 13):
        vectorized = assistant.get_best_player(sample_player_pool, round_num)
        reference = assistant._get_best_player_iterrows(sample_player_pool, round_num)
        assert vectorized["Player"] == reference["Player"]


def test_vectorized_matches_iterrows_top_n(sample_player_pool):
    assistant = GreedyDraftAssistant(sample_player_pool, LeagueConfig())
    round_num = 4

    top5 = assistant.get_top_candidates(sample_player_pool, round_num, n=5)

    scored = []
    for _, player in sample_player_pool.iterrows():
        eff = assistant.get_draft_efficiency(player, sample_player_pool, round_num)
        scored.append((eff, player["Player"]))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    expected_top5 = [name for _, name in scored[:5]]

    assert list(top5["Player"]) == expected_top5


def test_opportunity_cost_reacts_to_roster_fill(sample_player_pool):
    baseline = GreedyDraftAssistant(sample_player_pool, LeagueConfig())
    baseline_top_rb = baseline.get_top_candidates(sample_player_pool, round_num=3, n=1).iloc[0]

    filled = GreedyDraftAssistant(sample_player_pool, LeagueConfig())
    filled.record_pick("RB", is_ours=True)
    filled.record_pick("RB", is_ours=True)
    filled.record_pick("RB", is_ours=True)
    assert filled.roster_filled["RB"] == 3

    rb_row = sample_player_pool[sample_player_pool["Position"] == "RB"].iloc[0]
    baseline_eff = baseline.get_draft_efficiency(rb_row, sample_player_pool, round_num=3)
    filled_eff = filled.get_draft_efficiency(rb_row, sample_player_pool, round_num=3)

    assert filled_eff < baseline_eff
    assert baseline_top_rb["Player"] is not None  # sanity: baseline call didn't error


def test_needs_and_replacement_levels_scale_with_league_config():
    small = LeagueConfig(num_teams=10)
    large = LeagueConfig(num_teams=12)

    small_levels = small.replacement_levels()
    large_levels = large.replacement_levels()

    for pos in small_levels:
        assert large_levels[pos] >= small_levels[pos]

    # Matches the original hardcoded 12-team assumption exactly ("~1.5 QBs per team").
    assert large_levels["QB"] == 18
