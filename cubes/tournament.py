from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from .game import Game
from .models import PlayerSpec
from .settings import TOURS
from .strategies import STRATEGY_REGISTRY, build_player_spec, create_player, resolve_strategy_name

EXPORT_SCHEMA_VERSION = 3


def default_player_name(strategy_name: str, threshold: int, suffix: int) -> str:
    definition = STRATEGY_REGISTRY[strategy_name]
    if strategy_name == "CautiousStrategy":
        return f"{definition.display_name} {threshold}"
    if suffix == 1:
        return definition.display_name
    return f"{definition.display_name} {suffix}"


def parse_strategy_spec(spec: str) -> tuple[str | None, str, int]:
    parts = [part.strip() for part in spec.split(":")]
    if not parts or not parts[0]:
        raise ValueError(f"Invalid strategy spec '{spec}'")

    strategy_name = resolve_strategy_name(parts[0])
    definition = STRATEGY_REGISTRY[strategy_name]
    threshold = definition.default_threshold
    name = None

    if len(parts) >= 2 and parts[1]:
        threshold = int(parts[1])

    if len(parts) >= 3 and parts[2]:
        name = parts[2]

    return name, strategy_name, threshold


def build_player_specs(strategy_specs: list[str] | None = None) -> list[PlayerSpec]:
    if strategy_specs:
        specs: list[PlayerSpec] = []
        counts: Counter[str] = Counter()

        for raw_spec in strategy_specs:
            name, strategy_name, threshold = parse_strategy_spec(raw_spec)
            if not name:
                counts[strategy_name] += 1
                name = default_player_name(strategy_name, threshold, counts[strategy_name])
            specs.append(build_player_spec(name, strategy_name, threshold))

        return specs

    specs = [
        build_player_spec(
            name=f"{STRATEGY_REGISTRY['CautiousStrategy'].display_name} {threshold}",
            strategy="CautiousStrategy",
            threshold=threshold,
        )
        for threshold in range(0, 170, 5)
    ]

    specs.extend(
        [
            build_player_spec("Жадный", "GreedyStrategy", 1),
            build_player_spec("Надеющийся", "HopnessStrategy", 70),
            build_player_spec("Адаптивный", "AdaptiveStrategy", 60),
            build_player_spec("Бочкарь", "BarrelAwareStrategy", 55),
        ]
    )
    return specs


def build_players(strategy_specs: list[str] | None = None):
    return [
        create_player(
            name=spec.name,
            strategy=spec.strategy,
            threshold=spec.threshold,
        )
        for spec in build_player_specs(strategy_specs)
    ]


