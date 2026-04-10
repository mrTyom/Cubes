# Кубовая Тыща

CLI-проект для симуляции партии и аудита стратегий по игре "Кубовая Тыща". Кодовая база собрана как Python-пакет `cubes`, а корневые скрипты `main.py` и `plot_report.py` оставлены как совместимые точки входа.

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --seed 42 --json-out reports/report.json --csv-out reports/report.csv
python plot_report.py --json reports/report.json --out-dir reports/charts
```

Проект использует только стандартную библиотеку Python, поэтому `requirements.txt` не тянет внешние зависимости.

## Запуск тестов

Официальный способ запуска:

```bash
python -m unittest discover -s tests -v
```

Именно этот сценарий используется в CI.

## Структура проекта

- `cubes/game.py` — игровое ядро, правила броска, булки, небитки и бочки.
- `cubes/strategies.py` — стратегии, registry алиасов и фабрика создания игроков.
- `cubes/tournament.py` — orchestration аудита, агрегаты и экспорт.
- `cubes/reporting.py` — загрузка отчётов и генерация SVG-графиков.
- `cubes/models.py` — доменные dataclass-модели и типизированные записи истории.
- `main.py`, `plot_report.py` — совместимые CLI-оболочки.

## Правила игры

1. Побеждает участник, набравший 1000 или больше очков.
2. Игроки ходят по очереди.
3. У каждого игрока есть три броска и 5 кубиков.
4. Если на всех кубах есть очки, это небитка: сумма не сгорает и игрок получает ещё три броска.
5. Если очков за бросок не выпало вообще, это булка: все очки текущего хода сгорают.
6. В каждом броске игрок может записать очки или отложить любое количество очковых кубов и перебросить остальные.

### Комбинации очков

- 5 одинаковых кубов — 1000 очков.
- 4 одинаковых куба — `10x + 100` очков.
- 3 одинаковых куба — `10x` очков, кроме трёх единиц: это 100 очков.
- Один куб: единица — 10 очков, пятёрка — 5 очков.
- Дубли из двоек, троек, четвёрок и шестёрок очков не дают, но могут закрывать небитку, если остальные кубы очковые.

### Бочка

Если игрок набрал от 900 до 999 очков, сумма замораживается. Дальше нужно закрыться до 1000 в рамках одного хода; иначе счёт возвращается к замороженному значению.

## Команды

```bash
python main.py
python main.py --tours 200
python main.py --player greedy --player cautious:80 --player hopness:70:Риск
python main.py --seed 42 --json-out reports/report.json --csv-out reports/report.csv
python main.py --seed 42 --summary-only --json-out reports/summary.json
python main.py --seed 42 --show-game-history --json-out reports/history.json
python plot_report.py --json reports/report.json --out-dir reports/charts
python plot_report.py --csv reports/report.csv --out-dir reports/charts
```

По умолчанию `main.py` запускает независимые серии партий для каждой стратегии, а `--tours` задаёт число партий **на каждую** стратегию.

Формат `--player`:

- `greedy`
- `cautious:80`
- `hopness:70:ИмяИгрока`
- `adaptive:60:ИмяИгрока`
- `barrel:55:ИмяИгрока`

Неизвестная стратегия теперь считается ошибкой конфигурации и приводит к `ValueError`, а не к молчаливому переходу на жадную стратегию.

## Стратегии

- `greedy` — берёт максимум здесь и сейчас и почти всегда сразу записывает ход. Базовый `threshold`: `1`.
- `cautious` — раньше фиксирует очки и сильнее учитывает остаток бросков и риск булки. Базовый `threshold`: `50`.
- `hopness` — играет на небитку и старается оставлять минимум кубов на столе. Базовый `threshold`: `70`.
- `adaptive` — двигает порог записи в зависимости от риска булки и количества оставшихся бросков. Базовый `threshold`: `60`.
- `barrel` — отдельно оптимизирует вход в бочку и закрытие партии. Базовый `threshold`: `55`.

Registry стратегий находится в `cubes/strategies.py`. Если добавляется новая стратегия, нужно:

1. Добавить класс стратегии.
2. Зарегистрировать её в `STRATEGY_REGISTRY`.
3. При необходимости добавить тесты на алиасы, default threshold и поведение.
4. Обновить README, если стратегия становится частью публичного CLI.

## Формат экспорта

### JSON

- Верхний уровень содержит `schema_version`.
- В полном экспорте есть `summary` и `games`.
- В `summary` содержатся агрегаты аудита и `player_specs`.
- При `--show-game-history` каждая игра получает поле `history`.

Пример полей в `history`:

- `move`
- `step`
- `player`
- `roll`
- `cube_count`
- `hold`
- `hold_score`
- `turn_score`
- `total_score`
- `check_strike`
- `check_foul`
- `banked`

### CSV

- `summary`-режим сохраняет строки вида `section,name,value`.
- `full` и `per-game` сохраняют построчную статистику по каждой партии.
- История ходов в CSV сейчас не выгружается; для неё используйте JSON.

Загрузчики в `plot_report.py` и `cubes/reporting.py` сохраняют обратную совместимость со старыми CSV/JSON без `schema_version`.

## Графики

`plot_report.py` строит SVG-графики:

- `turns_to_win_by_player.svg`
- `average_score_by_player.svg`
- `scores_by_game.svg`

`scores_by_game.svg` сейчас особенно полезен для старых многопользовательских отчётов; в новом режиме аудита основной график — `turns_to_win_by_player.svg`.

## Правила качества

- Основной стиль имён в коде и в JSON history — `snake_case`.
- Публичные стратегии регистрируются централизованно через registry.
- Изменения в экспортных схемах должны сопровождаться обновлением `schema_version`, README и тестов загрузчиков.
- Новые пользовательские сценарии CLI должны иметь smoke-test или unit-тест.
