# Decision Companion

A CLI-based decision support system that helps you choose between options using a **Weighted Scoring Algorithm**. Built around the principle that good decisions require transparent, auditable logic — not black-box AI outputs.

## What It Does

Given a set of options and weighted criteria, the system:

1. **Normalises** every raw spec to a 0–10 scale (min-max normalisation)
2. **Scores** each option as a weighted sum of normalised values
3. **Ranks** all options and explains why each placed where it did
4. **Challenges its own recommendation** via sensitivity analysis — showing exactly how much any weight has to shift before the winner changes

## Quick Start

```bash
# Clone the repo
git clone https://github.com/arpansusheel/decision-companion.git
cd decision-companion

# (Optional) activate your virtual environment
source venv/bin/activate

# Default laptop comparison — Price 40%, Performance 30%, Battery 20%, Weight 10%
python3 main.py

# With sensitivity analysis
python3 main.py --sensitivity

# Custom weights (must sum to 1.0) — order: Price Performance Battery Weight
python3 main.py --weights 0.2 0.5 0.2 0.1

# Help
python3 main.py --help
```

### Interactive Mode — Compare Anything

Use `--interactive` (or `-i`) to compare **any type of option** — cars, phones, apartments, job offers, universities, etc. You define your own criteria and enter your own options:

```bash
# Interactive mode — you define everything
python3 main.py --interactive

# Interactive mode + sensitivity analysis
python3 main.py --interactive --sensitivity
```

The interactive mode walks you through:
1. **What you're comparing** (e.g. "cars")
2. **Your criteria** — name, direction (higher/lower is better), unit, weight
3. **Your options** — enter a value for each criterion per option
4. **Results** — full ranking, explanations, and optional sensitivity analysis

## Algorithm

```
Score(option) = Σ (normalised_score[criterion] × criterion.weight)
```

**Normalisation** converts raw specs to a 0–10 scale:

| Direction | Formula |
|---|---|
| Higher is better (performance, battery) | `(value − min) / (max − min) × 10` |
| Lower is better (price, weight) | `(max − value) / (max − min) × 10` |

**Default criteria weights:**

| Criterion | Key | Weight | Direction |
|---|---|---|---|
| Price | `price_usd` | 40% | Lower is better |
| Performance | `performance` | 30% | Higher is better |
| Battery Life | `battery_hours` | 20% | Higher is better |
| Weight | `weight_kg` | 10% | Lower is better |

## Project Structure

```
decision_companion/
├── main.py                  # CLI entry point (default + interactive modes)
├── decision_engine.py       # Weighted scoring + ranking pipeline
├── explanation_engine.py    # Algorithmic explanation generation
├── normalizer.py            # Min-max normalisation
├── sensitivity_analysis.py  # Standout feature — robustness testing
├── models.py                # Criteria, Laptop, Option, ScoredOption dataclasses
├── data/
│   └── laptops.json         # Default laptop dataset (6 options)
├── .gitignore
├── README.md
├── BUILD_PROCESS.md         # Engineering process journal
└── RESEARCH_LOG.md          # Research & decision log
```

## Sensitivity Analysis

The standout feature. For each criterion, the system:

- Shifts its weight **±10 percentage points** and redistributes the remainder proportionally
- Runs the full scoring pipeline with the adjusted weights
- Records whether the winner changes
- **Finds the tipping point**: the minimum shift to flip the winner (via 1% incremental scan)
- Outputs a **rank-shift matrix** showing how every option moves across all scenarios

This makes the confidence in the recommendation quantifiable, not just qualitative.

**Example output:**
```
Tipping Points (smallest weight shift to flip the winner):
  Price          decrease: +2%
  Performance    increase: +3%
  Battery Life   increase: +2%
  Weight         stable within ±50%
```

## Sample Output

```
🥇 1  Acer Swift 3               10.00       0.00       2.00       6.89      5.089
🥈 2  Apple MacBook Air M2        5.56       1.98       6.80       8.38      5.015
🥉 3  Apple MacBook Pro M3        0.00       7.35      10.00       4.19      4.624
   4  Lenovo ThinkPad X1 Carbon   3.56       2.82       4.40      10.00      4.148
   5  ASUS ROG Zephyrus G14       1.67      10.00       0.40       2.84      4.030
   6  Dell XPS 15                 2.22       5.09       0.00       0.00      2.415
```

## Design Principles

- **Algorithmic, not AI**: All scoring and explanations are computed from data — no LLM calls anywhere in the scoring pipeline.
- **Normalization is required**: Raw values like price and Cinebench scores are on incompatible scales. Skipping normalization would produce meaningless results.
- **Explainability first**: Every score is fully decomposable — you can trace exactly why any option ranked anywhere.
- **Transparency over simplicity**: The sensitivity analysis is there specifically to show when you _shouldn't_ be confident in the result.

## Dynamic, Not Hardcoded

This system is **not static**. Users control every input and get different outcomes based on their choices:

| Method | What the user controls | Command |
|---|---|---|
| **Custom weights** | Change how much each criterion matters | `python3 main.py --weights 0.1 0.6 0.2 0.1` |
| **Interactive mode** | Define own criteria, options, and values from scratch | `python3 main.py --interactive` |
| **Sensitivity analysis** | See how outcomes shift when priorities change | `python3 main.py --sensitivity` |

**Example**: With default weights (Price 40%), the budget Acer Swift 3 wins. Run `--weights 0.1 0.5 0.2 0.2` (Performance 50%), and the high-performance ASUS ROG Zephyrus jumps to #1. Different inputs → different outcomes, every time.

In interactive mode, users can compare **any category** — cars, phones, apartments, job offers — with their own criteria and values. Nothing is hardcoded.

## Fully Explainable — Not a Black Box

Every number is **traceable and verifiable by hand**. For each option, the system shows:

```
• Price (40%): $699 [↓ lower is better] → 10.00/10 (excellent) → weighted 4.000 pts
```

That one line exposes the entire calculation chain:
1. **Raw value** ($699) — what the option actually has
2. **Direction** (↓ lower is better) — how this criterion is evaluated
3. **Normalised score** (10.00/10) — computed from the min-max formula
4. **Adjective label** (excellent) — human-readable interpretation
5. **Weighted contribution** (4.000 pts) — normalised score × criterion weight

A user can verify by hand:
- Min price = $699, Max price = $1,599
- `(1599 − 699) / (1599 − 699) × 10 = 10.0 ✓`
- `10.0 × 0.40 = 4.0 ✓`

**There is no AI, no LLM, and no neural network anywhere in the scoring or explanation pipeline.** It is pure arithmetic — transparent and auditable from start to finish.

## Interactive Mode Example (Cars)

```bash
python3 main.py --interactive
```

```
What are you comparing? cars

Criterion 1/3: Price     — weight 40%, ↓ lower is better
Criterion 2/3: Fuel Efficiency — weight 35%, ↑ higher is better
Criterion 3/3: Horsepower    — weight 25%, ↑ higher is better

Ranked Results:
🥇 1  Honda Civic      — 7.500/10  (best price + fuel efficiency)
🥈 2  Toyota Camry     — 6.021/10  (balanced across all criteria)
🥉 3  BMW 3 Series     — 2.500/10  (best horsepower, but most expensive)
```

Works for any domain — just define your criteria and enter your options.
