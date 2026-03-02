"""
normalizer.py — Min-max normalization for the Decision Companion System.

Responsibility:
  Given a list of options (Laptop or generic Option) and a list of Criteria,
  normalize every option's raw value for each criterion to a 0–10 scale.

Algorithm (min-max normalization):
  For "higher_is_better":
      norm = (value - min) / (max - min) * 10

  For "lower_is_better"  (e.g. price, weight):
      norm = (max - value) / (max - min) * 10

  Edge case — all options have the same value for a criterion:
      norm = 10.0 for all (no differentiation possible, treat all as equal best)
"""

from models import Criteria, Laptop, ScoredLaptop, Option, ScoredOption


def normalize(laptops: list[Laptop], criteria: list[Criteria]) -> list[ScoredLaptop]:
    """
    Normalize all laptop values across all criteria and return ScoredLaptop objects.
    """
    scored = [ScoredLaptop(laptop=laptop) for laptop in laptops]

    for criterion in criteria:
        raw_values = [laptop.get_raw_value(criterion.key) for laptop in laptops]

        min_val = min(raw_values)
        max_val = max(raw_values)
        value_range = max_val - min_val

        for sl, raw in zip(scored, raw_values):
            if value_range == 0:
                norm_score = 10.0
            elif criterion.direction == "higher_is_better":
                norm_score = (raw - min_val) / value_range * 10.0
            else:
                norm_score = (max_val - raw) / value_range * 10.0

            sl.normalized_scores[criterion.key] = round(norm_score, 4)

    return scored


def normalize_options(options: list[Option], criteria: list[Criteria]) -> list[ScoredOption]:
    """
    Normalize all generic Option values across all criteria and return ScoredOption objects.

    Works for any domain — laptops, cars, phones, apartments, etc.
    """
    scored = [ScoredOption(option=opt) for opt in options]

    for criterion in criteria:
        raw_values = [opt.get_raw_value(criterion.key) for opt in options]

        min_val = min(raw_values)
        max_val = max(raw_values)
        value_range = max_val - min_val

        for so, raw in zip(scored, raw_values):
            if value_range == 0:
                norm_score = 10.0
            elif criterion.direction == "higher_is_better":
                norm_score = (raw - min_val) / value_range * 10.0
            else:
                norm_score = (max_val - raw) / value_range * 10.0

            so.normalized_scores[criterion.key] = round(norm_score, 4)

    return scored


def get_normalization_details(
    options, criteria: list[Criteria]
) -> dict[str, dict]:
    """
    Return per-criterion min/max/range metadata.
    Accepts either list[Laptop] or list[Option].
    """
    details: dict[str, dict] = {}
    for criterion in criteria:
        raw_values = [opt.get_raw_value(criterion.key) for opt in options]
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
