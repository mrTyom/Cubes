from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_SCHEMA_VERSION = 3


def sanitize_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def svg_bar_chart(title, labels, values, output_path, color="#3B82F6"):
    width = 1000
    height = 600
    margin_left = 180
    margin_right = 40
    margin_top = 70
    margin_bottom = 110
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_value = max(values) if values else 1
    max_value = max(max_value, 1)
    bar_gap = 14
    bar_width = max(18, int((plot_width - bar_gap * (len(values) - 1)) / max(len(values), 1)))

    bars = []
    labels_svg = []
    values_svg = []

    for index, (label, value) in enumerate(zip(labels, values)):
        x = margin_left + index * (bar_width + bar_gap)
        bar_height = 0 if max_value == 0 else (value / max_value) * plot_height
        y = margin_top + plot_height - bar_height
        bars.append(
            f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" '
            f'fill="{color}" rx="6" ry="6" />'
        )
        labels_svg.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{height - 55}" text-anchor="end" '
            f'font-size="14" transform="rotate(-35 {x + bar_width / 2:.2f},{height - 55})">{label}</text>'
        )
        values_svg.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y - 8:.2f}" text-anchor="middle" font-size="13">{value}</text>'
        )

    grid = []
    for step in range(6):
        y = margin_top + plot_height - plot_height * step / 5
        tick_value = round(max_value * step / 5, 1)
        grid.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#D1D5DB" stroke-dasharray="4 6" />')
        grid.append(f'<text x="{margin_left - 15}" y="{y + 5:.2f}" text-anchor="end" font-size="13">{tick_value}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="#FFFFFF" />
<text x="{width / 2}" y="36" text-anchor="middle" font-size="28" font-weight="700">{title}</text>
<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#111827" />
<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#111827" />
{''.join(grid)}
{''.join(bars)}
{''.join(labels_svg)}
{''.join(values_svg)}
</svg>"""
    Path(output_path).write_text(svg, encoding="utf-8")


def svg_line_chart(title, series, output_path):
    width = 1100
    height = 650
    margin_left = 80
    margin_right = 40
    margin_top = 70
    margin_bottom = 80
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    all_values = [value for _, values in series for value in values]
    max_value = max(all_values) if all_values else 1
    max_value = max(max_value, 1)
    max_points = max((len(values) for _, values in series), default=1)
    palette = ["#2563EB", "#DC2626", "#16A34A", "#D97706", "#7C3AED", "#0891B2"]

    grid = []
    for step in range(6):
        y = margin_top + plot_height - plot_height * step / 5
        tick_value = round(max_value * step / 5, 1)
        grid.append(f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" stroke="#E5E7EB" stroke-dasharray="4 6" />')
        grid.append(f'<text x="{margin_left - 10}" y="{y + 5:.2f}" text-anchor="end" font-size="12">{tick_value}</text>')

    x_ticks = []
    tick_count = min(max_points, 10)
    for idx in range(tick_count):
        game_no = 1 if tick_count == 1 else round(1 + (max_points - 1) * idx / (tick_count - 1))
        x = margin_left if max_points <= 1 else margin_left + plot_width * (game_no - 1) / (max_points - 1)
        x_ticks.append(f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{margin_top + plot_height}" stroke="#F3F4F6" />')
        x_ticks.append(f'<text x="{x:.2f}" y="{height - 30}" text-anchor="middle" font-size="12">{game_no}</text>')

    lines = []
    legend = []
    for index, (name, values) in enumerate(series):
        color = palette[index % len(palette)]
        points = []
        for pos, value in enumerate(values):
            x = margin_left if len(values) <= 1 else margin_left + plot_width * pos / (len(values) - 1)
            y = margin_top + plot_height - (value / max_value) * plot_height
            points.append(f"{x:.2f},{y:.2f}")

        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(points)}" />')
        legend_y = margin_top + 20 + index * 24
        legend.append(f'<rect x="{width - 220}" y="{legend_y - 12}" width="18" height="18" fill="{color}" rx="3" ry="3" />')
        legend.append(f'<text x="{width - 195}" y="{legend_y + 2}" font-size="14">{name}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="#FFFFFF" />
<text x="{width / 2}" y="36" text-anchor="middle" font-size="28" font-weight="700">{title}</text>
<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#111827" />
<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#111827" />
{''.join(grid)}
{''.join(x_ticks)}
{''.join(lines)}
{''.join(legend)}
</svg>"""
    Path(output_path).write_text(svg, encoding="utf-8")


def load_json_report(path: str | Path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("summary"), payload.get("games", [])


def _parse_number(value: str) -> float | int | str:
    try:
        parsed = float(value)
    except ValueError:
        return value

    if parsed.is_integer():
        return int(parsed)
    return parsed


def load_csv_report(path: str | Path):
    with Path(path).open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        return None, []

    if {"section", "name", "value"}.issubset(rows[0].keys()):
        summary: dict[str, Any] = {
            "average_score_by_player": {},
            "winrate_by_player": {},
            "winrate_by_strategy": {},
        }

        for row in rows:
            section = row["section"]
            name = row["name"]
            raw_value = row["value"]
            value = _parse_number(raw_value)

            if section == "summary":
                summary[name] = value
            else:
                summary.setdefault(section, {})[name] = value

        if "schema_version" not in summary:
            summary["schema_version"] = 1

        return summary, []

    if {"player", "strategy", "score", "turns"}.issubset(rows[0].keys()):
        games = []
        for row in rows:
            player_name = row["player"]
            strategy_name = row["strategy"]
            score = float(row["score"]) if row["score"] != "" else 0.0
            turns = int(float(row["turns"]))
            game_entry = {
                "game": int(float(row["game"])),
                "series": int(float(row["series"])) if row.get("series") else 0,
                "series_game": int(float(row["series_game"])) if row.get("series_game") else 0,
                "player": player_name,
                "strategy": strategy_name,
                "threshold": int(float(row["threshold"])) if row.get("threshold") else 0,
                "winner": row["winner"],
                "score": score,
                "turns": turns,
                "rolls": int(float(row["rolls"])),
                "fouls": int(float(row["fouls"])),
                "strikes": int(float(row["strikes"])),
                "scores": {player_name: score},
                "strategies": {player_name: strategy_name},
            }
            games.append(game_entry)

        grouped_by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
        grouped_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
        player_specs: dict[str, dict[str, Any]] = {}
        for game in games:
            grouped_by_player[game["player"]].append(game)
            grouped_by_strategy[game["strategy"]].append(game)
            player_specs.setdefault(
                game["player"],
                {
                    "name": game["player"],
                    "strategy": game["strategy"],
                    "threshold": game["threshold"],
                },
            )

        def build_summary_map(grouped: dict[str, list[dict[str, Any]]], field: str) -> dict[str, float]:
            return {
                name: round(sum(game[field] for game in items) / len(items), 1)
                for name, items in grouped.items()
                if items
            }

        def build_count_map(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
            return {name: len(items) for name, items in grouped.items()}

        def build_extreme_map(grouped: dict[str, list[dict[str, Any]]], fn) -> dict[str, int]:
            return {name: fn(game["turns"] for game in items) for name, items in grouped.items() if items}

        games_by_player = build_count_map(grouped_by_player)
        games_by_strategy = build_count_map(grouped_by_strategy)
        wins_by_player = {
            name: sum(1 for game in items if game["winner"] == name)
            for name, items in grouped_by_player.items()
        }
        wins_by_strategy = {
            name: sum(1 for game in items if game["winner"] == game["player"])
            for name, items in grouped_by_strategy.items()
        }

        summary = {
            "schema_version": 3,
            "total_games": len(games),
            "players": list(grouped_by_player.keys()),
            "player_specs": list(player_specs.values()),
            "average_score_by_player": build_summary_map(grouped_by_player, "score"),
            "average_rolls_by_player": build_summary_map(grouped_by_player, "rolls"),
            "average_turns_to_win_by_player": build_summary_map(grouped_by_player, "turns"),
            "turns_to_win_by_player": build_summary_map(grouped_by_player, "turns"),
            "min_turns_to_win_by_player": build_extreme_map(grouped_by_player, min),
            "max_turns_to_win_by_player": build_extreme_map(grouped_by_player, max),
            "games_by_player": games_by_player,
            "wins_by_player": wins_by_player,
            "winrate_by_player": {
                name: round(wins_by_player[name] / games_by_player[name] * 100, 1)
                for name in games_by_player
                if games_by_player[name]
            },
            "average_score_by_strategy": build_summary_map(grouped_by_strategy, "score"),
            "average_rolls_by_strategy": build_summary_map(grouped_by_strategy, "rolls"),
            "average_turns_to_win_by_strategy": build_summary_map(grouped_by_strategy, "turns"),
            "turns_to_win_by_strategy": build_summary_map(grouped_by_strategy, "turns"),
            "min_turns_to_win_by_strategy": build_extreme_map(grouped_by_strategy, min),
            "max_turns_to_win_by_strategy": build_extreme_map(grouped_by_strategy, max),
            "games_by_strategy": games_by_strategy,
            "wins_by_strategy": wins_by_strategy,
            "winrate_by_strategy": {
                name: round(wins_by_strategy[name] / games_by_strategy[name] * 100, 1)
                for name in games_by_strategy
                if games_by_strategy[name]
            },
            "average_rolls_per_game": round(sum(game["rolls"] for game in games) / len(games), 1),
            "average_turns_per_game": round(sum(game["turns"] for game in games) / len(games), 1),
            "foul_rate_per_roll": round(sum(game["fouls"] for game in games) / sum(game["rolls"] for game in games) * 100, 1),
            "strike_rate_per_roll": round(sum(game["strikes"] for game in games) / sum(game["rolls"] for game in games) * 100, 1),
            "fouls": sum(game["fouls"] for game in games),
            "strikes": sum(game["strikes"] for game in games),
            "rolls": sum(game["rolls"] for game in games),
            "turns": sum(game["turns"] for game in games),
        }
        return summary, games

    games = []
    for row in rows:
        scores = {key.split("::", 1)[1]: float(value) for key, value in row.items() if key.startswith("score::") and value != ""}
        strategies = {key.split("::", 1)[1]: value for key, value in row.items() if key.startswith("strategy::") and value != ""}
        games.append(
            {
                "game": int(row["game"]),
                "winner": row["winner"],
                "rolls": int(row["rolls"]),
                "turns": int(row["turns"]),
                "fouls": int(row["fouls"]),
                "strikes": int(row["strikes"]),
                "scores": scores,
                "strategies": strategies,
            }
        )

    winner_count = Counter(game["winner"] for game in games)
    total_games = len(games)
    average_score = {}
    if games:
        for name in games[0]["scores"]:
            average_score[name] = round(sum(game["scores"][name] for game in games) / total_games, 1)

    summary = {
        "schema_version": 1,
        "total_games": total_games,
        "average_score_by_player": average_score,
        "winrate_by_player": {
            name: round(count / total_games * 100, 1) for name, count in winner_count.items()
        },
        "average_rolls_per_game": round(sum(game["rolls"] for game in games) / total_games, 1),
        "average_turns_per_game": round(sum(game["turns"] for game in games) / total_games, 1),
        "foul_rate_per_roll": round(sum(game["fouls"] for game in games) / sum(game["rolls"] for game in games) * 100, 1),
        "strike_rate_per_roll": round(sum(game["strikes"] for game in games) / sum(game["rolls"] for game in games) * 100, 1),
    }
    return summary, games


def build_charts(summary, games, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    if summary:
        turns_summary = summary.get("average_turns_to_win_by_player") or summary.get("turns_to_win_by_player")
        if turns_summary:
            ordered_names = sorted(turns_summary, key=lambda name: turns_summary[name])
            values = [turns_summary[name] for name in ordered_names]
            svg_bar_chart(
                "Среднее число ходов до победы",
                ordered_names,
                values,
                out_dir / "turns_to_win_by_player.svg",
                color="#16A34A",
            )
        elif summary.get("winrate_by_player"):
            names = list(summary["winrate_by_player"].keys())
            values = [summary["winrate_by_player"][name] for name in names]
            svg_bar_chart("Winrate по игрокам", names, values, out_dir / "winrate_by_player.svg", color="#16A34A")

    if summary and summary.get("average_score_by_player"):
        names = list(summary["average_score_by_player"].keys())
        values = [summary["average_score_by_player"][name] for name in names]
        svg_bar_chart("Средний счёт по игрокам", names, values, out_dir / "average_score_by_player.svg", color="#2563EB")

    if games:
        if "player" in games[0]:
            grouped_scores: dict[str, list[float]] = defaultdict(list)
            for game in games:
                grouped_scores[game["player"]].append(game["score"])
            series = list(grouped_scores.items())
            svg_line_chart("Счёт игроков по партиям", series, out_dir / "scores_by_game.svg")
        elif games[0].get("scores"):
            player_names = list(games[0]["scores"].keys())
            series = []
            for name in player_names:
                values = [game["scores"][name] for game in games]
                series.append((name, values))

            svg_line_chart("Счёт игроков по партиям", series, out_dir / "scores_by_game.svg")

            winner_count = Counter(game["winner"] for game in games)
            labels = list(winner_count.keys())
            values = [winner_count[label] for label in labels]
            svg_bar_chart("Победы по игрокам", labels, values, out_dir / "wins_by_player.svg", color="#DC2626")
