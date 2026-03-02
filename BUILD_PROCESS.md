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

### Step 9: Interactive Mode — Domain-Agnostic Extension

**Trigger**: After the default laptop pipeline was working, the question came up: *"Can it work for all options and according to the options that the user gives?"* — meaning the system should not be locked to laptops.

**Design approach**: Rather than forcing users to edit JSON files and Python code, I built a fully interactive CLI mode (`--interactive` / `-i`) where users define everything at runtime:

1. **Category**: User names what they're comparing (cars, phones, apartments, etc.)
2. **Criteria**: User defines each criterion — name, direction (h/l), unit, weight
3. **Options**: User enters each option with a value per criterion
4. Full pipeline runs on the user-defined input

**Implementation changes required**:
- `models.py`: Added generic `Option` (name + dynamic values dict) and `ScoredOption` dataclasses alongside the existing `Laptop`/`ScoredLaptop` — kept both to avoid breaking the default mode
- `normalizer.py`: Added `normalize_options()` for generic types
- `decision_engine.py`: Added `score_and_rank_options()` for generic types
- `sensitivity_analysis.py`: Added `_run_scoring()` auto-detection — checks `isinstance(items[0], Option)` to route to the correct scoring function
- `main.py`: Added `run_interactive()` with guided prompts, input validation, and the `_explain_generic()` adapter for explanation generation

**Alternative considered**: Making everything generic-only and removing the Laptop-specific code. Rejected because:
- The default laptop mode is the primary demo for the evaluation
- Having both modes shows extensibility without sacrificing the focused demonstration

**Tested with**: Cars comparison (Price 40%, Fuel Efficiency 35%, Horsepower 25%) with Toyota Camry, Honda Civic, BMW 3 Series — Honda Civic ranked #1 at 7.5/10.

---

## Mistakes and Corrections

Real engineering involves iteration. Here are the mistakes made during the build and how each was corrected:

### Mistake 1: Sensitivity analysis was inline in `main.py`

**What happened**: The sensitivity analysis was initially written as a ~90-line function directly inside `main.py`. It worked, but it violated the single-responsibility principle — `main.py` was now doing CLI rendering, argument parsing, *and* statistical analysis.

**Correction**: Extracted the entire sensitivity analysis into its own `sensitivity_analysis.py` module with proper dataclasses (`Scenario`, `SensitivityReport`), a `run_sensitivity()` function, and a `format_report()` renderer. `main.py` went from 90 lines of inline analysis to a single delegate call.

**Lesson**: It's tempting to keep things in one file while prototyping, but extracting early leads to cleaner code and easier testing.

---

### Mistake 2: `__pycache__` committed to git

**What happened**: When committing the interactive mode changes, Python's `__pycache__/` directory (containing `.pyc` bytecode files) was accidentally included in the commit. These are auto-generated build artifacts that shouldn't be in version control.

**Correction**: Added a `.gitignore` file with standard Python exclusions (`__pycache__/`, `*.pyc`, `venv/`, etc.) and ran `git rm -r --cached __pycache__/` to remove the cached files from the repo.

**Lesson**: Always create `.gitignore` at project initialisation, not after the first accidental commit.

---

### Mistake 3: README not updated after interactive mode

**What happened**: The README was written on Day 3 when the system was laptop-only. After adding the interactive mode (`--interactive`), the README still said "Given a set of options (currently laptops)" and the "Extending to Other Domains" section told users to manually edit JSON files and Python code — even though the interactive mode had made that unnecessary.

**Correction**: Updated the README with an "Interactive Mode — Compare Anything" section, a cars comparison example, and replaced the old extension instructions with interactive mode documentation.

**Lesson**: Documentation must be updated alongside code, not after. A README that describes capabilities the system doesn't have (or misses capabilities it does) is misleading.

---

### Mistake 4: BUILD_PROCESS and RESEARCH_LOG fell behind

**What happened**: After adding the interactive mode and updating the README, both the BUILD_PROCESS and RESEARCH_LOG were still describing only the Day 1–3 work. The interactive mode design conversation, the domain-agnostic architecture decisions, and the development chat history were missing.

**Correction**: Added Step 9 (interactive mode) to BUILD_PROCESS with full design rationale, and rewrote RESEARCH_LOG to capture the actual development conversations (8 entries total) rather than just polished conclusions.

**Lesson**: Living documents need to stay alive. If you add a major feature, update all documentation — not just the user-facing README.

## Git Commit History

```
74906da  docs: update README and BUILD_PROCESS for interactive mode
63f156e  chore: add .gitignore and remove cached pycache files
ad6ea67  feat: add fully interactive mode — compare ANY options with custom criteria
b4c3ceb  docs: add README, BUILD_PROCESS, and RESEARCH_LOG
0c6171c  feat: extract sensitivity analysis into standalone module
a67e2cc  feat: add explanation engine and CLI entry point
294db2f  feat: implement weighted scoring engine with full pipeline
777792c  feat: implement min-max normalizer (0-10 scale, direction-aware)
08cbf43  data: add 6-laptop dataset covering budget to premium tier
39f2250  feat: add Criteria, Laptop, ScoredLaptop dataclasses with full validation
d4aa3f5  project initialization: folder structure and empty files
```

---

## What I Would Do Next

- Add a `--delta` CLI flag to customise the sensitivity shift magnitude
- Write pytest unit tests for the normalizer edge cases and weight validation
- Add `--export json` to save results to a file for dashboarding
- Support loading custom options from JSON files (`--data custom.json`)
