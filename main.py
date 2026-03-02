"""
main.py — CLI entry point for the Decision Companion System.

Usage:
    python main.py                              # Default laptop comparison
    python main.py --sensitivity                # Include sensitivity analysis
    python main.py --weights 0.5 0.3 0.1 0.1   # Custom weights for laptops
    python main.py --interactive                # Interactive mode — ANY options
    python main.py --interactive --sensitivity  # Interactive + sensitivity
    python main.py --help                       # Show help
"""

import argparse
import sys

from decision_engine import (
    DEFAULT_CRITERIA,
    load_laptops,
    score_and_rank,
    score_and_rank_options,
)
from explanation_engine import explain_ranking
from models import Criteria, Option
from sensitivity_analysis import run_sensitivity, format_report


# ---------------------------------------------------------------------------
# ANSI color codes (no external dependencies)
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _header(text: str) -> None:
    width = 70
    print(f"\n{CYAN}{BOLD}{'─' * width}{RESET}")
    print(f"{CYAN}{BOLD}  {text}{RESET}")
    print(f"{CYAN}{BOLD}{'─' * width}{RESET}")


def _score_bar(score: float, max_score: float = 10.0, width: int = 20) -> str:
    filled = int((score / max_score) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:.3f}/10"


def print_ranked_table(ranked, criteria) -> None:
    _header("RANKED RESULTS")

    # Build dynamic header
    headers = ["Rank", "Option"]
    for c in criteria:
        headers.append(f"{c.name}({int(c.weight*100)}%)")
    headers.append("TOTAL")

    # Print header
    row_parts = [f"{'Rank':<4}", f"{'Option':<32}"]
    for c in criteria:
        label = f"{c.name[:8]}({int(c.weight*100)}%)"
        row_parts.append(f"{label:>12}")
    row_parts.append(f"{'TOTAL':>10}")
    print(f"\n  {BOLD}" + " ".join(row_parts) + RESET)
    total_width = 4 + 32 + 12 * len(criteria) + 10 + len(criteria) + 2
    print(f"  {'─' * total_width}")

    crit_keys = [c.key for c in criteria]
    for sl in ranked:
        medal = MEDAL.get(sl.rank, "  ")
        color = GREEN if sl.rank == 1 else (YELLOW if sl.rank == 2 else RESET)

        row = f"  {color}{medal} {sl.rank:<2} {sl.name:<32}"
        for k in crit_keys:
            row += f" {sl.normalized_scores[k]:>10.2f}"
        row += f" {sl.total_score:>10.3f}{RESET}"
        print(row)

    print(f"\n  {DIM}(Values shown are normalized 0–10 scores, not raw values){RESET}\n")


def print_explanations(explanations: list[dict]) -> None:
    _header("DETAILED EXPLANATIONS")
    for exp in explanations:
        medal = MEDAL.get(exp["rank"], f"#{exp['rank']}")
        print(f"\n  {BOLD}{medal} Rank {exp['rank']}: {exp['name']}{RESET}")
        print(f"  {DIM}Score: {_score_bar(exp['total_score'])}{RESET}")
        print(f"\n  {BOLD}Verdict:{RESET}")
        print(f"    {exp['verdict']}")

        if exp["strengths"]:
            print(f"\n  {GREEN}{BOLD}Strengths:{RESET} {', '.join(exp['strengths'])}")
        if exp["weaknesses"]:
            print(f"  {RED}{BOLD}Weaknesses:{RESET} {', '.join(exp['weaknesses'])}")

        print(f"\n  {BOLD}Score Breakdown:{RESET}")
        for line in exp["breakdown"]:
            print(f"    • {line}")

        if exp["vs_winner"]:
            print(f"\n  {YELLOW}vs. Winner:{RESET} {exp['vs_winner']}")

        print(f"\n  {'·' * 68}")


def print_sensitivity_analysis(options_or_laptops, criteria) -> None:
    """Run sensitivity analysis via the dedicated module and print the report."""
    report = run_sensitivity(options_or_laptops, criteria)
    print(format_report(report, criteria))


# ---------------------------------------------------------------------------
# Interactive mode — user defines their own options and criteria
# ---------------------------------------------------------------------------

def _input_colored(prompt: str) -> str:
    """Print a colored prompt and read input."""
    return input(f"  {CYAN}{prompt}{RESET} ")


def _input_float(prompt: str) -> float:
    """Read a float from the user with validation."""
    while True:
        raw = _input_colored(prompt)
        try:
            return float(raw)
        except ValueError:
            print(f"  {RED}Please enter a valid number.{RESET}")


def _input_int(prompt: str, min_val: int = 1) -> int:
    """Read an integer from the user with validation."""
    while True:
        raw = _input_colored(prompt)
        try:
            val = int(raw)
            if val < min_val:
                print(f"  {RED}Must be at least {min_val}.{RESET}")
                continue
            return val
        except ValueError:
            print(f"  {RED}Please enter a valid whole number.{RESET}")


