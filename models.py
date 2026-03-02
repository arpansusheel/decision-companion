"""
models.py — Data models for the Decision Companion System.

Defines the core data structures:
  - Criteria: A single decision criterion with a name, weight, and direction.
  - Laptop: A laptop option with all raw specification values.
  - ScoredLaptop: A laptop after normalization and weighted scoring.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Criteria:
    """
    Represents a single decision criterion.

    Attributes:
        name:       Human-readable name (e.g. "Price").
        key:        Snake_case key matching Laptop attribute (e.g. "price_usd").
        weight:     Importance weight as a decimal (must sum to 1.0 across all criteria).
        direction:  "lower_is_better" for cost/weight, "higher_is_better" for perf/battery.
        unit:       Display unit for the raw value (e.g. "USD", "hours").
    """

    name: str
    key: str
    weight: float
    direction: Literal["lower_is_better", "higher_is_better"]
    unit: str = ""

    def __post_init__(self) -> None:
        if not (0 < self.weight <= 1):
            raise ValueError(
                f"Criteria '{self.name}': weight must be between 0 and 1, got {self.weight}"
            )
        if self.direction not in ("lower_is_better", "higher_is_better"):
            raise ValueError(
                f"Criteria '{self.name}': direction must be 'lower_is_better' or "
                f"'higher_is_better', got '{self.direction}'"
            )


@dataclass
class Laptop:
    """
    Represents a single laptop option with raw specification values.

    Attributes:
        name:           Display name (e.g. "Apple MacBook Air M2").
        brand:          Manufacturer name.
        price_usd:      Retail price in USD. Lower is better.
        performance:    Benchmark score (Cinebench R23 multi-core). Higher is better.
        battery_hours:  Rated battery life in hours. Higher is better.
        weight_kg:      Physical weight in kilograms. Lower is better.
    """

    name: str
    brand: str
    price_usd: float
    performance: float
    battery_hours: float
    weight_kg: float

    def __post_init__(self) -> None:
        if self.price_usd <= 0:
            raise ValueError(f"'{self.name}': price_usd must be positive.")
        if self.performance <= 0:
            raise ValueError(f"'{self.name}': performance score must be positive.")
        if self.battery_hours <= 0:
            raise ValueError(f"'{self.name}': battery_hours must be positive.")
        if self.weight_kg <= 0:
            raise ValueError(f"'{self.name}': weight_kg must be positive.")

    def get_raw_value(self, key: str) -> float:
        """Return the raw value for a given criteria key."""
        if not hasattr(self, key):
            raise AttributeError(
                f"Laptop has no attribute '{key}'. "
                f"Valid keys: price_usd, performance, battery_hours, weight_kg."
            )
        return float(getattr(self, key))

    def to_dict(self) -> dict:
        """Return laptop specs as a plain dictionary."""
        return {
            "name": self.name,
            "brand": self.brand,
            "price_usd": self.price_usd,
            "performance": self.performance,
            "battery_hours": self.battery_hours,
            "weight_kg": self.weight_kg,
        }


@dataclass
class ScoredLaptop:
    """
    A Laptop after normalization and weighted scoring.

    Attributes:
        laptop:             The original Laptop object.
        normalized_scores:  Dict mapping criteria key → normalized score (0–10).
        weighted_scores:    Dict mapping criteria key → (normalized_score × weight).
        total_score:        Sum of all weighted_scores — the final ranking score.
        rank:               Rank position (1 = best). Set after sorting.
    """

    laptop: Laptop
    normalized_scores: dict = field(default_factory=dict)
    weighted_scores: dict = field(default_factory=dict)
    total_score: float = 0.0
    rank: int = 0

    @property
    def name(self) -> str:
        return self.laptop.name

    def compute_total(self) -> None:
        """Recalculate total_score from current weighted_scores."""
        self.total_score = sum(self.weighted_scores.values())
