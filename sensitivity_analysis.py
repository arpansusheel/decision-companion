"""
sensitivity_analysis.py — Sensitivity analysis for the Decision Companion System.

Responsibility:
  Quantify how robust the ranking is to changes in criteria weights.
  For each criterion, shift its weight up and down by a configurable delta
  (default ±10 percentage points), redistribute the remainder proportionally
  across all other criteria, re-run scoring, and record if the winner changes.

This is the "standout feature" of the system:
  It answers the question "How confident should I be in this recommendation?"
  rather than just "What is the recommendation?"

Output:
  - Per-scenario result: which criterion was shifted, new weights, new winner.
  - Stability score: % of scenarios where the winner is unchanged.
  - Rank-shift matrix: how each laptop's rank changes per scenario.
  - Tipping-point search: smallest weight change that flips the winner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from models import Criteria, Laptop, ScoredLaptop, Option, ScoredOption
from decision_engine import score_and_rank, score_and_rank_options


def _run_scoring(items, criteria):
    """Auto-detect item type and call the correct scoring function."""
    if items and isinstance(items[0], Option):
        return score_and_rank_options(items, criteria)
    return score_and_rank(items, criteria)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """One sensitivity scenario — a single weight shift and its outcome."""

    focal_criterion: str       # Name of the criterion whose weight was shifted
    direction: str             # "increased" or "decreased"
    delta: float               # Magnitude of the weight shift (e.g. 0.10)
    adjusted_weights: dict     # {criterion_name: new_weight}
    ranked: list = field(default_factory=list)  # list[ScoredLaptop] or list[ScoredOption]
    winner_changed: bool = False
    new_winner: str = ""


@dataclass
class SensitivityReport:
    """Full sensitivity analysis report."""

    base_winner: str
    base_ranking: list[str]          # Laptop names in rank order
    scenarios: list[Scenario]
    stability_score: float           # 0.0 – 1.0 (fraction where winner unchanged)
    tipping_points: dict             # {criterion_name: min delta that flips winner}
    rank_shift_matrix: dict          # {laptop_name: {scenario_label: rank}}

    @property
    def stability_label(self) -> str:
        if self.stability_score >= 0.85:
            return "highly stable"
        elif self.stability_score >= 0.55:
            return "moderately stable"
        else:
            return "highly sensitive"


# ---------------------------------------------------------------------------
# Core analysis functions
# ---------------------------------------------------------------------------

def _scale_other_weights(
    criteria: list[Criteria],
    focal_index: int,
    new_focal_weight: float,
) -> list[Criteria] | None:
    """
    Build a new criteria list with the focal criterion's weight set to
    new_focal_weight and all others scaled proportionally.

    Returns None if the adjustment would produce any non-positive weight.
    """
    remaining_budget = 1.0 - new_focal_weight
    other_total = sum(c.weight for i, c in enumerate(criteria) if i != focal_index)

    if other_total <= 0 or remaining_budget <= 0:
        return None

    adjusted: list[Criteria] = []
    for i, c in enumerate(criteria):
        if i == focal_index:
            w = round(new_focal_weight, 6)
        else:
            w = round(c.weight / other_total * remaining_budget, 6)
        if w <= 0:
            return None
        adjusted.append(Criteria(c.name, c.key, w, c.direction, c.unit))

    return adjusted


def run_sensitivity(
    items,
    criteria: list[Criteria],
    delta: float = 0.10,
) -> SensitivityReport:
    """
    Run the full sensitivity analysis.
    Accepts either list[Laptop] or list[Option].
    """
    # Baseline
    base_ranked, _ = _run_scoring(items, criteria)
    base_winner = base_ranked[0].name
    base_ranking = [sl.name for sl in base_ranked]

    scenarios: list[Scenario] = []

    for i, focal in enumerate(criteria):
        for direction, sign in [("increased", +1), ("decreased", -1)]:
            new_weight = focal.weight + sign * delta

            if new_weight <= 0 or new_weight >= 1.0:
                continue  # Out of valid range, skip

            adjusted = _scale_other_weights(criteria, i, new_weight)
            if adjusted is None:
                continue

            try:
                new_ranked, _ = _run_scoring(items, adjusted)
            except ValueError:
                continue

            new_winner = new_ranked[0].name
            scenario = Scenario(
                focal_criterion=focal.name,
                direction=direction,
                delta=delta,
                adjusted_weights={c.name: c.weight for c in adjusted},
                ranked=new_ranked,
                winner_changed=(new_winner != base_winner),
                new_winner=new_winner,
            )
            scenarios.append(scenario)

    # Stability score
    stable = sum(1 for s in scenarios if not s.winner_changed)
    stability_score = stable / len(scenarios) if scenarios else 1.0

    # Tipping-point search (binary search per criterion)
    tipping_points = _find_tipping_points(items, criteria, base_winner)

    # Rank-shift matrix
    rank_shift_matrix = _build_rank_shift_matrix(base_ranking, scenarios)

    return SensitivityReport(
        base_winner=base_winner,
        base_ranking=base_ranking,
        scenarios=scenarios,
        stability_score=stability_score,
        tipping_points=tipping_points,
        rank_shift_matrix=rank_shift_matrix,
    )


def _find_tipping_points(
    items,
    criteria: list[Criteria],
    base_winner: str,
    precision: float = 0.01,
    max_delta: float = 0.50,
) -> dict:
    """
    For each criterion, binary-search the smallest shift (in either direction)
    that causes the winner to change.

    Returns {criterion_name: minimum_delta_to_flip} or "stable" if no flip found.
    """
    tipping: dict = {}

    for i, focal in enumerate(criteria):
        found = {}
        for sign, label in [(+1, "increase"), (-1, "decrease")]:
            lo, hi = 0.0, min(max_delta, (1.0 - focal.weight) if sign == 1 else focal.weight)
            flip_at = None

            # Coarse scan first (every 1%)
            for step in range(1, int(hi / precision) + 1):
                d = step * precision
                new_weight = focal.weight + sign * d
                if new_weight <= 0 or new_weight >= 1.0:
                    break
                adj = _scale_other_weights(criteria, i, new_weight)
                if adj is None:
                    break
                try:
                    new_ranked, _ = _run_scoring(items, adj)
                    if new_ranked[0].name != base_winner:
                        flip_at = d
                        break
                except ValueError:
                    break

            if flip_at is not None:
                found[label] = round(flip_at, 2)

        if found:
            tipping[focal.name] = found
        else:
            tipping[focal.name] = {"status": f"stable within ±{int(max_delta*100)}%"}

    return tipping


def _build_rank_shift_matrix(
    base_ranking: list[str],
    scenarios: list[Scenario],
) -> dict:
    """
    Build a matrix showing how each laptop's rank changes per scenario.

    Returns:
        {laptop_name: {"base": int, scenario_label: int, ...}}
    """
    matrix: dict = {name: {"base": i + 1} for i, name in enumerate(base_ranking)}

    for s in scenarios:
        label = f"{s.focal_criterion} {s.direction[:3]}."
        rank_map = {sl.name: sl.rank for sl in s.ranked}
        for name in base_ranking:
            matrix[name][label] = rank_map.get(name, "?")

    return matrix


# ---------------------------------------------------------------------------
# Formatting helpers (used by main.py CLI display)
# ---------------------------------------------------------------------------

def format_report(report: SensitivityReport, criteria: list[Criteria]) -> str:
    """
    Render the full sensitivity report as a formatted string for CLI display.
    """
    lines: list[str] = []
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    lines.append(f"\n{CYAN}{BOLD}{'─' * 70}{RESET}")
    lines.append(f"{CYAN}{BOLD}  SENSITIVITY ANALYSIS{RESET}")
    lines.append(f"{CYAN}{BOLD}{'─' * 70}{RESET}\n")

    lines.append(
        f"  {DIM}Base winner: {BOLD}{report.base_winner}{RESET}  "
        f"|  Stability: {BOLD}{report.stability_label} "
        f"({report.stability_score:.0%}){RESET}\n"
    )

    # ── Scenario table ─────────────────────────────────────────────────────
    lines.append(f"  {BOLD}{'Criterion':<20} {'Change':<12} {'New Wt':>8}  {'Winner':<34} {'Stable?'}{RESET}")
    lines.append(f"  {'─' * 84}")

    for s in report.scenarios:
        new_wt = s.adjusted_weights[s.focal_criterion]
        stability = f"{GREEN}✓ YES{RESET}" if not s.winner_changed else f"{RED}✗ NO{RESET}"
        winner_str = s.new_winner if not s.winner_changed else f"{RED}{s.new_winner}{RESET}"
        lines.append(
            f"  {s.focal_criterion:<20} {s.direction:<12} {new_wt:>7.0%}  "
            f"{winner_str:<34} {stability}"
        )

    # ── Tipping points ─────────────────────────────────────────────────────
    lines.append(f"\n  {BOLD}Tipping Points{RESET} (smallest weight shift to flip the winner):\n")
    for crit_name, details in report.tipping_points.items():
        if "status" in details:
            lines.append(f"    {crit_name:<20} {GREEN}{details['status']}{RESET}")
        else:
            parts = [f"{dir_}: +{val*100:.0f}%" for dir_, val in details.items()]
            color = YELLOW if any(v <= 0.15 for v in details.values()) else GREEN
            lines.append(f"    {crit_name:<20} {color}{' | '.join(parts)}{RESET}")

    # ── Rank-shift matrix ──────────────────────────────────────────────────
    lines.append(f"\n  {BOLD}Rank-Shift Matrix{RESET} (how ranks change per scenario):\n")
    # Header row
    scenario_labels = [f"{s.focal_criterion[:6]}.{s.direction[:3]}." for s in report.scenarios]
    header = f"  {'Laptop':<34} {'Base':>5}"
    for lbl in scenario_labels:
        header += f" {lbl[:10]:>10}"
    lines.append(f"  {BOLD}{header.strip()}{RESET}")
    lines.append(f"  {'─' * (34 + 6 + 11 * len(scenario_labels))}")

    for laptop_name, ranks in report.rank_shift_matrix.items():
        base_rank = ranks["base"]
        row = f"  {laptop_name:<34} {base_rank:>5}"
        for s in report.scenarios:
            lbl = f"{s.focal_criterion} {s.direction[:3]}."
            r = ranks.get(lbl, "?")
            shift = (r - base_rank) if isinstance(r, int) else 0
            if shift < 0:
                cell = f"{GREEN}{r:>2}(↑{abs(shift)}){RESET}"
            elif shift > 0:
                cell = f"{RED}{r:>2}(↓{shift}){RESET}"
            else:
                cell = f"{r:>2}(  )"
            row += f" {cell:>10}"
        lines.append(row)

    # ── Stability summary ──────────────────────────────────────────────────
    lines.append(f"\n  {BOLD}Stability Summary:{RESET}")
    stable_count = sum(1 for s in report.scenarios if not s.winner_changed)
    total = len(report.scenarios)
    color = GREEN if report.stability_score >= 0.85 else (YELLOW if report.stability_score >= 0.55 else RED)
    lines.append(
        f"  {color}Winner unchanged in {stable_count}/{total} scenarios "
        f"({report.stability_score:.0%}) — {report.stability_label}.{RESET}"
    )

    return "\n".join(lines)
