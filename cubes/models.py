from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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


@dataclass(frozen=True)
class PlayerSpec:
    name: str
    strategy: str
    threshold: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TurnLogEntry:
    move: int
    step: int | str
    player: str
    roll: list[int]
    cube_count: dict[int, int]
    hold: dict[int, int]
    hold_score: int
    turn_score: int
    total_score: int
    check_strike: bool
    check_foul: bool
    banked: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Player:
    name: str
    strategy: Any
    total_score: int = 0
    barrel_score: int | None = None

    @property
    def strategy_name(self) -> str:
        return self.strategy.__class__.__name__
