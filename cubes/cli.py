from __future__ import annotations

import argparse
from pathlib import Path

from .reporting import build_charts, load_csv_report, load_json_report
from .settings import TOURS
from .tournament import Tournament


def build_main_parser():
    parser = argparse.ArgumentParser(
        description="Аудит стратегий в игре 'Кубовая Тыща'."
    )
    parser.add_argument(
        "--tours",
        type=int,
        default=TOURS,
        help=f"Количество партий на каждую стратегию. По умолчанию: {TOURS}.",
    )
    parser.add_argument(
        "--player",
        action="append",
        default=[],
        help=(
            "Добавить стратегию в формате strategy[:threshold][:name]. "
            "Примеры: greedy, cautious:80, hopness:70:Надеющийся, adaptive:60."
        ),
    )
    parser.add_argument("--seed", type=int, help="Сид для воспроизводимого аудита.")
    parser.add_argument(
        "--json-out",
        help="Путь к JSON-файлу с итоговой сводкой и статистикой по партиям.",
    )
    parser.add_argument(
        "--csv-out",
        help="Путь к CSV-файлу со статистикой по каждой партии.",
    )
    export_mode = parser.add_mutually_exclusive_group()
    export_mode.add_argument("--summary-only", action="store_true", help="Экспортировать только итоговую сводку.")
    export_mode.add_argument("--per-game-only", action="store_true", help="Экспортировать только статистику по отдельным партиям.")
    parser.add_argument(
        "--show-game-history",
        action="store_true",
        help="Сохранять историю ходов каждой партии в JSON-экспорт.",
    )
    return parser


def build_plot_parser():
    parser = argparse.ArgumentParser(
        description="Построение SVG-графиков по JSON/CSV-отчёту аудита."
    )
    parser.add_argument("--json", help="Путь к JSON-отчёту турнира.")
    parser.add_argument("--csv", help="Путь к CSV-отчёту турнира.")
    parser.add_argument("--out-dir", default="reports/charts", help="Директория для сохранения SVG-графиков.")
    return parser


def main():
    parser = build_main_parser()
    args = parser.parse_args()

    tournament = Tournament(
        tours=args.tours,
        strategy_specs=args.player or None,
        collect_game_history=args.show_game_history,
        seed=args.seed,
    )
    tournament.start()
    tournament.report()

    export_mode = "full"
    if args.summary_only:
        export_mode = "summary"
    elif args.per_game_only:
        export_mode = "per-game"

    if args.json_out:
        tournament.export_json(args.json_out, mode=export_mode)
        print(f"JSON-отчёт сохранён в {args.json_out}")

    if args.csv_out:
        tournament.export_csv(args.csv_out, mode=export_mode)
        print(f"CSV-отчёт сохранён в {args.csv_out}")


def plot_main():
    parser = build_plot_parser()
    args = parser.parse_args()

    if not args.json and not args.csv:
        parser.error("Нужно указать хотя бы один из источников: --json или --csv")

    summary = None
    games = []

    if args.json:
        summary, games = load_json_report(args.json)

    if args.csv and (summary is None or not games):
        summary, games = load_csv_report(args.csv)

    out_dir = Path(args.out_dir)
    build_charts(summary, games, out_dir)
    print(f"SVG-графики сохранены в {out_dir}")
