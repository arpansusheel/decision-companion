# Research Log — Decision Companion

This log captures research questions that came up during the project, what I investigated, and what conclusions were reached. Entries are in chronological order.

---

## Entry 1 — Why Weighted Scoring Over Other Methods

**Question**: Multi-Criteria Decision Analysis (MCDA) has many methods — TOPSIS, AHP, ELECTRE, SAW. Which is most appropriate here?

**Research summary**:

| Method | Strength | Weakness |
|---|---|---|
| Simple Additive Weighting (SAW) | Transparent, easy to explain | Assumes linear preferences |
| TOPSIS | Considers both ideal and anti-ideal | Less intuitive output |
| AHP | Derives weights from pairwise comparisons | Complex setup, overkill for 4 criteria |
| ELECTRE | Handles incomparability | Very complex, hard to explain |

**Conclusion**: SAW (the weighted scoring approach used here) is the right choice for this project because:
1. The output — a score on a known scale — is directly explainable to a non-technical user
2. Weights are elicited directly (user states their priorities), not derived via complex pairwise comparisons
3. With only 4 criteria and 6 options, the added complexity of TOPSIS or ELECTRE adds no decision quality

**Reference**: Triantaphyllou, E. (2000). *Multi-Criteria Decision Making Methods: A Comparative Study*. Springer.

---

## Entry 2 — Normalization: Min-Max vs. Z-Score

**Question**: Should values be normalised using min-max or z-score standardisation?

**Research summary**:

| Approach | Output range | Interpretable? | Handles outliers? |
|---|---|---|---|
| Min-max | [0, N] (bounded) | Yes — 0 is worst, N is best | No — outliers compress others |
| Z-score | Unbounded, can be negative | Less so for lay users | Yes — robust to outliers |
| Vector normalisation | [0, 1] | Moderate | No |

**Conclusion**: Min-max to a 0–10 scale was chosen because:
- The 0–10 output is intuitive and makes the score directly comparable to the final weighted score
- With only 6 laptops from known market segments, extreme outliers are unlikely
- The evaluation criterion requires explainability — "this laptop scored 8.9/10 on price" is more communicable than "this laptop has a z-score of 1.4"

**Edge case documented**: If all options share the same value for a criterion (range = 0), all receive 10.0. The alternative (assigning 5.0 / "neutral") was considered but rejected — if nothing differentiates on a criterion, no option should be penalised for it.

---

## Entry 3 — Weight Elicitation

**Question**: How should the default weights be chosen, and are they defensible?

**Research**: Reviewed consumer decision research on laptop purchase priorities.

Key findings:
- Price is consistently the #1 or #2 consideration in laptop purchases (Gartner, 2023 Consumer PC survey; Statista consumer electronics reports)
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

**Note**: These are *default* weights. The system explicitly supports custom weights via `--weights` precisely because individual priorities vary. The sensitivity analysis then shows whether the recommendation is robust to those variations.

---

## Entry 4 — Cinebench R23 as the Performance Metric

**Question**: What benchmark score should represent "performance"?

**Options considered**:
- Cinebench R23 (multi-core) — CPU rendering throughput
- Geekbench 6 (multi-core) — general CPU throughput
- SPECrate2017 — more rigorous, less commonly published
- Passmark — composite score across CPU/GPU/memory

**Conclusion**: Cinebench R23 multi-core was chosen because:
- It is the most widely published benchmark in laptop reviews (Notebookcheck, The Verge, Wirecutter all use it)
- It is architecture-neutral (Apple Silicon and x86 are both tested on the same workload)
- It measures real sustained CPU throughput, not burst performance

**Limitation acknowledged**: Cinebench does not capture GPU performance, which matters for gaming and creative workloads. This is an acceptable simplification for v1 — GPU could be added as a fifth criterion if the domain is narrowed to gaming or creative laptops.

---

## Entry 5 — Sensitivity Analysis Design

**Question**: How should "sensitivity" be formally defined and tested?

**Research**: Reviewed sensitivity analysis approaches in MCDA literature.

**Two main approaches**:
1. **One-at-a-time (OAT)**: Vary one weight at a time, hold others constant → doesn't maintain sum-to-1 constraint
2. **Proportional redistribution**: When focal weight changes, scale others proportionally → maintains sum-to-1

**Conclusion**: Proportional redistribution (approach 2) was implemented because:
- Holding others constant breaks the weights-sum-to-1 invariant, which corrupts the score scale
- Proportional redistribution models the realistic "I care more about X, so I care proportionally less about everything else" mental model

**Tipping-point search**: The smallest-shift-to-flip-winner was added because a binary yes/no per ±10% scenario is coarse. A tipping point at 2% is very different from a tipping point at 45% — both produce the same "winner changed" answer at 10%, but convey completely different confidence levels.

---

## Entry 6 — No External Dependencies

**Decision**: The project uses only Python standard library.

**Rationale**:
- Demonstrates algorithmic capability without framework scaffolding
- No `pip install` required — anyone with Python 3.10+ can run it immediately
- Keeps the evaluation focus on the logic, not library usage

**What was deliberately not used**:
- `pandas` — not needed; data volume is tiny and `dataclass` + `list` is sufficient
- `numpy` — the only operation that would benefit is min/max, which Python's builtins handle
- `rich` / `colorama` — ANSI escape codes achieve the coloured output without dependencies
