# Build Process Journal — Decision Companion

This document captures the engineering process chronologically: what was built, why each design decision was made, what alternatives were considered, and what was learned.

---

## Day 1 — Foundation

### Step 1: Project Structure

**Decision**: Separate modules for models, normalization, scoring, explanation, and sensitivity — rather than one monolithic `main.py`.

**Rationale**: Each module has a single, clearly defined responsibility. This makes the system testable, readable, and extensible. An evaluator should be able to read `normalizer.py` in isolation and understand exactly what it does.

**Alternative considered**: A single-file script. Rejected because it conflates responsibilities and makes the logic harder to audit.

---

### Step 2: Data Models (`models.py`)

Used Python `@dataclass` for `Criteria`, `Laptop`, and `ScoredLaptop`.

**Key choices**:
- `Criteria.direction` is a `Literal["lower_is_better", "higher_is_better"]` — forces explicit handling of both cases in the normalizer, making bugs impossible to silently ignore.
- `ScoredLaptop` wraps a `Laptop` rather than inheriting from it — composition over inheritance keeps the raw data immutable.
- Validators in `__post_init__` catch bad data at construction time, not at scoring time.

---

### Step 3: Dataset (`data/laptops.json`)

**Selected 6 laptops** spanning budget to premium:
- Acer Swift 3 — budget baseline
- MacBook Air M2 — balanced Apple option
- ThinkPad X1 Carbon — business/portability focus
- Dell XPS 15 — premium Windows performance
- MacBook Pro M3 — high-end Apple
- ASUS ROG Zephyrus G14 — gaming/max performance

**Rationale for spread**: A dataset with all similar laptops produces near-identical scores and makes normalization meaningless. Wide value spread (price: $699–$1599, performance: 6500–18200 pts) ensures the algorithm has genuine differentiation to work with.

**Performance metric**: Cinebench R23 multi-core benchmark was chosen because it is:
- Widely published and comparable across platforms
- CPU-representative (the primary performance bottleneck for most workloads)
- Single-number, which maps cleanly to the scoring model

---

### Step 4: Normalizer (`normalizer.py`)

**Algorithm**: Min-max normalisation to 0–10 scale.

**Why min-max over z-score (standard deviation normalisation)**:
- Min-max produces bounded, interpretable scores (0–10)
- Z-score produces unbounded values and can produce negatives — harder to explain to a non-technical user
- For a small dataset with known value ranges, min-max is the appropriate choice

**Edge case**: When all options have the same value for a criterion (range = 0), all receive `10.0`. This is a deliberate "neutral" choice — if no option is differentiated on a criterion, they should all receive full credit for it rather than penalising the entire group.

---

## Day 2 — Core Logic

### Step 5: Decision Engine (`decision_engine.py`)

**Pipeline**: `load_laptops → normalize → apply weights → sort → assign ranks`

**Weight validation**: `_validate_weights()` raises `ValueError` if weights don't sum to 1.0 within floating-point tolerance (1e-6). This is a critical guard — weights that don't sum to 1.0 break the 0–10 score scale interpretation.

**Custom criteria support**: `score_and_rank()` accepts an optional `criteria` argument. This was designed specifically to support the sensitivity analysis module, which needs to re-run scoring with modified weights without modifying global state.

---

### Step 6: Explanation Engine (`explanation_engine.py`)

**Design principle**: All explanation text is generated algorithmically from score data — no LLM involvement.

**What the engine produces**:
1. **Breakdown**: For each criterion, shows the raw value, normalised score, adjective label, and weighted contribution — so a reader can verify the math manually.
2. **Strengths/Weaknesses**: Criteria where the normalised score ≥ 7.0 are strengths; ≤ 3.0 are weaknesses. These thresholds were chosen to avoid labelling average performance as either strong or weak.
3. **Verdict**: One-line profile summary assembled from the score tier and strength/weakness pattern.
4. **Gap to winner**: Identifies the criterion with the largest weighted-score gap to the #1 option — telling the reader specifically what would need to change.

---

### Step 7: CLI (`main.py`)

**Features**:
- Default run, `--sensitivity`, `--weights` flags
- Coloured terminal output using ANSI escape codes (no external dependencies)
- ASCII score bars for visual score comparison
- Medal emojis for top 3

**Dependency philosophy**: Zero external dependencies. The entire project runs on Python standard library + built-ins. This was a deliberate choice to demonstrate algorithmic capability without framework scaffolding.

---

## Day 3 — Standout Feature + Documentation

### Step 8: Sensitivity Analysis (`sensitivity_analysis.py`)

This is the most analytically sophisticated component.

**Three outputs**:

1. **Scenario table**: ±10% weight shifts, winner stability per scenario.

2. **Tipping-point search**: For each criterion, scans 1% increments to find the minimum weight shift that flips the winner. This is more useful than the scenario table because it quantifies fragility precisely.

   Example: "Price weight only needs to drop 2% before the winner changes." That's a much stronger statement than "the winner changes when Price drops 10%."

3. **Rank-shift matrix**: Shows how every laptop's rank changes across every scenario. Useful for identifying which options are consistently mid-tier vs. which oscillate depending on priorities.

**Why this is the standout feature**:
Most decision-support tools give you a recommendation. Good decision-support tells you when to trust it. Sensitivity analysis operationalises that: the stability score directly answers "how confident should I be?"

---

## What I Would Do Next

- Add a `--delta` CLI flag to customise the sensitivity shift magnitude
- Write pytest unit tests for the normalizer edge cases and weight validation
- Support additional domains (cars, apartments) via a plugin-style data loader
- Export results to JSON for downstream use or dashboarding
