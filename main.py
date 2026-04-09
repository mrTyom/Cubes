import argparse

from settings import TOURS
from tournament import Tournament


def build_parser():
    parser = argparse.ArgumentParser(
        description="Симуляция турнира по игре 'Кубовая Тыща'."
    )
    parser.add_argument(
        "--tours",
        type=int,
        default=TOURS,
        help=f"Количество партий в турнире. По умолчанию: {TOURS}.",
    )
    parser.add_argument(
        "--player",
        action="append",
        default=[],
        help=(
            "Добавить игрока в формате strategy[:threshold][:name]. "
            "Примеры: greedy, cautious:80, hopness:70:Надеющийся, adaptive:60."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Сид для воспроизводимого турнира.",
    )
    parser.add_argument(
        "--json-out",
        help="Путь к JSON-файлу с итоговой сводкой и статистикой по партиям.",
    )
    parser.add_argument(
        "--csv-out",
        help="Путь к CSV-файлу со статистикой по каждой партии.",
    )
    export_mode = parser.add_mutually_exclusive_group()
    export_mode.add_argument(
        "--summary-only",
        action="store_true",
        help="Экспортировать только итоговую сводку.",
    )
    export_mode.add_argument(
        "--per-game-only",
        action="store_true",
        help="Экспортировать только статистику по отдельным партиям.",
    )
    parser.add_argument(
        "--show-game-history",
        action="store_true",
        help="Сохранять историю бросков каждой партии. Замедляет турнир.",
    )
    return parser


def main():
    parser = build_parser()
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


if __name__ == "__main__":
    main()
