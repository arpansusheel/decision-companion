"""
normalizer.py — Min-max normalization for the Decision Companion System.

Responsibility:
  Given a list of Laptop objects and a list of Criteria, normalize every
  laptop's raw value for each criterion to a 0–10 scale.

Algorithm (min-max normalization):
  For "higher_is_better":
      norm = (value - min) / (max - min) * 10

  For "lower_is_better"  (e.g. price, weight):
      norm = (max - value) / (max - min) * 10

  Edge case — all laptops have the same value for a criterion:
      norm = 10.0 for all (no differentiation possible, treat all as equal best)
"""

from models import Criteria, Laptop, ScoredLaptop


def normalize(laptops: list[Laptop], criteria: list[Criteria]) -> list[ScoredLaptop]:
    """
    Normalize all laptop values across all criteria and return ScoredLaptop objects.

    Args:
        laptops:  List of raw Laptop objects loaded from data.
        criteria: List of Criteria defining weights and directions.

    Returns:
        List of ScoredLaptop objects with normalized_scores populated.
        weighted_scores and total_score are NOT computed here (that is
        the responsibility of the decision_engine).
    """
    # Build ScoredLaptop wrappers — one per laptop
    scored = [ScoredLaptop(laptop=laptop) for laptop in laptops]

    for criterion in criteria:
        # Collect raw values for this criterion across all laptops
        raw_values = [laptop.get_raw_value(criterion.key) for laptop in laptops]

        min_val = min(raw_values)
        max_val = max(raw_values)
        value_range = max_val - min_val

        for sl, raw in zip(scored, raw_values):
            if value_range == 0:
                # All options are identical for this criterion — assign full score
                norm_score = 10.0
            elif criterion.direction == "higher_is_better":
                norm_score = (raw - min_val) / value_range * 10.0
            else:  # lower_is_better
                norm_score = (max_val - raw) / value_range * 10.0

            sl.normalized_scores[criterion.key] = round(norm_score, 4)

    return scored


def get_normalization_details(
    laptops: list[Laptop], criteria: list[Criteria]
) -> dict[str, dict]:
    """
    Return per-criterion min/max/range metadata — useful for explainability
    and sensitivity analysis.

    Returns:
        {
          "price_usd": {"min": 699, "max": 1599, "range": 900, "direction": "lower_is_better"},
          ...
        }
    """
    details: dict[str, dict] = {}
    for criterion in criteria:
        raw_values = [laptop.get_raw_value(criterion.key) for laptop in laptops]
        min_val = min(raw_values)
        max_val = max(raw_values)
        details[criterion.key] = {
            "min": min_val,
            "max": max_val,
            "range": max_val - min_val,
            "direction": criterion.direction,
            "unit": criterion.unit,
        }
    return details
