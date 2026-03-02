"""
decision_engine.py — Weighted scoring and ranking for the Decision Companion System.

Responsibility:
  1. Define the default criteria (Price 40%, Performance 30%, Battery 20%, Weight 10%).
  2. Load laptop data from laptops.json.
  3. Orchestrate normalization → weighted scoring → ranking.

Algorithm:
  Score(laptop) = Σ (normalized_score[criterion] × criterion.weight)
  normalized_score is on a 0–10 scale (from normalizer.py).
  Final score is therefore also on a 0–10 scale.
"""

import json
from pathlib import Path

from models import Criteria, Laptop, ScoredLaptop
from normalizer import normalize, get_normalization_details


# ---------------------------------------------------------------------------
# Default criteria — weights must sum to 1.0
# ---------------------------------------------------------------------------
DEFAULT_CRITERIA: list[Criteria] = [
    Criteria(
        name="Price",
        key="price_usd",
        weight=0.40,
        direction="lower_is_better",
        unit="USD",
    ),
    Criteria(
        name="Performance",
        key="performance",
        weight=0.30,
        direction="higher_is_better",
        unit="pts",
    ),
    Criteria(
        name="Battery Life",
        key="battery_hours",
        weight=0.20,
        direction="higher_is_better",
        unit="hrs",
    ),
    Criteria(
        name="Weight",
        key="weight_kg",
        weight=0.10,
        direction="lower_is_better",
        unit="kg",
    ),
]

# Path to the laptop dataset (relative to this file)
DATA_PATH = Path(__file__).parent / "data" / "laptops.json"


def load_laptops(path: Path = DATA_PATH) -> list[Laptop]:
    """
    Load and validate laptop data from a JSON file.

    Args:
        path: Path to the JSON file containing a "laptops" array.

    Returns:
        List of validated Laptop objects.

    Raises:
        FileNotFoundError: If the data file does not exist.
        KeyError: If the JSON is missing required fields.
    """
    if not path.exists():
        raise FileNotFoundError(f"Laptop data not found at: {path}")

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    laptops: list[Laptop] = []
    for entry in raw["laptops"]:
        laptops.append(
            Laptop(
                name=entry["name"],
                brand=entry["brand"],
                price_usd=float(entry["price_usd"]),
                performance=float(entry["performance"]),
                battery_hours=float(entry["battery_hours"]),
                weight_kg=float(entry["weight_kg"]),
            )
        )
    return laptops


def score_and_rank(
    laptops: list[Laptop],
    criteria: list[Criteria] | None = None,
) -> tuple[list[ScoredLaptop], dict]:
    """
    Run the full decision pipeline: normalize → weight → rank.

    Args:
        laptops:  List of Laptop objects to evaluate.
        criteria: Criteria to use. Defaults to DEFAULT_CRITERIA.

    Returns:
        A tuple of:
          - ranked: List of ScoredLaptop, sorted best → worst (rank 1 = best).
          - norm_details: Per-criterion normalization metadata (for explanation engine).
    """
    if criteria is None:
        criteria = DEFAULT_CRITERIA

    _validate_weights(criteria)

    # Step 1 — Normalize raw values to 0–10 scale
    scored = normalize(laptops, criteria)

    # Step 2 — Compute weighted scores for each laptop
    for sl in scored:
        for criterion in criteria:
            norm = sl.normalized_scores[criterion.key]
            sl.weighted_scores[criterion.key] = round(norm * criterion.weight, 4)
        sl.compute_total()

    # Step 3 — Sort descending by total score, assign ranks
    scored.sort(key=lambda sl: sl.total_score, reverse=True)
    for rank, sl in enumerate(scored, start=1):
        sl.rank = rank

    # Normalization metadata used by the explanation engine
    norm_details = get_normalization_details(laptops, criteria)

    return scored, norm_details


def _validate_weights(criteria: list[Criteria]) -> None:
    """Raise ValueError if weights do not sum to 1.0 (within floating-point tolerance)."""
    total = sum(c.weight for c in criteria)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Criteria weights must sum to 1.0, but got {total:.4f}. "
            "Please adjust your weights."
        )
