import csv
import json
import unittest
from pathlib import Path

from game import Game
from player import Player, STRATEGY_REGISTRY, Strategy, TurnState
from plot_report import load_csv_report, load_json_report
from tournament import Tournament, build_player_specs, build_players, parse_strategy_spec


class ScriptedGame(Game):
    def __init__(self, player_set, rolls):
        super().__init__(player_set)
        self.rolls = [list(roll) for roll in rolls]

    def roll(self, cubes):
        if not self.rolls:
            raise AssertionError("Not enough scripted rolls provided")

        roll = self.rolls.pop(0)
        if len(roll) != cubes:
            raise AssertionError(f"Expected roll with {cubes} cubes, got {len(roll)}")

        return roll


class NoBankStrategy(Strategy):
    def choose_hold(self, turn_state, roll_counts, hold_options):
        return max(hold_options, key=lambda option: (option.score, option.used_dice))

    def should_bank(self, turn_state):
        return False


class MinimalHoldStrategy(Strategy):
    def choose_hold(self, turn_state, roll_counts, hold_options):
        return min(hold_options, key=lambda option: (option.used_dice, option.score))

    def should_bank(self, turn_state):
        return False


class StrategyTests(unittest.TestCase):
    def test_cautious_threshold_changes_decision(self):
        low_threshold = Player("low", strategy="CautiousStrategy", threshold=20)
        high_threshold = Player("high", strategy="CautiousStrategy", threshold=50)
        state = TurnState(
            total_score=0,
            turn_score=30,
            remaining_cubes=4,
            rolls_left=2,
            barrel_active=False,
            frozen_score=0,
        )

        self.assertTrue(low_threshold.strategy.should_bank(state))
        self.assertFalse(high_threshold.strategy.should_bank(state))

    def test_adaptive_strategy_banks_early_when_risk_is_high(self):
        adaptive = Player("adaptive", strategy="AdaptiveStrategy", threshold=60)
        state = TurnState(
            total_score=200,
            turn_score=35,
            remaining_cubes=1,
            rolls_left=2,
            barrel_active=False,
            frozen_score=200,
        )

        self.assertTrue(adaptive.strategy.should_bank(state))

    def test_barrel_aware_strategy_forces_close_on_barrel(self):
        barrel = Player("barrel", strategy="BarrelAwareStrategy", threshold=55)
        state = TurnState(
            total_score=920,
            turn_score=80,
            remaining_cubes=2,
            rolls_left=1,
            barrel_active=True,
            frozen_score=920,
        )

        self.assertTrue(barrel.strategy.should_bank(state))


class GameRuleTests(unittest.TestCase):
    def test_grade_counts_single_and_group_scores(self):
        self.assertEqual(Game.grade({1: 1}), 10)
        self.assertEqual(Game.grade({5: 1}), 5)
        self.assertEqual(Game.grade({1: 3}), 100)
        self.assertEqual(Game.grade({4: 4}), 140)
        self.assertEqual(Game.grade({6: 5}), 1000)
        self.assertEqual(Game.grade({1: 2, 5: 2, 3: 1}), 30)

    def test_strike_accepts_non_scoring_pairs_when_all_dice_are_covered(self):
        self.assertTrue(Game.check_strike({2: 2, 1: 2, 5: 1}))
        self.assertFalse(Game.check_strike({2: 1, 1: 1, 5: 1}))

    def test_foul_burns_turn_score(self):
        player = Player("Жадный", strategy="GreedyStrategy")
        game = ScriptedGame([player], rolls=[[2, 2, 3, 4, 6]])

        finished = game.play_turn(player)

        self.assertFalse(finished)
        self.assertEqual(player.total_score, 0)
        self.assertTrue(game.history[-1]["check_foul"])

    def test_hold_reduces_cube_count_for_next_roll(self):
        player = Player("Нетерпеливый", strategy=MinimalHoldStrategy())
        game = ScriptedGame(
            [player],
            rolls=[
                [1, 5, 2, 3, 4],
                [5, 2, 3, 4],
                [1, 2, 3],
            ],
        )

        game.play_turn(player)

        self.assertEqual(len(game.history[0]["roll"]), 5)
        self.assertEqual(len(game.history[1]["roll"]), 4)
        self.assertEqual(len(game.history[2]["roll"]), 3)

    def test_strike_resets_throw_cycle_and_cube_count(self):
        player = Player("Осторожный", strategy=NoBankStrategy())
        game = ScriptedGame(
            [player],
            rolls=[
                [2, 2, 1, 1, 5],
                [1, 2, 3, 4, 6],
                [5, 2, 3, 4],
                [1, 2, 3],
            ],
        )

        game.play_turn(player)

        self.assertTrue(game.history[0]["check_strike"])
        self.assertEqual(len(game.history[1]["roll"]), 5)

    def test_barrel_closes_when_player_reaches_target(self):
        player = Player("Жадный", strategy="GreedyStrategy")
        game = ScriptedGame([player], rolls=[[1, 1, 1, 1, 1]])
        player.total_score = 920
        player.barrel_score = 920

        finished = game.play_turn(player)

        self.assertTrue(finished)
        self.assertGreaterEqual(player.total_score, 1000)
        self.assertIsNone(player.barrel_score)

    def test_barrel_keeps_score_frozen_on_failed_close(self):
        player = Player("Упрямый", strategy=NoBankStrategy())
        game = ScriptedGame(
            [player],
            rolls=[
                [5, 2, 3, 4, 6],
                [5, 2, 3, 4],
                [5, 2, 3],
            ],
        )
        player.total_score = 920
        player.barrel_score = 920

        finished = game.play_turn(player)

        self.assertFalse(finished)
        self.assertEqual(player.total_score, 920)
        self.assertEqual(player.barrel_score, 920)


