# Research Log — Decision Companion

This log captures every research question and development conversation that shaped the project, in chronological order. Each entry documents *what was discussed*, *what was decided*, and *why*.

---

## Entry 1 — Why Weighted Scoring Over Other Methods

**Context**: Starting the project, the first question was which MCDA (Multi-Criteria Decision Analysis) method to use.

**Conversation**: Looked at the evaluation criteria — "problem structuring, decision logic, explainability, engineering maturity, transparency." This pointed strongly toward a method whose internals are fully visible, not a black-box.

**Research summary**:

| Method | Strength | Weakness |
|---|---|---|
| Simple Additive Weighting (SAW) | Transparent, easy to explain | Assumes linear preferences |
| TOPSIS | Considers both ideal and anti-ideal | Less intuitive output |
| AHP | Derives weights from pairwise comparisons | Complex setup, overkill for 4 criteria |
| ELECTRE | Handles incomparability | Very complex, hard to explain |

**Decision**: SAW (weighted scoring), because:
1. The output — a score on a known scale — is directly explainable to a non-technical user
2. Weights are elicited directly (user states their priorities), not derived via complex pairwise comparisons
3. With only 4 criteria and 6 options, the added complexity of TOPSIS or ELECTRE adds no decision quality

**Reference**: Triantaphyllou, E. (2000). *Multi-Criteria Decision Making Methods: A Comparative Study*. Springer.

---

## Entry 2 — Normalization: Min-Max vs. Z-Score

**Context**: Before writing `normalizer.py`, had to decide how to bring raw values (price in USD, performance in Cinebench points, weight in kg) onto a common scale.

**Conversation**: The core question was "should a user see a score of -1.4 for a laptop?" — z-score normalisation would produce results like that. The evaluation specifically calls for *explainability*, which means scores need to be intuitive.

**Research summary**:

| Approach | Output range | Interpretable? | Handles outliers? |
|---|---|---|---|
| Min-max | [0, N] (bounded) | Yes — 0 is worst, N is best | No — outliers compress others |
| Z-score | Unbounded, can be negative | Less so for lay users | Yes — robust to outliers |
| Vector normalisation | [0, 1] | Moderate | No |

**Decision**: Min-max to a 0–10 scale, because:
- The 0–10 output is intuitive and makes the score directly comparable to the final weighted score
- With only 6 laptops from known market segments, extreme outliers are unlikely
- "This laptop scored 8.9/10 on price" is more communicable than "this laptop has a z-score of 1.4"

**Edge case discussed**: If all options share the same value for a criterion (range = 0), all receive 10.0. The alternative (assigning 5.0 / "neutral") was considered but rejected — if nothing differentiates on a criterion, no option should be penalised for it.

---

## Entry 3 — Weight Elicitation and Default Weights

**Context**: Needed defensible default weights for the laptop comparison.

**Conversation**: Reviewed consumer decision research on laptop purchase priorities to ground the defaults in data rather than arbitrary choices.

**Key findings**:
- Price is consistently the #1 or #2 consideration (Gartner, 2023 Consumer PC survey; Statista consumer electronics reports)
- Performance is #1 for power users, #2-3 for general consumers
- Battery life has grown in importance post-pandemic (remote work shifts)
- Physical weight matters for frequent travellers but rarely for home users

**Chosen weights and rationale**:

| Criterion | Weight | Rationale |
|---|---|---|
| Price | 40% | Single largest purchase barrier; affects broadest population |
| Performance | 30% | Core functional requirement for most users |
| Battery Life | 20% | Critical for portability; growing in post-pandemic priority |
| Weight | 10% | Relevant but secondary for most; matters mainly to frequent flyers |

**Note**: These are *default* weights. The system supports custom weights via `--weights` and interactive mode precisely because individual priorities vary.

---

## Entry 4 — Cinebench R23 as the Performance Metric

**Context**: Laptops have many possible performance metrics — needed to pick one that's comparable across architectures.

**Options considered**:
- Cinebench R23 (multi-core) — CPU rendering throughput
- Geekbench 6 (multi-core) — general CPU throughput
- SPECrate2017 — more rigorous, less commonly published
- Passmark — composite score across CPU/GPU/memory

**Decision**: Cinebench R23 multi-core, because:
- Most widely published benchmark in laptop reviews (Notebookcheck, The Verge, Wirecutter all use it)
- Architecture-neutral (Apple Silicon and x86 tested on the same workload)
- Measures real sustained CPU throughput, not burst performance

**Limitation acknowledged**: Does not capture GPU performance, which matters for gaming/creative workloads. Acceptable for v1 — GPU could be added as a fifth criterion.

---

## Entry 5 — Sensitivity Analysis Design

**Context**: After the basic ranking was working, the question was how to make the system *self-critical* — not just "here's the answer" but "here's how much you should trust it."

