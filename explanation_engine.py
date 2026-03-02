"""
explanation_engine.py — Human-readable explanations for Decision Companion rankings.

Responsibility:
  Given the ranked list of ScoredLaptop objects and the criteria used,
  generate clear, factual explanations of:
    1. Why a laptop ranked where it did (strength/weakness breakdown).
    2. What separates the winner from the runner-up.
    3. A per-laptop "verdict" summarising its profile.

Design principle:
  All explanation text is generated algorithmically from scores and data —
  no LLM or AI-generated prose. This ensures reproducibility and auditability.
"""

from models import Criteria, ScoredLaptop


# Thresholds for scoring adjectives (on a 0–10 normalized scale)
def _score_label(score: float) -> str:
    """Convert a normalized score to a descriptive adjective."""
    if score >= 8.5:
        return "excellent"
    elif score >= 6.5:
        return "good"
    elif score >= 4.0:
        return "average"
    elif score >= 2.0:
        return "below average"
    else:
        return "poor"


def explain_ranking(
    ranked: list[ScoredLaptop],
    criteria: list[Criteria],
    norm_details: dict,
) -> list[dict]:
    """
    Generate a full explanation for every laptop in the ranked list.

    Args:
        ranked:       List of ScoredLaptop objects sorted best → worst.
        criteria:     The criteria used in this run.
        norm_details: Per-criterion min/max/range from the normalizer.

    Returns:
        List of dicts, one per laptop, containing:
          - "rank":        int rank position.
          - "name":        laptop name.
          - "total_score": final score (0–10).
          - "verdict":     one-line summary of the laptop's profile.
          - "strengths":   list of criterion names where it scored highly.
          - "weaknesses":  list of criterion names where it scored poorly.
          - "breakdown":   list of per-criterion explanation strings.
          - "vs_winner":   (for rank > 1) gap explanation vs. the winner.
    """
    explanations = []
    winner = ranked[0]

    for sl in ranked:
        breakdown = _build_breakdown(sl, criteria, norm_details)
        strengths, weaknesses = _find_strengths_weaknesses(sl, criteria)
        verdict = _build_verdict(sl, criteria, strengths, weaknesses)
        vs_winner = _vs_winner_text(sl, winner, criteria) if sl.rank > 1 else None

        explanations.append(
            {
                "rank": sl.rank,
                "name": sl.name,
                "total_score": round(sl.total_score, 3),
                "verdict": verdict,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "breakdown": breakdown,
                "vs_winner": vs_winner,
            }
        )

    return explanations


def _build_breakdown(
    sl: ScoredLaptop,
    criteria: list[Criteria],
    norm_details: dict,
) -> list[str]:
    """
    Build a per-criterion explanation sentence for a single laptop.

    Example:
      "Price: $1,099 — normalized 8.89/10 (excellent) → contributes 3.56 pts (weight 40%)"
    """
    lines = []
    for c in criteria:
        raw = sl.laptop.get_raw_value(c.key)
        norm = sl.normalized_scores[c.key]
        weighted = sl.weighted_scores[c.key]
        label = _score_label(norm)
        unit = norm_details[c.key]["unit"]
        direction_note = "↓ lower is better" if c.direction == "lower_is_better" else "↑ higher is better"

        # Format raw value nicely
        if c.key == "price_usd":
            raw_str = f"${raw:,.0f}"
        elif c.key == "weight_kg":
            raw_str = f"{raw:.2f} {unit}"
        elif c.key == "performance":
            raw_str = f"{raw:,.0f} {unit}"
        else:
            raw_str = f"{raw:.1f} {unit}"

        lines.append(
            f"{c.name} ({int(c.weight*100)}%): {raw_str} [{direction_note}] "
            f"→ {norm:.2f}/10 ({label}) "
            f"→ weighted {weighted:.3f} pts"
        )
    return lines


def _find_strengths_weaknesses(
    sl: ScoredLaptop,
    criteria: list[Criteria],
) -> tuple[list[str], list[str]]:
    """Identify criteria where this laptop excels (≥7) or struggles (≤3)."""
    strengths = []
    weaknesses = []
    for c in criteria:
        norm = sl.normalized_scores[c.key]
        if norm >= 7.0:
            strengths.append(c.name)
        elif norm <= 3.0:
            weaknesses.append(c.name)
    return strengths, weaknesses


def _build_verdict(
    sl: ScoredLaptop,
    criteria: list[Criteria],
    strengths: list[str],
    weaknesses: list[str],
) -> str:
    """Generate a one-line profile verdict."""
    score = sl.total_score

    if score >= 7.5:
        quality = "a top-tier all-rounder"
    elif score >= 6.0:
        quality = "a strong contender"
    elif score >= 4.5:
        quality = "a solid mid-range choice"
    else:
        quality = "a niche option"

    if strengths and weaknesses:
        verb = "excels at" if len(strengths) > 1 else "excels in"
        summary = (
            f"{sl.name} is {quality} that {verb} "
            f"{', '.join(strengths)} but struggles with "
            f"{', '.join(weaknesses)}."
        )
    elif strengths:
        summary = (
            f"{sl.name} is {quality} with strong marks across "
            f"{', '.join(strengths)}."
        )
    elif weaknesses:
        summary = (
            f"{sl.name} is {quality} held back by "
            f"weak {', '.join(weaknesses)}."
        )
    else:
        summary = f"{sl.name} is {quality} with balanced performance across all criteria."

    return summary


def _vs_winner_text(
    sl: ScoredLaptop,
    winner: ScoredLaptop,
    criteria: list[Criteria],
) -> str:
    """
    Explain what's holding this laptop back relative to the winner.
    Finds the criterion where the gap is largest (in weighted contribution).
    """
    biggest_gap_criterion = max(
        criteria,
        key=lambda c: winner.weighted_scores[c.key] - sl.weighted_scores[c.key],
    )
    gap = sl.total_score - winner.total_score  # will be negative
    c = biggest_gap_criterion
    winner_norm = winner.normalized_scores[c.key]
    sl_norm = sl.normalized_scores[c.key]

    return (
        f"Trails {winner.name} by {abs(gap):.2f} pts overall. "
        f"Biggest gap: {c.name} "
        f"({sl_norm:.1f}/10 vs winner's {winner_norm:.1f}/10, "
        f"weighted {int(c.weight*100)}%)."
    )