class TournamentTests(unittest.TestCase):
    def test_parse_strategy_spec_with_threshold_and_name(self):
        name, strategy, threshold = parse_strategy_spec("cautious:80:Тест")

        self.assertEqual(name, "Тест")
        self.assertEqual(strategy, "CautiousStrategy")
        self.assertEqual(threshold, 80)

    def test_build_players_uses_cli_specs(self):
        players = build_players(["greedy", "adaptive:90:Риск"])

        self.assertEqual([player.name for player in players], ["Жадный", "Риск"])
        self.assertEqual(players[0].strategy_name, "GreedyStrategy")
        self.assertEqual(players[1].strategy.threshold, 90)

    def test_build_player_specs_uses_registry_defaults(self):
        specs = build_player_specs(["greedy", "barrel"])

        self.assertEqual(
            specs[0].threshold,
            STRATEGY_REGISTRY["GreedyStrategy"].default_threshold,
        )
        self.assertEqual(
            specs[1].threshold,
            STRATEGY_REGISTRY["BarrelAwareStrategy"].default_threshold,
        )

    def test_unknown_strategy_raises_error(self):
        with self.assertRaises(ValueError):
            Player("Ошибка", strategy="NoSuchStrategy")

    def test_tournament_collects_summary_without_history(self):
        tournament = Tournament(
            tours=3,
            strategy_specs=["greedy:1:Жадный", "cautious:50:Осторожный"],
            collect_game_history=False,
            seed=123,
        )

        tournament.start()
        summary = tournament.build_summary()

        self.assertEqual(summary["total_games"], 6)
        self.assertEqual(set(summary["players"]), {"Жадный", "Осторожный"})
        self.assertGreater(summary["rolls"], 0)
        self.assertIn("GreedyStrategy", summary["winrate_by_strategy"])
        self.assertIn("Жадный", summary["average_score_by_player"])
        self.assertIn("Жадный", summary["average_turns_to_win_by_player"])
        self.assertEqual(summary["games_by_player"]["Жадный"], 3)
        self.assertEqual(summary["seed"], 123)

    def test_tournament_is_reproducible_with_same_seed(self):
        specs = ["greedy:1:Жадный", "barrel:55:Бочкарь", "adaptive:60:Адаптивный"]
        tournament_a = Tournament(tours=5, strategy_specs=specs, seed=777)
        tournament_b = Tournament(tours=5, strategy_specs=specs, seed=777)

        tournament_a.start()
        tournament_b.start()

        self.assertEqual(tournament_a.statistics, tournament_b.statistics)
        self.assertEqual(tournament_a.build_summary(), tournament_b.build_summary())

    def test_export_json_and_csv(self):
        tournament = Tournament(
            tours=2,
            strategy_specs=["greedy:1:Жадный", "adaptive:60:Адаптивный"],
            seed=99,
        )
        tournament.start()

        export_dir = Path("tests") / "_artifacts"
        export_dir.mkdir(exist_ok=True)
        json_path = export_dir / "report.json"
        csv_path = export_dir / "report.csv"

        self.addCleanup(lambda: json_path.unlink(missing_ok=True))
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        tournament.export_json(json_path)
        tournament.export_csv(csv_path)

        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(json_payload["schema_version"], 3)
        self.assertIn("summary", json_payload)
        self.assertEqual(json_payload["summary"]["seed"], 99)
        self.assertEqual(len(json_payload["games"]), 4)
        self.assertIn("player", json_payload["games"][0])
        self.assertIn("score", json_payload["games"][0])

        with csv_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 4)
        self.assertIn("player", rows[0])
        self.assertIn("strategy", rows[0])
        self.assertIn("score", rows[0])

    def test_summary_only_and_per_game_only_exports(self):
        tournament = Tournament(
            tours=2,
            strategy_specs=["greedy:1:Жадный", "barrel:55:Бочкарь"],
            seed=55,
        )
        tournament.start()

        export_dir = Path("tests") / "_artifacts"
        export_dir.mkdir(exist_ok=True)
        json_summary = export_dir / "summary_only.json"
        csv_summary = export_dir / "summary_only.csv"
        json_games = export_dir / "per_game_only.json"

        self.addCleanup(lambda: json_summary.unlink(missing_ok=True))
        self.addCleanup(lambda: csv_summary.unlink(missing_ok=True))
        self.addCleanup(lambda: json_games.unlink(missing_ok=True))

        tournament.export_json(json_summary, mode="summary")
        tournament.export_csv(csv_summary, mode="summary")
        tournament.export_json(json_games, mode="per-game")

        summary_payload = json.loads(json_summary.read_text(encoding="utf-8"))
        self.assertIn("summary", summary_payload)
        self.assertNotIn("games", summary_payload)

        per_game_payload = json.loads(json_games.read_text(encoding="utf-8"))
        self.assertIn("games", per_game_payload)
        self.assertNotIn("summary", per_game_payload)

        with csv_summary.open("r", encoding="utf-8", newline="") as file:
            summary_rows = list(csv.DictReader(file))
        self.assertEqual(summary_rows[0]["section"], "summary")
        self.assertIn(summary_rows[0]["name"], {"schema_version", "total_games", "seed"})
        self.assertTrue(any(row["section"] == "average_turns_to_win_by_player" for row in summary_rows))

    def test_show_game_history_exports_history_to_json(self):
        tournament = Tournament(
            tours=1,
            strategy_specs=["greedy:1:Жадный", "barrel:55:Бочкарь"],
            seed=7,
            collect_game_history=True,
        )
        tournament.start()

        export_dir = Path("tests") / "_artifacts"
        export_dir.mkdir(exist_ok=True)
        json_path = export_dir / "history_report.json"

        self.addCleanup(lambda: json_path.unlink(missing_ok=True))

        tournament.export_json(json_path)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("history", payload["games"][0])
        self.assertTrue(payload["games"][0]["history"])
        self.assertIn("roll", payload["games"][0]["history"][0])
        self.assertIn("check_foul", payload["games"][0]["history"][0])

    def test_plot_loaders_understand_json_and_csv_exports(self):
        tournament = Tournament(
            tours=2,
            strategy_specs=["greedy:1:Жадный", "adaptive:60:Адаптивный"],
            seed=101,
        )
        tournament.start()

        export_dir = Path("tests") / "_artifacts"
        export_dir.mkdir(exist_ok=True)
        json_path = export_dir / "plot_report.json"
        csv_path = export_dir / "plot_report.csv"

        self.addCleanup(lambda: json_path.unlink(missing_ok=True))
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        tournament.export_json(json_path)
        tournament.export_csv(csv_path)

        json_summary, json_games = load_json_report(json_path)
        csv_summary, csv_games = load_csv_report(csv_path)

        self.assertEqual(json_summary["seed"], 101)
        self.assertEqual(json_summary["schema_version"], 3)
        self.assertEqual(len(json_games), 4)
        self.assertEqual(csv_summary["total_games"], 4)
        self.assertIn("average_turns_to_win_by_player", csv_summary)
        self.assertEqual(len(csv_games), 4)

    def test_plot_loader_understands_legacy_multi_player_csv_exports(self):
        export_dir = Path("tests") / "_artifacts"
        export_dir.mkdir(exist_ok=True)
        legacy_csv = export_dir / "legacy_report.csv"

        self.addCleanup(lambda: legacy_csv.unlink(missing_ok=True))

        legacy_csv.write_text(
            "game,winner,rolls,turns,fouls,strikes,score::Жадный,strategy::Жадный,score::Адаптивный,strategy::Адаптивный\n"
            "1,Жадный,10,3,0,1,120,GreedyStrategy,90,AdaptiveStrategy\n",
            encoding="utf-8",
        )

        summary, games = load_csv_report(legacy_csv)

        self.assertEqual(summary["schema_version"], 1)
        self.assertIn("Жадный", summary["average_score_by_player"])
        self.assertEqual(len(games), 1)


if __name__ == "__main__":
    unittest.main()
