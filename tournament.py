from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

from game import Game
from player import Player
from settings import TOURS


def build_players(strategy_specs=None):
    """Создаёт набор игроков по CLI-спецификации или по умолчанию."""

    if strategy_specs:
        players = []
        counts = Counter()

        for spec in strategy_specs:
            name, strategy_name, threshold = parse_strategy_spec(spec)
            if not name:
                counts[strategy_name] += 1
                suffix = counts[strategy_name]
                if strategy_name == "CautiousStrategy":
                    name = f"Прозорливый {threshold}"
                elif strategy_name == "GreedyStrategy":
                    name = "Жадный" if suffix == 1 else f"Жадный {suffix}"
                elif strategy_name == "HopnessStrategy":
                    name = "Надеющийся" if suffix == 1 else f"Надеющийся {suffix}"
                elif strategy_name == "AdaptiveStrategy":
                    name = "Адаптивный" if suffix == 1 else f"Адаптивный {suffix}"
                elif strategy_name == "BarrelAwareStrategy":
                    name = "Бочкарь" if suffix == 1 else f"Бочкарь {suffix}"
                else:
                    name = f"{strategy_name} {suffix}"

            players.append(
                Player(
                    name=name,
                    strategy=strategy_name,
                    threshold=threshold,
                )
            )

        return players

    players = [
        Player(
            name=f"Прозорливый {threshold}",
            strategy="CautiousStrategy",
            threshold=threshold,
        )
        for threshold in range(0, 170, 5)
    ]

    players.append(Player(name="Жадный", strategy="GreedyStrategy"))
    players.append(
        Player(
            name="Надеющийся",
            strategy="HopnessStrategy",
            threshold=70,
        )
    )
    players.append(
        Player(
            name="Адаптивный",
            strategy="AdaptiveStrategy",
            threshold=60,
        )
    )
    players.append(
        Player(
            name="Бочкарь",
            strategy="BarrelAwareStrategy",
            threshold=55,
        )
    )
    return players


def parse_strategy_name(value):
    aliases = {
        "greedy": "GreedyStrategy",
        "greedystrategy": "GreedyStrategy",
        "жадный": "GreedyStrategy",
        "cautious": "CautiousStrategy",
        "cautiousstrategy": "CautiousStrategy",
        "прозорливый": "CautiousStrategy",
        "hopness": "HopnessStrategy",
        "hopnessstrategy": "HopnessStrategy",
        "hope": "HopnessStrategy",
        "надеющийся": "HopnessStrategy",
        "adaptive": "AdaptiveStrategy",
        "adaptivestrategy": "AdaptiveStrategy",
        "адаптивный": "AdaptiveStrategy",
        "barrel": "BarrelAwareStrategy",
        "barrelaware": "BarrelAwareStrategy",
        "barrelawarestrategy": "BarrelAwareStrategy",
        "бочкарь": "BarrelAwareStrategy",
    }

    normalized = value.strip().lower()
    if normalized not in aliases:
        raise ValueError(f"Unknown strategy '{value}'")

    return aliases[normalized]


def parse_strategy_spec(spec):
    """Формат: strategy[:threshold][:name]."""

    parts = [part.strip() for part in spec.split(":")]
    if not parts or not parts[0]:
        raise ValueError(f"Invalid strategy spec '{spec}'")

    strategy_name = parse_strategy_name(parts[0])

    default_thresholds = {
        "GreedyStrategy": 1,
        "CautiousStrategy": 50,
        "HopnessStrategy": 70,
        "AdaptiveStrategy": 60,
        "BarrelAwareStrategy": 55,
    }

    threshold = default_thresholds[strategy_name]
    name = None

    if len(parts) >= 2 and parts[1]:
        threshold = int(parts[1])

    if len(parts) >= 3 and parts[2]:
        name = parts[2]

    return name, strategy_name, threshold


