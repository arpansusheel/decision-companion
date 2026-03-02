"""
streamlit_app.py — Web interface for the Decision Companion System.

Provides a browser-based UI for comparing options using weighted scoring.
Supports both the default laptop dataset and custom interactive comparisons.
"""

import streamlit as st
import json
from pathlib import Path

from models import Criteria, Laptop, Option
from decision_engine import (
    DEFAULT_CRITERIA,
    load_laptops,
    score_and_rank,
    score_and_rank_options,
)
from explanation_engine import explain_ranking
from sensitivity_analysis import run_sensitivity

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Decision Companion",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #333;
    }
    .winner-card {
        background: linear-gradient(135deg, #0d4e2c 0%, #1a5c3a 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2d8a5e;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def score_label(score: float) -> str:
    if score >= 8.5: return "🟢 Excellent"
    elif score >= 6.5: return "🟡 Good"
    elif score >= 4.0: return "🟠 Average"
    elif score >= 2.0: return "🔴 Below Avg"
    else: return "⚫ Poor"


def render_score_bar(score: float, max_score: float = 10.0) -> str:
    pct = score / max_score * 100
    color = "#00ff88" if pct >= 70 else "#ffaa00" if pct >= 40 else "#ff4444"
    return f"""
    <div style="background: #222; border-radius: 8px; height: 24px; width: 100%; position: relative;">
        <div style="background: {color}; border-radius: 8px; height: 24px; width: {pct}%;"></div>
        <span style="position: absolute; right: 8px; top: 2px; font-size: 14px; color: white; font-weight: 600;">{score:.2f}/10</span>
    </div>
    """


MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Mode")
    mode = st.radio(
        "Choose comparison mode:",
        ["🔧 Default (Laptops)", "✨ Interactive (Anything)"],
        index=0,
        help="Default uses pre-loaded laptop data. Interactive lets you define everything."
    )

    st.markdown("---")
    run_sens = st.checkbox("📊 Run Sensitivity Analysis", value=False,
                           help="Test how robust the ranking is to weight changes")

    st.markdown("---")
    st.markdown("### 📖 About")
    st.markdown(
        "**Decision Companion** uses a Weighted Scoring Algorithm (SAW) "
        "to rank options transparently. Every score is traceable and "
        "verifiable by hand — **no AI, no black box.**"
    )
    st.markdown("[GitHub Repo](https://github.com/arpansusheel/decision-companion)")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="main-header">🎯 Decision Companion</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Transparent, algorithmic decision support — not a black box</p>',
            unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DEFAULT MODE
# ---------------------------------------------------------------------------

if mode == "🔧 Default (Laptops)":
    st.markdown("### 🖥️ Laptop Comparison")
    st.caption("6 laptops scored across 4 criteria using weighted scoring")

    # Weight sliders
    st.markdown("#### Adjust Criteria Weights")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        w_price = st.slider("💰 Price", 0.0, 1.0, 0.40, 0.05, help="Lower is better")
    with col2:
        w_perf = st.slider("⚡ Performance", 0.0, 1.0, 0.30, 0.05, help="Higher is better")
    with col3:
        w_batt = st.slider("🔋 Battery", 0.0, 1.0, 0.20, 0.05, help="Higher is better")
    with col4:
        w_weight = st.slider("⚖️ Weight", 0.0, 1.0, 0.10, 0.05, help="Lower is better")

    total_weight = w_price + w_perf + w_batt + w_weight

    if abs(total_weight - 1.0) > 0.01:
        st.error(f"⚠️ Weights must sum to 1.0 — currently {total_weight:.2f}. Adjust the sliders.")
    else:
        criteria = [
            Criteria("Price", "price_usd", round(w_price, 4), "lower_is_better", "USD"),
            Criteria("Performance", "performance", round(w_perf, 4), "higher_is_better", "pts"),
            Criteria("Battery Life", "battery_hours", round(w_batt, 4), "higher_is_better", "hrs"),
            Criteria("Weight", "weight_kg", round(w_weight, 4), "lower_is_better", "kg"),
        ]

        try:
            laptops = load_laptops()
            ranked, norm_details = score_and_rank(laptops, criteria)
            explanations = explain_ranking(ranked, criteria, norm_details)
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

        # Winner banner
        winner = ranked[0]
        st.markdown("---")
        col_w1, col_w2 = st.columns([1, 2])
        with col_w1:
            st.markdown(f"### 🏆 Best Choice")
            st.markdown(f"## {winner.name}")
        with col_w2:
            st.markdown(render_score_bar(winner.total_score), unsafe_allow_html=True)
            st.caption(explanations[0]["verdict"])

        # Ranking table
        st.markdown("---")
        st.markdown("### 📊 Full Rankings")

        for sl, exp in zip(ranked, explanations):
            medal = MEDAL.get(sl.rank, f"#{sl.rank}")
            with st.expander(f"{medal} Rank {sl.rank}: **{sl.name}** — {sl.total_score:.3f}/10", expanded=(sl.rank <= 3)):
                st.markdown(render_score_bar(sl.total_score), unsafe_allow_html=True)
                st.markdown(f"**{exp['verdict']}**")

                if exp["strengths"]:
                    st.success(f"💪 Strengths: {', '.join(exp['strengths'])}")
                if exp["weaknesses"]:
                    st.error(f"⚠️ Weaknesses: {', '.join(exp['weaknesses'])}")

                st.markdown("**Score Breakdown:**")
                for line in exp["breakdown"]:
                    st.markdown(f"- {line}")

                if exp["vs_winner"]:
                    st.info(f"📏 {exp['vs_winner']}")

        # Sensitivity
        if run_sens:
            st.markdown("---")
            st.markdown("### 🔬 Sensitivity Analysis")
            report = run_sensitivity(laptops, criteria)

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                color = "🟢" if report.stability_score >= 0.85 else ("🟡" if report.stability_score >= 0.55 else "🔴")
                st.metric("Stability Score", f"{report.stability_score:.0%}", report.stability_label)
            with col_s2:
                st.metric("Scenarios Tested", len(report.scenarios),
                          f"{sum(1 for s in report.scenarios if not s.winner_changed)} unchanged")

            st.markdown("#### Tipping Points")
            for crit_name, details in report.tipping_points.items():
                if "status" in details:
                    st.markdown(f"- **{crit_name}**: 🟢 {details['status']}")
                else:
                    parts = [f"{d}: ±{v*100:.0f}%" for d, v in details.items()]
                    st.markdown(f"- **{crit_name}**: {'  |  '.join(parts)}")

            st.markdown("#### Scenario Results")
            scenario_data = []
            for s in report.scenarios:
                scenario_data.append({
                    "Criterion": s.focal_criterion,
                    "Change": s.direction,
                    "New Weight": f"{s.adjusted_weights[s.focal_criterion]:.0%}",
                    "Winner": s.new_winner,
                    "Stable": "✅" if not s.winner_changed else "❌",
                })
            st.dataframe(scenario_data, use_container_width=True)


# ---------------------------------------------------------------------------
# INTERACTIVE MODE
# ---------------------------------------------------------------------------

else:
    st.markdown("### ✨ Interactive Mode — Compare Anything")
    st.caption("Define your own criteria and options — works for cars, phones, apartments, job offers, etc.")

    # Category
    category = st.text_input("What are you comparing?", placeholder="e.g. cars, phones, apartments",
                             value="options")

    st.markdown("---")

    # Criteria definition
    st.markdown("#### 📏 Define Your Criteria")
    num_criteria = st.number_input("Number of criteria", min_value=2, max_value=10, value=3)

    criteria_list = []
    cols_per_row = 3
    for i in range(int(num_criteria)):
        st.markdown(f"**Criterion {i+1}**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            name = st.text_input(f"Name", key=f"crit_name_{i}", placeholder="e.g. Price")
        with c2:
            direction = st.selectbox(f"Direction", ["lower_is_better", "higher_is_better"],
                                     key=f"crit_dir_{i}",
                                     format_func=lambda x: "↓ Lower is better" if x == "lower_is_better" else "↑ Higher is better")
        with c3:
            unit = st.text_input(f"Unit", key=f"crit_unit_{i}", placeholder="e.g. USD, kg")
        with c4:
            weight = st.number_input(f"Weight (0-1)", min_value=0.01, max_value=1.0,
                                      value=round(1.0 / num_criteria, 2), step=0.05,
                                      key=f"crit_weight_{i}")

        if name:
            criteria_list.append({
                "name": name,
                "key": name.lower().replace(" ", "_"),
                "direction": direction,
                "unit": unit,
                "weight": weight,
            })

    # Weight validation
    if criteria_list:
        total_w = sum(c["weight"] for c in criteria_list)
        if abs(total_w - 1.0) > 0.01:
            st.warning(f"⚠️ Weights sum to {total_w:.2f} — should be 1.0")

    st.markdown("---")

    # Options definition
    st.markdown(f"#### 📦 Enter Your {category.title()}")
    num_options = st.number_input(f"Number of {category}", min_value=2, max_value=20, value=3)

    options_list = []
    for i in range(int(num_options)):
        st.markdown(f"**{category.title()} {i+1}**")
        opt_name = st.text_input(f"Name", key=f"opt_name_{i}", placeholder=f"e.g. Option {i+1}")

        values = {}
        if criteria_list:
            cols = st.columns(len(criteria_list))
            for j, crit in enumerate(criteria_list):
                with cols[j]:
                    val = st.number_input(
                        f"{crit['name']} ({crit['unit'] or 'value'})",
                        key=f"opt_{i}_crit_{j}",
                        value=0.0,
                        step=0.1,
                        format="%.2f",
                    )
                    values[crit["key"]] = val

        if opt_name and values:
            options_list.append(Option(name=opt_name, values=values))

    # Run button
    st.markdown("---")
    if st.button("🚀 Run Comparison", type="primary", use_container_width=True):
        if len(criteria_list) < 2:
            st.error("Please define at least 2 criteria with names.")
        elif len(options_list) < 2:
            st.error(f"Please enter at least 2 {category} with names.")
        elif abs(sum(c["weight"] for c in criteria_list) - 1.0) > 0.01:
            st.error("Weights must sum to 1.0!")
        else:
            # Build Criteria objects
            criteria = [
                Criteria(c["name"], c["key"], c["weight"], c["direction"], c["unit"])
                for c in criteria_list
            ]

            try:
                ranked, norm_details = score_and_rank_options(options_list, criteria)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

            # Winner
            winner = ranked[0]
            st.markdown("---")
            st.markdown(f"### 🏆 Best {category.title()}: **{winner.name}**")
            st.markdown(render_score_bar(winner.total_score), unsafe_allow_html=True)

            # Full rankings
            st.markdown("### 📊 Full Rankings")
            for so in ranked:
                medal = MEDAL.get(so.rank, f"#{so.rank}")
                with st.expander(f"{medal} Rank {so.rank}: **{so.name}** — {so.total_score:.3f}/10",
                                 expanded=(so.rank <= 3)):
                    st.markdown(render_score_bar(so.total_score), unsafe_allow_html=True)

                    # Breakdown
                    st.markdown("**Score Breakdown:**")
                    for c in criteria:
                        raw = so.option.get_raw_value(c.key)
                        norm = so.normalized_scores[c.key]
                        weighted = so.weighted_scores[c.key]
                        label = score_label(norm)
                        dir_note = "↓ lower is better" if c.direction == "lower_is_better" else "↑ higher is better"
                        st.markdown(
                            f"- **{c.name}** ({int(c.weight*100)}%): {raw:,.2f} {c.unit} "
                            f"[{dir_note}] → {norm:.2f}/10 {label} → weighted **{weighted:.3f}** pts"
                        )

                    # Strengths/Weaknesses
                    strengths = [c.name for c in criteria if so.normalized_scores[c.key] >= 7.0]
                    weaknesses = [c.name for c in criteria if so.normalized_scores[c.key] <= 3.0]
                    if strengths:
                        st.success(f"💪 Strengths: {', '.join(strengths)}")
                    if weaknesses:
                        st.error(f"⚠️ Weaknesses: {', '.join(weaknesses)}")

            # Sensitivity
            if run_sens:
                st.markdown("---")
                st.markdown("### 🔬 Sensitivity Analysis")
                report = run_sensitivity(options_list, criteria)

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.metric("Stability Score", f"{report.stability_score:.0%}", report.stability_label)
                with col_s2:
                    st.metric("Scenarios Tested", len(report.scenarios))

                st.markdown("#### Tipping Points")
                for crit_name, details in report.tipping_points.items():
                    if "status" in details:
                        st.markdown(f"- **{crit_name}**: 🟢 {details['status']}")
                    else:
                        parts = [f"{d}: ±{v*100:.0f}%" for d, v in details.items()]
                        st.markdown(f"- **{crit_name}**: {'  |  '.join(parts)}")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.85rem;">'
    '🎯 Decision Companion — Algorithmic, Transparent, Explainable<br>'
    'Built with Python • Zero AI in the scoring pipeline • '
    '<a href="https://github.com/arpansusheel/decision-companion" style="color: #667eea;">GitHub</a>'
    '</div>',
    unsafe_allow_html=True,
)
