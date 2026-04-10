from __future__ import annotations

import random
from collections import Counter

from .models import HoldOption, Player, TurnLogEntry, TurnState
from .settings import BARREL, CUBES, EDGES, STEPS, WIN


class Game:
    def __init__(
        self,
        player_set: list[Player],
        rng: random.Random | None = None,
        collect_history: bool = True,
    ):
        self.player_set = player_set
        self.rng = rng or random.Random()
        self.collect_history = collect_history
        self.history: list[dict] = []
        self.winner: str | None = None
        self.record = 0
        self.move_number = 0
        self.stats = {
            "rolls": 0,
            "fouls": 0,
            "strikes": 0,
            "turns": 0,
        }

        for player in self.player_set:
            player.total_score = 0
            player.barrel_score = None

    @staticmethod
    def cube_count(cube_set: list[int]) -> dict[int, int]:
        return dict(Counter(cube_set))

    @staticmethod
    def grade(cube_count: dict[int, int]) -> int:
        score = 0

        for key, value in cube_count.items():
            if value == 5:
                score += 1000
            elif value == 4:
                score += key * 10 + 100
            elif value == 3:
                score += 100 if key == 1 else key * 10
            elif value == 2:
                if key == 5:
                    score += 10
                elif key == 1:
                    score += 20
            elif value == 1:
                if key == 5:
                    score += 5
                elif key == 1:
                    score += 10

        return score

    @staticmethod
    def is_scoring_face(face: int, count: int) -> bool:
        if count >= 3:
            return True
        if face in (1, 5) and count >= 1:
            return True
        return False

    @classmethod
    def hold_options(cls, cube_count: dict[int, int]) -> list[HoldOption]:
        faces = sorted(cube_count)
        options: dict[tuple[tuple[int, int], ...], HoldOption] = {}

        def backtrack(index: int, current: dict[int, int]) -> None:
            if index == len(faces):
                if not current:
                    return

                if not all(
                    cls.is_scoring_face(face, count)
                    for face, count in current.items()
                ):
                    return

                score = cls.grade(current)
                if score <= 0:
                    return

                held_counts = dict(sorted(current.items()))
                options[tuple(held_counts.items())] = HoldOption(
                    held_counts=held_counts,
                    score=score,
                    used_dice=sum(held_counts.values()),
                )
                return

            face = faces[index]
            max_count = cube_count[face]

            for selected in range(max_count + 1):
                if selected:
                    current[face] = selected
                else:
                    current.pop(face, None)

                backtrack(index + 1, current)

            current.pop(face, None)

        backtrack(0, {})
        return list(options.values())

    @staticmethod
    def check_strike(cube_count: dict[int, int]) -> bool:
        has_score = False
        used_dice = 0

        for face, count in cube_count.items():
            if count >= 3:
                has_score = True
                used_dice += count
            elif face in (1, 5):
                has_score = True
                used_dice += count
            elif count >= 2:
                used_dice += count

        return has_score and used_dice == sum(cube_count.values())

    @staticmethod
    def check_foul(score: int) -> bool:
        return score == 0

    def max_score(self) -> None:
        leader = max(self.player_set, key=lambda player: player.total_score)
        self.winner = leader.name
        self.record = leader.total_score

    def roll(self, cubes: int) -> list[int]:
        return [self.rng.randint(1, EDGES) for _ in range(cubes)]

    def raffle(self, cubes: int) -> tuple[list[int], dict[int, int], int]:
        cube_set = self.roll(cubes)
        cube_set_count = self.cube_count(cube_set)
        score = self.grade(cube_set_count)
        return cube_set, cube_set_count, score

    def build_turn_state(
        self,
        player: Player,
        turn_score: int,
        remaining_cubes: int,
        rolls_left: int,
    ) -> TurnState:
        frozen_score = (
            player.barrel_score if player.barrel_score is not None else player.total_score
        )
        return TurnState(
            total_score=player.total_score,
            turn_score=turn_score,
            remaining_cubes=remaining_cubes,
            rolls_left=rolls_left,
            barrel_active=player.barrel_score is not None,
            frozen_score=frozen_score,
        )

    def apply_bank(self, player: Player, turn_score: int) -> bool:
        if player.barrel_score is not None:
            if player.barrel_score + turn_score >= WIN:
                player.total_score = player.barrel_score + turn_score
                player.barrel_score = None
                return True

            player.total_score = player.barrel_score
            return False

        player.total_score += turn_score

        if BARREL <= player.total_score < WIN:
            player.barrel_score = player.total_score

        return player.total_score >= WIN

    def play_turn(self, player: Player) -> bool:
        turn_score = 0
        remaining_cubes = CUBES
        rolls_left = STEPS
        closed_game = False
        self.stats["turns"] += 1

        while rolls_left > 0:
            self.move_number += 1
            roll_index = STEPS - rolls_left + 1
            cube_set, cube_set_count, roll_score = self.raffle(remaining_cubes)
            strike = self.check_strike(cube_set_count)
            foul = self.check_foul(roll_score)
            self.stats["rolls"] += 1
            if strike:
                self.stats["strikes"] += 1
            if foul:
                self.stats["fouls"] += 1

            if foul:
                turn_score = 0
                self.log_row(
                    TurnLogEntry(
                        move=self.move_number,
                        step=roll_index,
                        player=player.name,
                        roll=cube_set,
                        cube_count=cube_set_count,
                        hold={},
                        hold_score=0,
                        turn_score=turn_score,
                        total_score=player.total_score,
                        check_strike=strike,
                        check_foul=foul,
                        banked=False,
                    )
                )
                return False

            hold_options = self.hold_options(cube_set_count)
            turn_state = self.build_turn_state(player, turn_score, remaining_cubes, rolls_left)
            hold = player.strategy.choose_hold(turn_state, cube_set_count, hold_options)

            if hold is None or hold.score <= 0:
                raise ValueError(f"{player.name} selected an invalid hold option")

            turn_score += hold.score

            if strike:
                remaining_cubes = CUBES
                rolls_left = STEPS
            else:
                remaining_cubes -= hold.used_dice
                rolls_left -= 1

                if remaining_cubes == 0:
                    remaining_cubes = CUBES
                    rolls_left = STEPS

            decision_state = self.build_turn_state(player, turn_score, remaining_cubes, rolls_left)
            banked = player.strategy.should_bank(decision_state)

            if player.barrel_score is not None and player.barrel_score + turn_score < WIN:
                banked = False

            if banked:
                closed_game = self.apply_bank(player, turn_score)

            self.log_row(
                TurnLogEntry(
                    move=self.move_number,
                    step=roll_index,
                    player=player.name,
                    roll=cube_set,
                    cube_count=cube_set_count,
                    hold=hold.held_counts,
                    hold_score=hold.score,
                    turn_score=turn_score,
                    total_score=player.total_score,
                    check_strike=strike,
                    check_foul=foul,
                    banked=banked,
                )
            )

            if banked:
                return closed_game

        if player.barrel_score is None:
            closed_game = self.apply_bank(player, turn_score)

        self.log_row(
            TurnLogEntry(
                move=self.move_number,
                step="end",
                player=player.name,
                roll=[],
                cube_count={},
                hold={},
                hold_score=0,
                turn_score=turn_score,
                total_score=player.total_score,
                check_strike=False,
                check_foul=False,
                banked=player.barrel_score is None,
            )
        )

        return closed_game

    def log_row(self, row: TurnLogEntry) -> None:
        if self.collect_history:
            self.history.append(row.to_dict())

    def start(self) -> str | None:
        while self.record < WIN:
            for player in self.player_set:
                if self.play_turn(player):
                    self.max_score()
                    return self.winner

            self.max_score()

        return self.winner

    def report(self) -> None:
        for row in self.history:
            print(row)
