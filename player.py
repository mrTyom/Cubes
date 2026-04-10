from cubes.models import HoldOption, Player as BasePlayer, PlayerSpec, TurnLogEntry, TurnState
from cubes.strategies import (
    AdaptiveStrategy,
    BarrelAwareStrategy,
    CautiousStrategy,
    GreedyStrategy,
    HopnessStrategy,
    STRATEGY_REGISTRY,
    Strategy,
    StrategyDefinition,
    create_player,
    create_strategy,
    resolve_strategy_name,
)


class Player(BasePlayer):
    def __init__(self, name, strategy=None, threshold=5):
        if isinstance(strategy, Strategy):
            super().__init__(name=name, strategy=strategy)
            return

        strategy_name = strategy or "GreedyStrategy"
        super().__init__(
            name=name,
            strategy=create_strategy(strategy_name, threshold=threshold),
        )


__all__ = [
    "AdaptiveStrategy",
    "BarrelAwareStrategy",
    "CautiousStrategy",
    "GreedyStrategy",
    "HoldOption",
    "HopnessStrategy",
    "Player",
    "PlayerSpec",
    "STRATEGY_REGISTRY",
    "Strategy",
    "StrategyDefinition",
    "TurnLogEntry",
    "TurnState",
    "create_player",
    "create_strategy",
    "resolve_strategy_name",
]
