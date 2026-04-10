from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import HoldOption, Player, PlayerSpec, TurnState


class Strategy(ABC):
    """Base interface for player strategies."""

    FOUL_RISK_BY_CUBES = {
        1: 0.67,
        2: 0.47,
        3: 0.34,
        4: 0.24,
        5: 0.18,
    }

    def __init__(self, threshold: int = 5):
        self.threshold = threshold

    @abstractmethod
    def choose_hold(
        self,
        turn_state: TurnState,
        roll_counts: dict[int, int],
        hold_options: list[HoldOption],
    ) -> HoldOption:
        """Return the selected scoring dice set."""

    @abstractmethod
    def should_bank(self, turn_state: TurnState) -> bool:
        """Return whether the player should bank now."""

    def foul_risk(self, remaining_cubes: int) -> float:
        return self.FOUL_RISK_BY_CUBES.get(remaining_cubes, 0.18)

    def hold_value(self, option: HoldOption, turn_state: TurnState) -> float:
        cubes_left = max(1, turn_state.remaining_cubes - option.used_dice)
        continue_safety = (1 - self.foul_risk(cubes_left)) * 25
        return option.score + continue_safety

    def pick_high_score_hold(self, hold_options: list[HoldOption]) -> HoldOption:
        return max(
            hold_options,
            key=lambda option: (option.score, option.used_dice),
        )


class GreedyStrategy(Strategy):
    def choose_hold(self, turn_state, roll_counts, hold_options):
        return self.pick_high_score_hold(hold_options)

    def should_bank(self, turn_state):
        return turn_state.turn_score > 0


class CautiousStrategy(Strategy):
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
    def choose_hold(self, turn_state, roll_counts, hold_options):
        if turn_state.barrel_active:
            need = max(0, 1000 - turn_state.frozen_score)
            closers = [
                option
                for option in hold_options
                if option.score + turn_state.turn_score >= need
            ]
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


@dataclass(frozen=True)
class StrategyDefinition:
    key: str
    aliases: tuple[str, ...]
    display_name: str
    strategy_cls: type[Strategy]
    default_threshold: int


STRATEGY_REGISTRY = {
    "GreedyStrategy": StrategyDefinition(
        key="GreedyStrategy",
        aliases=("greedy", "greedystrategy", "жадный"),
        display_name="Жадный",
        strategy_cls=GreedyStrategy,
        default_threshold=1,
    ),
    "CautiousStrategy": StrategyDefinition(
        key="CautiousStrategy",
        aliases=("cautious", "cautiousstrategy", "прозорливый"),
        display_name="Прозорливый",
        strategy_cls=CautiousStrategy,
        default_threshold=50,
    ),
    "HopnessStrategy": StrategyDefinition(
        key="HopnessStrategy",
        aliases=("hopness", "hopnessstrategy", "hope", "надеющийся"),
        display_name="Надеющийся",
        strategy_cls=HopnessStrategy,
        default_threshold=70,
    ),
    "AdaptiveStrategy": StrategyDefinition(
        key="AdaptiveStrategy",
        aliases=("adaptive", "adaptivestrategy", "адаптивный"),
        display_name="Адаптивный",
        strategy_cls=AdaptiveStrategy,
        default_threshold=60,
    ),
    "BarrelAwareStrategy": StrategyDefinition(
        key="BarrelAwareStrategy",
        aliases=("barrel", "barrelaware", "barrelawarestrategy", "бочкарь"),
        display_name="Бочкарь",
        strategy_cls=BarrelAwareStrategy,
        default_threshold=55,
    ),
}

STRATEGY_ALIAS_MAP = {
    alias: definition.key
    for definition in STRATEGY_REGISTRY.values()
    for alias in definition.aliases
}
STRATEGY_ALIAS_MAP.update(
    {definition.key.lower(): definition.key for definition in STRATEGY_REGISTRY.values()}
)


def resolve_strategy_name(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in STRATEGY_ALIAS_MAP:
        raise ValueError(f"Unknown strategy '{value}'")
    return STRATEGY_ALIAS_MAP[normalized]


def strategy_definition(value: str) -> StrategyDefinition:
    return STRATEGY_REGISTRY[resolve_strategy_name(value)]


def create_strategy(value: str, threshold: int | None = None) -> Strategy:
    definition = strategy_definition(value)
    actual_threshold = definition.default_threshold if threshold is None else threshold
    return definition.strategy_cls(threshold=actual_threshold)


def create_player(
    name: str,
    strategy: str | Strategy | None = None,
    threshold: int | None = None,
) -> Player:
    if isinstance(strategy, Strategy):
        return Player(name=name, strategy=strategy)

    strategy_name = strategy or "GreedyStrategy"
    return Player(
        name=name,
        strategy=create_strategy(strategy_name, threshold=threshold),
    )


def build_player_spec(name: str, strategy: str, threshold: int) -> PlayerSpec:
    return PlayerSpec(
        name=name,
        strategy=resolve_strategy_name(strategy),
        threshold=threshold,
    )