class Tournament:
    def __init__(
        self,
        tours: int = TOURS,
        strategy_specs: list[str] | None = None,
        collect_game_history: bool = False,
        seed: int | None = None,
    ):
        self.tours = tours
        self.collect_game_history = collect_game_history
        self.seed = seed
        self.random = random.Random(seed)
        self.player_specs = build_player_specs(strategy_specs)
        self.statistics: list[dict[str, Any]] = []
        self.aggregate = {
            "games_by_player": Counter(),
            "wins_by_player": Counter(),
            "games_by_strategy": Counter(),
            "wins_by_strategy": Counter(),
            "total_scores_by_player": Counter(),
            "total_scores_by_strategy": Counter(),
            "total_turns_by_player": Counter(),
            "total_turns_by_strategy": Counter(),
            "total_rolls_by_player": Counter(),
            "total_rolls_by_strategy": Counter(),
            "min_turns_by_player": {},
            "max_turns_by_player": {},
            "min_turns_by_strategy": {},
            "max_turns_by_strategy": {},
            "fouls": 0,
            "strikes": 0,
            "rolls": 0,
            "turns": 0,
        }

    def create_player(self, spec: PlayerSpec):
        return create_player(
            name=spec.name,
            strategy=spec.strategy,
            threshold=spec.threshold,
        )

    def create_player_set(self):
        return [self.create_player(spec) for spec in self.player_specs]

    def _update_turn_bounds(self, key: str, turns: int, minimums: dict[str, int], maximums: dict[str, int]) -> None:
        current_min = minimums.get(key)
        current_max = maximums.get(key)
        minimums[key] = turns if current_min is None else min(current_min, turns)
        maximums[key] = turns if current_max is None else max(current_max, turns)

    def record_game(
        self,
        game_index: int,
        series_index: int,
        series_game_index: int,
        spec: PlayerSpec,
        game: Game,
        winner: str | None,
    ) -> None:
        player = game.player_set[0]
        turns = game.stats["turns"]
        score = player.total_score

        game_entry: dict[str, Any] = {
            "game": game_index,
            "series": series_index,
            "series_game": series_game_index,
            "player": spec.name,
            "strategy": spec.strategy,
            "threshold": spec.threshold,
            "winner": winner,
            "score": score,
            "turns": turns,
            "rolls": game.stats["rolls"],
            "fouls": game.stats["fouls"],
            "strikes": game.stats["strikes"],
            "scores": {spec.name: score},
            "strategies": {spec.name: spec.strategy},
        }
        if self.collect_game_history:
            game_entry["history"] = game.history

        self.statistics.append(game_entry)

        if winner is not None:
            self.aggregate["wins_by_player"][winner] += 1
            self.aggregate["wins_by_strategy"][spec.strategy] += 1

        self.aggregate["games_by_player"][spec.name] += 1
        self.aggregate["games_by_strategy"][spec.strategy] += 1
        self.aggregate["total_scores_by_player"][spec.name] += score
        self.aggregate["total_scores_by_strategy"][spec.strategy] += score
        self.aggregate["total_turns_by_player"][spec.name] += turns
        self.aggregate["total_turns_by_strategy"][spec.strategy] += turns
        self.aggregate["total_rolls_by_player"][spec.name] += game.stats["rolls"]
        self.aggregate["total_rolls_by_strategy"][spec.strategy] += game.stats["rolls"]
        self._update_turn_bounds(
            spec.name,
            turns,
            self.aggregate["min_turns_by_player"],
            self.aggregate["max_turns_by_player"],
        )
        self._update_turn_bounds(
            spec.strategy,
            turns,
            self.aggregate["min_turns_by_strategy"],
            self.aggregate["max_turns_by_strategy"],
        )
        self.aggregate["fouls"] += game.stats["fouls"]
        self.aggregate["strikes"] += game.stats["strikes"]
        self.aggregate["rolls"] += game.stats["rolls"]
        self.aggregate["turns"] += game.stats["turns"]

    def play_series(self, spec: PlayerSpec, series_index: int, game_index_start: int) -> int:
        game_index = game_index_start

        for series_game_index in range(1, self.tours + 1):
            game_seed = self.random.randrange(0, 2**32)
            player = self.create_player(spec)
            game = Game(
                [player],
                rng=random.Random(game_seed),
                collect_history=self.collect_game_history,
            )
            winner = game.start()
            self.record_game(game_index, series_index, series_game_index, spec, game, winner)
            game_index += 1

        return game_index

    def start(self) -> None:
        game_index = 1
        for series_index, spec in enumerate(self.player_specs, start=1):
            game_index = self.play_series(spec, series_index, game_index)

    def _average_by_player(self, total_key: str, count_key: str) -> dict[str, float]:
        return {
            name: round(self.aggregate[total_key][name] / self.aggregate[count_key][name], 1)
            for name in self.aggregate[count_key]
            if self.aggregate[count_key][name]
        }

    def _bounds_by_player(self, key: str) -> dict[str, int]:
        return dict(self.aggregate[key])

    def build_summary(self) -> dict[str, Any]:
        total_games = len(self.statistics)
        average_scores = self._average_by_player("total_scores_by_player", "games_by_player")
        average_turns = self._average_by_player("total_turns_by_player", "games_by_player")
        average_rolls = self._average_by_player("total_rolls_by_player", "games_by_player")
        average_scores_by_strategy = self._average_by_player("total_scores_by_strategy", "games_by_strategy")
        average_turns_by_strategy = self._average_by_player("total_turns_by_strategy", "games_by_strategy")
        average_rolls_by_strategy = self._average_by_player("total_rolls_by_strategy", "games_by_strategy")

        winrate_by_player = (
            {
                spec.name: round(
                    self.aggregate["wins_by_player"].get(spec.name, 0)
                    / self.aggregate["games_by_player"].get(spec.name, 1)
                    * 100,
                    1,
                )
                for spec in self.player_specs
            }
            if total_games
            else {}
        )

        strategy_names = sorted({spec.strategy for spec in self.player_specs})
        winrate_by_strategy = (
            {
                strategy: round(
                    self.aggregate["wins_by_strategy"].get(strategy, 0)
                    / self.aggregate["games_by_strategy"].get(strategy, 1)
                    * 100,
                    1,
                )
                for strategy in strategy_names
            }
            if total_games
            else {}
        )

        average_turns_to_win_by_player = average_turns
        average_turns_to_win_by_strategy = average_turns_by_strategy

        return {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "total_games": total_games,
            "seed": self.seed,
            "players": [spec.name for spec in self.player_specs],
            "player_specs": [spec.to_dict() for spec in self.player_specs],
            "average_score_by_player": average_scores,
            "average_rolls_by_player": average_rolls,
            "average_turns_to_win_by_player": average_turns_to_win_by_player,
            "turns_to_win_by_player": average_turns_to_win_by_player,
            "min_turns_to_win_by_player": self._bounds_by_player("min_turns_by_player"),
            "max_turns_to_win_by_player": self._bounds_by_player("max_turns_by_player"),
            "games_by_player": dict(self.aggregate["games_by_player"]),
            "wins_by_player": dict(self.aggregate["wins_by_player"]),
            "winrate_by_player": winrate_by_player,
            "average_score_by_strategy": average_scores_by_strategy,
            "average_rolls_by_strategy": average_rolls_by_strategy,
            "average_turns_to_win_by_strategy": average_turns_to_win_by_strategy,
            "turns_to_win_by_strategy": average_turns_to_win_by_strategy,
            "min_turns_to_win_by_strategy": self._bounds_by_player("min_turns_by_strategy"),
            "max_turns_to_win_by_strategy": self._bounds_by_player("max_turns_by_strategy"),
            "games_by_strategy": dict(self.aggregate["games_by_strategy"]),
            "wins_by_strategy": dict(self.aggregate["wins_by_strategy"]),
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

    def export_payload(self, mode: str = "full") -> dict[str, Any]:
        payload = {"schema_version": EXPORT_SCHEMA_VERSION}
        summary = self.build_summary()

        if mode == "summary":
            payload["summary"] = summary
            return payload

        if mode == "per-game":
            payload["games"] = self.statistics
            return payload

        payload["summary"] = summary
        payload["games"] = self.statistics
        return payload

    def export_json(self, output_path: str | Path, mode: str = "full") -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.export_payload(mode=mode)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def export_csv(self, output_path: str | Path, mode: str = "full") -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as file:
            if mode == "summary":
                writer = csv.DictWriter(file, fieldnames=["section", "name", "value"])
                writer.writeheader()
                summary = self.build_summary()
                scalar_fields = {
                    "schema_version": summary["schema_version"],
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

                for name, value in summary["average_rolls_by_player"].items():
                    writer.writerow({"section": "average_rolls_by_player", "name": name, "value": value})

                for name, value in summary["average_turns_to_win_by_player"].items():
                    writer.writerow({"section": "average_turns_to_win_by_player", "name": name, "value": value})

                for name, value in summary["min_turns_to_win_by_player"].items():
                    writer.writerow({"section": "min_turns_to_win_by_player", "name": name, "value": value})

                for name, value in summary["max_turns_to_win_by_player"].items():
                    writer.writerow({"section": "max_turns_to_win_by_player", "name": name, "value": value})

                for name, value in summary["games_by_player"].items():
                    writer.writerow({"section": "games_by_player", "name": name, "value": value})

                for name, value in summary["wins_by_player"].items():
                    writer.writerow({"section": "wins_by_player", "name": name, "value": value})

                for name, value in summary["winrate_by_player"].items():
                    writer.writerow({"section": "winrate_by_player", "name": name, "value": value})

                for name, value in summary["average_score_by_strategy"].items():
                    writer.writerow({"section": "average_score_by_strategy", "name": name, "value": value})

                for name, value in summary["average_rolls_by_strategy"].items():
                    writer.writerow({"section": "average_rolls_by_strategy", "name": name, "value": value})

                for name, value in summary["average_turns_to_win_by_strategy"].items():
                    writer.writerow({"section": "average_turns_to_win_by_strategy", "name": name, "value": value})

                for name, value in summary["min_turns_to_win_by_strategy"].items():
                    writer.writerow({"section": "min_turns_to_win_by_strategy", "name": name, "value": value})

                for name, value in summary["max_turns_to_win_by_strategy"].items():
                    writer.writerow({"section": "max_turns_to_win_by_strategy", "name": name, "value": value})

                for name, value in summary["games_by_strategy"].items():
                    writer.writerow({"section": "games_by_strategy", "name": name, "value": value})

                for name, value in summary["wins_by_strategy"].items():
                    writer.writerow({"section": "wins_by_strategy", "name": name, "value": value})

                for name, value in summary["winrate_by_strategy"].items():
                    writer.writerow({"section": "winrate_by_strategy", "name": name, "value": value})
                return

            fieldnames = [
                "game",
                "series",
                "series_game",
                "player",
                "strategy",
                "threshold",
                "winner",
                "score",
                "turns",
                "rolls",
                "fouls",
                "strikes",
            ]

            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for game in self.statistics:
                row = {
                    "game": game["game"],
                    "series": game["series"],
                    "series_game": game["series_game"],
                    "player": game["player"],
                    "strategy": game["strategy"],
                    "threshold": game["threshold"],
                    "winner": game["winner"],
                    "score": game["score"],
                    "turns": game["turns"],
                    "rolls": game["rolls"],
                    "fouls": game["fouls"],
                    "strikes": game["strikes"],
                }

                writer.writerow(row)

    def report(self) -> None:
        summary = self.build_summary()
        total_games = summary["total_games"]

        print(f"Сыграно партий: {total_games}")
        if self.seed is not None:
            print(f"Seed турнира: {self.seed}")
        print("Состав аудита:")
        for spec in self.player_specs:
            print(f"- {spec.name}: {spec.strategy} (threshold={spec.threshold})")

        if total_games == 0:
            print("Турнир ещё не запускался.")
            return

        print()
        print("Сводка по аудиту:")
        print(f"- Среднее число бросков за игру: {summary['average_rolls_per_game']}")
        print(f"- Среднее число ходов за игру: {summary['average_turns_per_game']}")
        print(f"- Частота булок: {summary['foul_rate_per_roll']}%")
        print(f"- Частота небиток: {summary['strike_rate_per_roll']}%")

        print()
        print("Результаты по стратегиям:")
        for name in sorted(
            summary["average_turns_to_win_by_player"],
            key=lambda player_name: (
                summary["average_turns_to_win_by_player"][player_name],
                summary["average_score_by_player"][player_name],
            ),
        ):
            print(
                f"- {name}: средние ходы до победы {summary['average_turns_to_win_by_player'][name]}, "
                f"средний счёт {summary['average_score_by_player'][name]}"
            )
