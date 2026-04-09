from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class HoldOption:
    held_counts: dict[int, int]
    score: int
    used_dice: int


@dataclass(frozen=True)
class TurnState:
    total_score: int
    turn_score: int
    remaining_cubes: int
    rolls_left: int
    barrel_active: bool
    frozen_score: int


class Player:
    def __init__(
        self,
        name,
        strategy=None,
        threshold=5,
    ):
        """Конструктор игрока."""

        self.name = name
        self.total_score = 0
        self.barrel_score = None

        if isinstance(strategy, Strategy):
            self.strategy = strategy
            return

        strategy_name = strategy or "GreedyStrategy"

        if strategy_name == "GreedyStrategy":
            self.strategy = GreedyStrategy(threshold=threshold)
        elif strategy_name == "CautiousStrategy":
            self.strategy = CautiousStrategy(threshold=threshold)
        elif strategy_name == "HopnessStrategy":
            self.strategy = HopnessStrategy(threshold=threshold)
        elif strategy_name == "AdaptiveStrategy":
            self.strategy = AdaptiveStrategy(threshold=threshold)
        elif strategy_name == "BarrelAwareStrategy":
            self.strategy = BarrelAwareStrategy(threshold=threshold)
        else:
            self.strategy = GreedyStrategy(threshold=threshold)

    @property
    def strategy_name(self):
        return self.strategy.__class__.__name__


class Strategy(ABC):
    """Интерфейс стратегии."""

    FOUL_RISK_BY_CUBES = {
        1: 0.67,
        2: 0.47,
        3: 0.34,
        4: 0.24,
        5: 0.18,
    }

    def __init__(self, threshold=5):
        self.threshold = threshold

    @abstractmethod
    def choose_hold(self, turn_state, roll_counts, hold_options):
        """Возвращает выбранный набор кубов для откладывания."""

    @abstractmethod
    def should_bank(self, turn_state):
        """Определяет, завершать ли ход записью очков."""

    def foul_risk(self, remaining_cubes):
        return self.FOUL_RISK_BY_CUBES.get(remaining_cubes, 0.18)

    def target_score(self, turn_state):
        if turn_state.barrel_active:
            return max(0, 1000 - turn_state.frozen_score)

        return self.threshold

    def hold_value(self, option, turn_state):
        cubes_left = max(1, turn_state.remaining_cubes - option.used_dice)
        continue_safety = (1 - self.foul_risk(cubes_left)) * 25
        return option.score + continue_safety

    def pick_high_score_hold(self, turn_state, hold_options):
        return max(
            hold_options,
            key=lambda option: (option.score, option.used_dice),
        )


class GreedyStrategy(Strategy):
    """Берёт максимум из текущего броска и сразу записывает очки."""

    def choose_hold(self, turn_state, roll_counts, hold_options):
        return self.pick_high_score_hold(turn_state, hold_options)

    def should_bank(self, turn_state):
        return turn_state.turn_score > 0


class CautiousStrategy(Strategy):
    """Копит очки до заданного порога, но учитывает остаток бросков и риск булки."""

    def choose_hold(self, turn_state, roll_counts, hold_options):
        return max(
            hold_options,
            key=lambda option: (
                self.hold_value(option, turn_state),
                option.used_dice,
            ),
        )

    def should_bank(self, turn_state):
        if turn_state.barrel_active:
            return turn_state.frozen_score + turn_state.turn_score >= 1000

        if turn_state.turn_score >= self.threshold:
            return True

        if turn_state.rolls_left <= 1:
            return turn_state.turn_score > 0

        return self.foul_risk(turn_state.remaining_cubes) >= 0.45 and turn_state.turn_score >= max(
            10,
            self.threshold * 0.5,
        )


class HopnessStrategy(Strategy):
    """Ставит на небитку: стремится оставить как можно меньше кубов на столе."""

    def choose_hold(self, turn_state, roll_counts, hold_options):
        return max(
            hold_options,
            key=lambda option: (
                option.used_dice,
                option.score,
                self.hold_value(option, turn_state),
            ),
        )

    def should_bank(self, turn_state):
        if turn_state.barrel_active:
            return turn_state.frozen_score + turn_state.turn_score >= 1000

        if turn_state.turn_score >= self.threshold * 1.4:
            return True

        if turn_state.rolls_left <= 1:
            return turn_state.turn_score >= self.threshold

        return False


class AdaptiveStrategy(Strategy):
    """Балансирует доходность хода и риск булки."""

    def choose_hold(self, turn_state, roll_counts, hold_options):
        return max(
            hold_options,
            key=lambda option: (
                self.hold_value(option, turn_state),
                -option.used_dice,
                option.score,
            ),
        )

    def should_bank(self, turn_state):
        if turn_state.barrel_active:
            return turn_state.frozen_score + turn_state.turn_score >= 1000

        danger = self.foul_risk(turn_state.remaining_cubes)
        dynamic_target = self.threshold

        if danger >= 0.45:
            dynamic_target *= 0.55
        elif danger <= 0.24 and turn_state.rolls_left > 1:
            dynamic_target *= 1.25

        if turn_state.rolls_left <= 1:
            dynamic_target *= 0.7

        return turn_state.turn_score >= max(10, dynamic_target)


class BarrelAwareStrategy(Strategy):
    """Аккуратно ведёт игру до бочки и агрессивно закрывается после неё."""

    def choose_hold(self, turn_state, roll_counts, hold_options):
        if turn_state.barrel_active:
            need = max(0, 1000 - turn_state.frozen_score)
            closers = [option for option in hold_options if option.score + turn_state.turn_score >= need]
            if closers:
                return min(
                    closers,
                    key=lambda option: (
                        option.score + turn_state.turn_score - need,
                        -option.score,
                    ),
                )

            return max(
                hold_options,
                key=lambda option: (
                    option.score,
                    -self.foul_risk(max(1, turn_state.remaining_cubes - option.used_dice)),
                    option.used_dice,
                ),
            )

        return max(
            hold_options,
            key=lambda option: (
                self.hold_value(option, turn_state),
                option.score,
            ),
        )

    def should_bank(self, turn_state):
        if turn_state.barrel_active:
            return turn_state.frozen_score + turn_state.turn_score >= 1000

        near_barrel = turn_state.total_score >= 850
        danger = self.foul_risk(turn_state.remaining_cubes)

        if near_barrel and turn_state.total_score + turn_state.turn_score >= 900:
            return True

        if turn_state.turn_score >= self.threshold:
            return True

        return danger >= 0.47 and turn_state.turn_score >= max(10, self.threshold * 0.55)