**Conversation**: Looked at two main approaches from MCDA literature.

**Two approaches**:
1. **One-at-a-time (OAT)**: Vary one weight at a time, hold others constant → doesn't maintain sum-to-1 constraint
2. **Proportional redistribution**: When focal weight changes, scale others proportionally → maintains sum-to-1

**Decision**: Proportional redistribution (approach 2), because:
- Holding others constant breaks the weights-sum-to-1 invariant, which corrupts the score scale
- Proportional redistribution models the realistic mental model: "I care more about X, so I care proportionally less about everything else"

**Tipping-point search design**: Added because a binary yes/no per ±10% scenario is coarse. A tipping point at 2% is very different from 45% — both produce "winner changed" at 10%, but convey completely different confidence levels. Implemented as a 1% incremental scan per criterion.

---

## Entry 6 — No External Dependencies

**Context**: Considered using pandas, numpy, or rich for the project.

**Decision**: Python standard library only.

**Rationale**:
- Demonstrates algorithmic capability without framework scaffolding
- No `pip install` required — anyone with Python 3.10+ can run immediately
- Keeps the evaluation focus on decision logic, not library usage

**What was deliberately not used**:
- `pandas` — data volume is tiny, `dataclass` + `list` is sufficient
- `numpy` — only min/max would benefit, Python builtins handle it
- `rich` / `colorama` — ANSI escape codes achieve coloured output without dependencies

---

## Entry 7 — Making the System Domain-Agnostic (Interactive Mode)

**Context**: After the full laptop pipeline was working and verified (default mode, sensitivity, custom weights all passing), the key question came up during our development conversation:

> *"Can it work for all options and according to the options that the user gives, including all details?"*

This was the turning point — the system needed to go from "a laptop comparison tool" to "a decision comparison tool that happens to ship with a laptop demo."

**Conversation flow**:
1. First reaction: "Right now it's hardcoded to laptops with 4 fixed criteria."
2. Design question: Should users edit JSON files, or should the CLI guide them?
3. Decision: Fully interactive CLI — users shouldn't need to touch any code or files.

**Research/Design decisions**:

| Question | Decision | Why |
|---|---|---|
| New dataclass or reuse Laptop? | New generic `Option` dataclass with dynamic `values: dict` | Laptop has hardcoded fields; generic options need arbitrary criteria |
| Replace Laptop code or keep both? | Keep both side-by-side | Default laptop mode is the primary evaluation demo; don't break it |
| Where do generic explanations come from? | `_explain_generic()` adapter in main.py | Reuses the same algorithmic logic but works with `ScoredOption` instead of `ScoredLaptop` |
| How does sensitivity detect the type? | `isinstance(items[0], Option)` in `_run_scoring()` | Simple, reliable, no configuration needed |

**What was built**:
- `models.py` → `Option`, `ScoredOption` dataclasses
- `normalizer.py` → `normalize_options()` function
- `decision_engine.py` → `score_and_rank_options()` function
- `sensitivity_analysis.py` → `_run_scoring()` type auto-detection
- `main.py` → `run_interactive()` with guided prompts, `--interactive` / `-i` flag

**Verified with**: Cars (Toyota Camry, Honda Civic, BMW 3 Series) — Honda Civic ranked #1 at 7.5/10. Also verified default laptop mode still works identically.

---

## Entry 8 — Documentation Approach

**Context**: The evaluation criteria mention "transparency" — the evaluator should understand not just *what* was built but *how* and *why*.

**Decision**: Three separate documents, each with a distinct purpose.

| Document | Purpose | Audience |
|---|---|---|
| `README.md` | How to use the system — quick start, commands, examples | End user |
| `BUILD_PROCESS.md` | Engineering journal — what was built and why, step by step | Technical evaluator |
| `RESEARCH_LOG.md` | This document — research questions, alternatives, conversations, decisions | Anyone auditing the decision-making process |

**Principle**: The research log should read like a development diary — capturing the actual questions that came up during building, the conversations that led to decisions, and the reasoning behind each choice. Not a polished report, but a transparent record of the thought process.

---

## Summary of Key Conversations

| # | Question | Decision |
|---|---|---|
| 1 | Which MCDA method? | SAW — transparent, explainable, appropriate scale |
| 2 | Min-max or z-score? | Min-max to 0–10 — intuitive, bounded |
| 3 | Default weights? | Price 40%, Perf 30%, Battery 20%, Weight 10% — grounded in consumer research |
| 4 | Performance metric? | Cinebench R23 — widely published, architecture-neutral |
| 5 | Sensitivity approach? | Proportional redistribution — maintains weight invariant |
| 6 | External deps? | Zero — stdlib only, algorithmic focus |
| 7 | Domain-agnostic? | Interactive CLI mode — user defines everything at runtime |
| 8 | Documentation style? | Three docs with distinct purposes — transparency over polish |