def run_interactive(run_sensitivity_flag: bool) -> None:
    """
    Fully interactive mode: user defines the category, criteria, and options.
    Works for any domain — laptops, cars, phones, apartments, etc.
    """
    _header("DECISION COMPANION — INTERACTIVE MODE")
    print(f"\n  {DIM}You can compare anything: laptops, cars, phones, apartments...{RESET}")
    print(f"  {DIM}Just define your criteria and enter your options.{RESET}\n")

    # ── Step 1: Category ───────────────────────────────────────────────
    category = _input_colored("What are you comparing? (e.g. laptops, cars, phones):").strip()
    if not category:
        category = "options"
    print(f"\n  {GREEN}✓ Comparing: {BOLD}{category}{RESET}\n")

    # ── Step 2: Criteria ───────────────────────────────────────────────
    print(f"  {BOLD}Define your decision criteria.{RESET}")
    print(f"  {DIM}Each criterion has a name, direction, and importance weight.{RESET}\n")

    num_criteria = _input_int("How many criteria? (e.g. 3, 4, 5):")
    criteria: list[Criteria] = []

    remaining_weight = 1.0
    for i in range(num_criteria):
        print(f"\n  {BOLD}─── Criterion {i + 1}/{num_criteria} ───{RESET}")

        name = _input_colored(f"  Name (e.g. Price, Speed, Battery):").strip()
        key = name.lower().replace(" ", "_")

        # Direction
        while True:
            direction_input = _input_colored(
                f"  Is higher better or lower better? (h/l):"
            ).strip().lower()
            if direction_input in ("h", "higher", "higher_is_better"):
                direction = "higher_is_better"
                break
            elif direction_input in ("l", "lower", "lower_is_better"):
                direction = "lower_is_better"
                break
            else:
                print(f"  {RED}Enter 'h' for higher is better, or 'l' for lower is better.{RESET}")

        # Unit (optional)
        unit = _input_colored(f"  Unit (e.g. USD, kg, hours — or press Enter to skip):").strip()

        # Weight
        if i < num_criteria - 1:
            while True:
                weight = _input_float(
                    f"  Weight (0-1, remaining: {remaining_weight:.2f}):"
                )
                if 0 < weight <= remaining_weight:
                    break
                print(f"  {RED}Weight must be between 0 and {remaining_weight:.2f}.{RESET}")
            remaining_weight -= weight
        else:
            # Last criterion gets whatever weight remains
            weight = round(remaining_weight, 4)
            print(f"  {DIM}  Weight auto-assigned: {weight:.2f} (remaining){RESET}")

        criteria.append(Criteria(
            name=name, key=key, weight=round(weight, 4),
            direction=direction, unit=unit,
        ))

        dir_arrow = "↑ higher is better" if direction == "higher_is_better" else "↓ lower is better"
        print(f"  {GREEN}✓ {name}: weight {weight:.0%}, {dir_arrow}{RESET}")

    # Show criteria summary
    print(f"\n  {BOLD}Your criteria:{RESET}")
    for c in criteria:
        dir_arrow = "↑" if c.direction == "higher_is_better" else "↓"
        print(f"    {c.name:<20} weight: {c.weight:.0%}   {dir_arrow} {c.direction.replace('_', ' ')}")

    # ── Step 3: Options ────────────────────────────────────────────────
    print(f"\n  {BOLD}Now enter your {category}.{RESET}")
    num_options = _input_int(f"How many {category} do you want to compare? (min 2):", min_val=2)

    options: list[Option] = []
    for i in range(num_options):
        print(f"\n  {BOLD}─── {category.title()} {i + 1}/{num_options} ───{RESET}")
        name = _input_colored(f"  Name:").strip()

        values = {}
        for c in criteria:
            val = _input_float(f"  {c.name} ({c.unit or 'value'}):")
            values[c.key] = val

        options.append(Option(name=name, values=values))
        print(f"  {GREEN}✓ Added: {name}{RESET}")

    # ── Step 4: Run scoring ────────────────────────────────────────────
    print(f"\n  {DIM}Running scoring pipeline...{RESET}")

    try:
        ranked, norm_details = score_and_rank_options(options, criteria)
    except ValueError as e:
        print(f"\n{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    # Adapt ranked results for the explanation engine
    # (explanation_engine uses .laptop.get_raw_value, so we create an adapter)
    explanations = _explain_generic(ranked, criteria, norm_details)

    # Display
    print_ranked_table(ranked, criteria)
    print_explanations(explanations)

    # Sensitivity analysis
    if run_sensitivity_flag:
        print_sensitivity_analysis(options, criteria)

    # Recommendation
    _header("RECOMMENDATION")
    winner = explanations[0]
    print(f"\n  {GREEN}{BOLD}Best {category.title()}: {winner['name']}{RESET}")
    print(f"  Score: {_score_bar(winner['total_score'])}")
    print(f"  {winner['verdict']}\n")


def _explain_generic(ranked, criteria, norm_details) -> list[dict]:
    """
    Generate explanations for generic ScoredOption objects.
    Adapts the explanation engine's logic for the generic Option type.
    """
    from explanation_engine import _score_label

    explanations = []
    winner = ranked[0] if ranked else None

    for so in ranked:
        # Build breakdown
        breakdown = []
        for c in criteria:
            raw = so.option.get_raw_value(c.key)
            norm = so.normalized_scores[c.key]
            weighted = so.weighted_scores[c.key]
            label = _score_label(norm)
            unit = c.unit or ""
            dir_note = "↓ lower is better" if c.direction == "lower_is_better" else "↑ higher is better"
            raw_str = f"{raw:,.2f} {unit}".strip()
            breakdown.append(
                f"{c.name} ({int(c.weight*100)}%): {raw_str} [{dir_note}] "
                f"→ {norm:.2f}/10 ({label}) → weighted {weighted:.3f} pts"
            )

        # Strengths / weaknesses
        strengths = [c.name for c in criteria if so.normalized_scores[c.key] >= 7.0]
        weaknesses = [c.name for c in criteria if so.normalized_scores[c.key] <= 3.0]

        # Verdict
        score = so.total_score
        if score >= 7.5:
            quality = "a top-tier all-rounder"
        elif score >= 6.0:
            quality = "a strong contender"
        elif score >= 4.5:
            quality = "a solid mid-range choice"
        else:
            quality = "a niche option"

        if strengths and weaknesses:
            verdict = (
                f"{so.name} is {quality} that excels in "
                f"{', '.join(strengths)} but struggles with {', '.join(weaknesses)}."
            )
        elif strengths:
            verdict = f"{so.name} is {quality} with strong marks in {', '.join(strengths)}."
        elif weaknesses:
            verdict = f"{so.name} is {quality} held back by weak {', '.join(weaknesses)}."
        else:
            verdict = f"{so.name} is {quality} with balanced performance across all criteria."

        # vs winner
        vs_winner = None
        if so.rank > 1 and winner:
            biggest_gap_crit = max(
                criteria,
                key=lambda c: winner.weighted_scores[c.key] - so.weighted_scores[c.key],
            )
            gap = so.total_score - winner.total_score
            c = biggest_gap_crit
            vs_winner = (
                f"Trails {winner.name} by {abs(gap):.2f} pts overall. "
                f"Biggest gap: {c.name} "
                f"({so.normalized_scores[c.key]:.1f}/10 vs winner's "
                f"{winner.normalized_scores[c.key]:.1f}/10, weighted {int(c.weight*100)}%)."
            )

        explanations.append({
            "rank": so.rank,
            "name": so.name,
            "total_score": round(so.total_score, 3),
            "verdict": verdict,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "breakdown": breakdown,
            "vs_winner": vs_winner,
        })

    return explanations


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision_companion",
        description=(
            "Decision Companion — Algorithmic decision support using weighted scoring.\n\n"
            "Default mode compares laptops. Use --interactive to compare ANYTHING."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode — define your own criteria and options (works for anything).",
    )
    parser.add_argument(
        "--sensitivity", "-s",
        action="store_true",
        help="Run sensitivity analysis (vary each weight ±10%% and check if winner changes).",
    )
    parser.add_argument(
        "--weights",
        nargs=4,
        type=float,
        metavar=("PRICE", "PERF", "BATT", "WEIGHT"),
        help=(
            "Custom weights for laptop mode (decimals summing to 1.0). "
            "Order: Price Performance Battery Weight."
        ),
    )
    return parser


def build_criteria_from_weights(weights: list[float]) -> list[Criteria]:
    """Construct criteria list from user-supplied weights."""
    base = DEFAULT_CRITERIA
    custom = []
    for c, w in zip(base, weights):
        custom.append(Criteria(c.name, c.key, w, c.direction, c.unit))
    return custom


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Interactive mode ───────────────────────────────────────────────
    if args.interactive:
        run_interactive(run_sensitivity_flag=args.sensitivity)
        return

    # ── Default laptop mode ────────────────────────────────────────────
    if args.weights:
        criteria = build_criteria_from_weights(args.weights)
        weight_str = ", ".join(
            f"{c.name} {int(c.weight*100)}%" for c in criteria
        )
        print(f"\n  {DIM}Using custom weights: {weight_str}{RESET}")
    else:
        criteria = DEFAULT_CRITERIA

    try:
        laptops = load_laptops()
    except FileNotFoundError as e:
        print(f"\n{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    try:
        ranked, norm_details = score_and_rank(laptops, criteria)
    except ValueError as e:
        print(f"\n{RED}Configuration error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    explanations = explain_ranking(ranked, criteria, norm_details)

    print_ranked_table(ranked, criteria)
    print_explanations(explanations)

    if args.sensitivity:
        print_sensitivity_analysis(laptops, criteria)

    _header("RECOMMENDATION")
    winner_exp = explanations[0]
    print(f"\n  {GREEN}{BOLD}Best Choice: {winner_exp['name']}{RESET}")
    print(f"  Score: {_score_bar(winner_exp['total_score'])}")
    print(f"  {winner_exp['verdict']}\n")


if __name__ == "__main__":
    main()
