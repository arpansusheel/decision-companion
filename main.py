"""
main.py — CLI entry point for the Decision Companion System.

Usage:
    python main.py                          # Run with default criteria
    python main.py --sensitivity            # Include sensitivity analysis
    python main.py --weights 0.5 0.3 0.1 0.1   # Custom weights (Price Perf Batt Weight)
    python main.py --help                   # Show help

The CLI outputs:
  1. Ranked results table
  2. Per-laptop explanations
  3. (Optional) Sensitivity analysis
"""

import argparse
import sys

from decision_engine import DEFAULT_CRITERIA, load_laptops, score_and_rank
from explanation_engine import explain_ranking
from models import Criteria
from sensitivity_analysis import run_sensitivity, format_report


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
RESET = "\033[0m"

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


def _header(text: str) -> None:
    width = 70
    print(f"\n{CYAN}{BOLD}{'─' * width}{RESET}")
    print(f"{CYAN}{BOLD}  {text}{RESET}")
    print(f"{CYAN}{BOLD}{'─' * width}{RESET}")


def _score_bar(score: float, max_score: float = 10.0, width: int = 20) -> str:
    """Render a simple ASCII progress bar for a score."""
    filled = int((score / max_score) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:.3f}/10"


def print_ranked_table(ranked, criteria) -> None:
    _header("RANKED RESULTS")
    col_widths = [4, 32, 12, 12, 12, 12, 12]
    headers = ["Rank", "Laptop", "Price(40%)", "Perf(30%)", "Batt(20%)", "Wt(10%)", "TOTAL"]
    row_fmt = "{:<4} {:<32} {:>10} {:>10} {:>10} {:>10} {:>10}"

    print(f"\n  {BOLD}" + row_fmt.format(*headers) + RESET)
    print(f"  {'─' * 92}")

    crit_keys = [c.key for c in criteria]
    for sl in ranked:
        medal = MEDAL.get(sl.rank, "  ")
        norm_cols = [f"{sl.normalized_scores[k]:.2f}" for k in crit_keys]
        total_str = f"{BOLD}{sl.total_score:.3f}{RESET}"
        color = GREEN if sl.rank == 1 else (YELLOW if sl.rank == 2 else RESET)
        print(
            f"  {color}{medal} {sl.rank:<2} {sl.name:<32}"
            + "".join(f" {v:>10}" for v in norm_cols)
            + f" {sl.total_score:>10.3f}{RESET}"
        )
    print(f"\n  {DIM}(Values shown are normalized 0–10 scores, not raw specs){RESET}\n")


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


def print_sensitivity_analysis(laptops, criteria) -> None:
    """Run sensitivity analysis via the dedicated module and print the report."""
    report = run_sensitivity(laptops, criteria)
    print(format_report(report, criteria))


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision_companion",
        description=(
            "Decision Companion — Algorithmic laptop ranking using weighted scoring.\n"
            "Criteria: Price (40%), Performance (30%), Battery (20%), Weight (10%)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="Run sensitivity analysis (vary each weight ±10%% and check if winner changes).",
    )
    parser.add_argument(
        "--weights",
        nargs=4,
        type=float,
        metavar=("PRICE", "PERF", "BATT", "WEIGHT"),
        help=(
            "Custom weights as decimals summing to 1.0. "
            "Order: Price Performance Battery Weight. "
            "Example: --weights 0.5 0.3 0.1 0.1"
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

    # Build criteria
    if args.weights:
        criteria = build_criteria_from_weights(args.weights)
        weight_str = ", ".join(
            f"{c.name} {int(c.weight*100)}%" for c in criteria
        )
        print(f"\n  {DIM}Using custom weights: {weight_str}{RESET}")
    else:
        criteria = DEFAULT_CRITERIA

    # Load data
    try:
        laptops = load_laptops()
    except FileNotFoundError as e:
        print(f"\n{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    # Run scoring pipeline
    try:
        ranked, norm_details = score_and_rank(laptops, criteria)
    except ValueError as e:
        print(f"\n{RED}Configuration error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    # Generate explanations
    explanations = explain_ranking(ranked, criteria, norm_details)

    # Display
    print_ranked_table(ranked, criteria)
    print_explanations(explanations)

    # Sensitivity analysis (optional)
    if args.sensitivity:
        print_sensitivity_analysis(laptops, criteria)

    _header("RECOMMENDATION")
    winner_exp = explanations[0]
    print(f"\n  {GREEN}{BOLD}Best Choice: {winner_exp['name']}{RESET}")
    print(f"  Score: {_score_bar(winner_exp['total_score'])}")
    print(f"  {winner_exp['verdict']}\n")


if __name__ == "__main__":
    main()