class Tournament:
    def __init__(
        self,
        tours=TOURS,
        strategy_specs=None,
        collect_game_history=False,
        seed=None,
    ):
        """Конструктор турнира."""

        self.tours = tours
        self.collect_game_history = collect_game_history
        self.seed = seed
        self.random = random.Random(seed)
        self.player_specs = self.describe_players(build_players(strategy_specs))
        self.statistics = []
        self.aggregate = {
            "wins_by_player": Counter(),
            "wins_by_strategy": Counter(),
            "total_scores_by_player": Counter(),
            "games_by_player": Counter(),
            "fouls": 0,
            "strikes": 0,
            "rolls": 0,
            "turns": 0,
        }

    @staticmethod
    def describe_players(players):
        return [
            {
                "name": player.name,
                "strategy": player.strategy_name,
                "threshold": player.strategy.threshold,
            }
            for player in players
        ]

    def create_player_set(self):
        return [
            Player(
                name=spec["name"],
                strategy=spec["strategy"],
                threshold=spec["threshold"],
            )
            for spec in self.player_specs
        ]

    def record_game(self, game_index, game, winner):
        scores = {player.name: player.total_score for player in game.player_set}
        strategies = {player.name: player.strategy_name for player in game.player_set}

        self.statistics.append(
            {
                "game": game_index,
                "winner": winner,
                "scores": scores,
                "strategies": strategies,
                "rolls": game.stats["rolls"],
                "fouls": game.stats["fouls"],
                "strikes": game.stats["strikes"],
                "turns": game.stats["turns"],
            }
        )

        self.aggregate["wins_by_player"][winner] += 1
        self.aggregate["wins_by_strategy"][strategies[winner]] += 1
        self.aggregate["fouls"] += game.stats["fouls"]
        self.aggregate["strikes"] += game.stats["strikes"]
        self.aggregate["rolls"] += game.stats["rolls"]
        self.aggregate["turns"] += game.stats["turns"]

        for name, score in scores.items():
            self.aggregate["total_scores_by_player"][name] += score
            self.aggregate["games_by_player"][name] += 1

    def start(self):
        """Запуск турнира."""

        for game_index in range(1, self.tours + 1):
            game_seed = self.random.randrange(0, 2**32)
            game = Game(
                self.create_player_set(),
                rng=random.Random(game_seed),
                collect_history=self.collect_game_history,
            )
            winner = game.start()
            self.record_game(game_index, game, winner)

    def build_summary(self):
        total_games = len(self.statistics)
        average_scores = {
            name: round(
                self.aggregate["total_scores_by_player"][name]
                / self.aggregate["games_by_player"][name],
                1,
            )
            for name in self.aggregate["games_by_player"]
        }

        winrate_by_player = (
            {
                spec["name"]: round(
                    self.aggregate["wins_by_player"].get(spec["name"], 0) / total_games * 100,
                    1,
                )
                for spec in self.player_specs
            }
            if total_games
            else {}
        )

        strategy_names = sorted({spec["strategy"] for spec in self.player_specs})
        winrate_by_strategy = (
            {
                strategy: round(
                    self.aggregate["wins_by_strategy"].get(strategy, 0) / total_games * 100,
                    1,
                )
                for strategy in strategy_names
            }
            if total_games
            else {}
        )

        return {
            "total_games": total_games,
            "seed": self.seed,
            "players": [spec["name"] for spec in self.player_specs],
            "player_specs": self.player_specs,
            "average_score_by_player": average_scores,
            "winrate_by_player": winrate_by_player,
            "winrate_by_strategy": winrate_by_strategy,
            "foul_rate_per_roll": round(
                self.aggregate["fouls"] / self.aggregate["rolls"] * 100,
                1,
            )
            if self.aggregate["rolls"]
            else 0.0,
            "strike_rate_per_roll": round(
                self.aggregate["strikes"] / self.aggregate["rolls"] * 100,
                1,
            )
            if self.aggregate["rolls"]
            else 0.0,
            "average_rolls_per_game": round(self.aggregate["rolls"] / total_games, 1)
            if total_games
            else 0.0,
            "average_turns_per_game": round(self.aggregate["turns"] / total_games, 1)
            if total_games
            else 0.0,
            "fouls": self.aggregate["fouls"],
            "strikes": self.aggregate["strikes"],
            "rolls": self.aggregate["rolls"],
            "turns": self.aggregate["turns"],
        }

    def export_payload(self, mode="full"):
        summary = self.build_summary()

        if mode == "summary":
            return {"summary": summary}

        if mode == "per-game":
            return {"games": self.statistics}

        return {
            "summary": summary,
            "games": self.statistics,
        }

    def export_json(self, output_path, mode="full"):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.export_payload(mode=mode)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def export_csv(self, output_path, mode="full"):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as file:
            if mode == "summary":
                writer = csv.DictWriter(
                    file,
                    fieldnames=["section", "name", "value"],
                )
                writer.writeheader()

                summary = self.build_summary()

                scalar_fields = {
                    "total_games": summary["total_games"],
                    "seed": summary["seed"],
                    "foul_rate_per_roll": summary["foul_rate_per_roll"],
                    "strike_rate_per_roll": summary["strike_rate_per_roll"],
                    "average_rolls_per_game": summary["average_rolls_per_game"],
                    "average_turns_per_game": summary["average_turns_per_game"],
                    "fouls": summary["fouls"],
                    "strikes": summary["strikes"],
                    "rolls": summary["rolls"],
                    "turns": summary["turns"],
                }

                for name, value in scalar_fields.items():
                    writer.writerow({"section": "summary", "name": name, "value": value})

                for name, value in summary["average_score_by_player"].items():
                    writer.writerow({"section": "average_score_by_player", "name": name, "value": value})

                for name, value in summary["winrate_by_player"].items():
                    writer.writerow({"section": "winrate_by_player", "name": name, "value": value})

                for name, value in summary["winrate_by_strategy"].items():
                    writer.writerow({"section": "winrate_by_strategy", "name": name, "value": value})

                return

            fieldnames = ["game", "winner", "rolls", "turns", "fouls", "strikes"]

            for spec in self.player_specs:
                fieldnames.append(f"score::{spec['name']}")
                fieldnames.append(f"strategy::{spec['name']}")

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for game in self.statistics:
                row = {
                    "game": game["game"],
                    "winner": game["winner"],
                    "rolls": game["rolls"],
                    "turns": game["turns"],
                    "fouls": game["fouls"],
                    "strikes": game["strikes"],
                }

                for spec in self.player_specs:
                    name = spec["name"]
                    row[f"score::{name}"] = game["scores"][name]
                    row[f"strategy::{name}"] = game["strategies"][name]

                writer.writerow(row)

    def report(self):
        """Печать подробного отчёта."""

        summary = self.build_summary()
        total_games = summary["total_games"]

        print(f"Сыграно партий: {total_games}")
        if self.seed is not None:
            print(f"Seed турнира: {self.seed}")
        print("Состав турнира:")
        for spec in self.player_specs:
            print(
                f"- {spec['name']}: {spec['strategy']} (threshold={spec['threshold']})"
            )

        if total_games == 0:
            print("Турнир ещё не запускался.")
            return

        print()
        print("Сводка по турниру:")
        print(f"- Среднее число бросков за игру: {summary['average_rolls_per_game']}")
        print(f"- Среднее число ходов за игру: {summary['average_turns_per_game']}")
        print(f"- Частота булок: {summary['foul_rate_per_roll']}%")
        print(f"- Частота небиток: {summary['strike_rate_per_roll']}%")

        print()
        print("Результаты по игрокам:")
        for name in sorted(
            summary["average_score_by_player"],
            key=lambda player_name: (
                summary["winrate_by_player"].get(player_name, 0.0),
                summary["average_score_by_player"][player_name],
            ),
            reverse=True,
        ):
            winrate = summary["winrate_by_player"].get(name, 0.0)
            average_score = summary["average_score_by_player"][name]
            print(f"- {name}: winrate {winrate}%, средний счёт {average_score}")

        print()
        print("Winrate по стратегиям:")
        for strategy in sorted(
            summary["winrate_by_strategy"],
            key=lambda strategy_name: summary["winrate_by_strategy"][strategy_name],
            reverse=True,
        ):
            print(f"- {strategy}: {summary['winrate_by_strategy'][strategy]}%")
