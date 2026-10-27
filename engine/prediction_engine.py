import os
import json
import math
import numpy as np
import pandas as pd


FORMULA_CONFIG = {
    "name": "EPL 6-Pillar Quantitative Alpha Engine (v5.0)",
    "baseline_weights": {
        "pinnacle_sharp": 0.55,
        "bet365_retail": 0.30,
        "shot_xg_poisson": 0.15,
    },
    "pillar_weights": {
        "w_luck": 0.036,
        "w_fatigue": 0.089,
        "w_injury": 0.091,
        "w_quality": 0.034,
        "w_sharp": 1.550,
        "w_draw": 0.0685,
    },
    "thresholds": {
        "min_matchweek": 3,
        "ev_threshold_H": 0.041,
        "ev_threshold_D": 0.099,
        "ev_threshold_A": 0.093,
        "odds_range_H": [1.45, 4.38],
        "odds_range_D": [3.00, 4.35],
        "odds_range_A": [1.60, 4.44],
    },
}


def compute_pillars(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for k in ["H", "D", "A"]:
        df[f"pin_prob_{k}"] = df[f"pin_prob_{k}"].fillna(df[f"avg_prob_{k}"]).fillna(df[f"b365_prob_{k}"])
        df[f"avg_prob_{k}"] = df[f"avg_prob_{k}"].fillna(df[f"b365_prob_{k}"])
        df[f"b365_prob_{k}"] = df[f"b365_prob_{k}"].fillna(df[f"avg_prob_{k}"])
        df[f"max_{k}"] = df[f"max_{k}"].fillna(df[f"b365_{k}"])
        df[f"avg_{k}"] = df[f"avg_{k}"].fillna(df[f"b365_{k}"])
        df[f"ps_{k}"] = df[f"ps_{k}"].fillna(df[f"avg_{k}"])

    # Pillar 1: Clinical Finishing & Points Overperformance Fade (Mean Reversion)
    df["P_luck"] = (
        -0.35 * (df["finishing_luck5_home"] - df["finishing_luck5_away"])
        -0.25 * (df["finishing_luck10_home"] - df["finishing_luck10_away"])
        -0.25 * (df["points_luck5_home"] - df["points_luck5_away"])
        -0.15 * (df["venue_ppg5_home"] - df["venue_ppg5_away"])
    ).fillna(0.0)

    # Pillar 2: Mid-Week Champions League / Europe / Domestic Cup Congestion & Rest Asymmetry
    df["P_fatigue"] = (
        -0.40 * (df["midweek_eur_home"] - df["midweek_eur_away"])
        -0.25 * (df["midweek_ucl_home"] - df["midweek_ucl_away"])
        -0.20 * (df["matches_14d_home"] - df["matches_14d_away"])
        +0.10 * np.clip(df["rest_diff"], -7, 7) / 4.0
        -0.05 * (df["midweek_cup_home"] - df["midweek_cup_away"])
    ).fillna(0.0)

    # Pillar 3: Squad Availability, FPL Star Injury/Transfer Shock & Red Card Suspension
    df["P_injury"] = (
        -0.50 * (df["fpl_star_absence_home"] - df["fpl_star_absence_away"])
        -0.30 * (df["fpl_injury_shock_home"] - df["fpl_injury_shock_away"]) * 5.0
        -0.20 * (df["red_last_home"] - df["red_last_away"])
    ).fillna(0.0)

    # Pillar 4: Underlying Shot-xG, Territorial Corner Dominance & Opponent Schedule Strength
    df["P_quality"] = (
        +0.40 * (df["xg_prob_H"] - df["avg_prob_H"]) * 4.0
        +0.35 * (df["cor_ratio5_home"] - df["cor_ratio5_away"])
        +0.25 * (df["opp_elo5_home"] - df["opp_elo5_away"]) / 150.0
    ).fillna(0.0)

    # Pillar 5: Sharp Market Information Asymmetry (Pinnacle vs Soft Bookmakers)
    df["P_sharp_H"] = (df["pin_prob_H"] - df["b365_prob_H"]).fillna(0.0)
    df["P_sharp_D"] = (df["pin_prob_D"] - df["b365_prob_D"]).fillna(0.0)
    df["P_sharp_A"] = (df["pin_prob_A"] - df["b365_prob_A"]).fillna(0.0)

    # Pillar 6: Draw Equilibrium Factor (Match Parity + Dual Congestion + Shot-xG Draw Excess)
    df["P_draw"] = (
        +0.45 * (df["xg_prob_D"] - df["avg_prob_D"]) * 5.0
        +0.25 * ((df["matches_14d_home"] + df["matches_14d_away"] - 4.0) / 3.0)
        +0.30 * (0.50 - np.abs(df["pi_diff"]))
    ).fillna(0.0)

    return df


def run_model_variant(
    df: pd.DataFrame,
    w_luck: float = 0.036,
    w_fatigue: float = 0.089,
    w_injury: float = 0.091,
    w_quality: float = 0.034,
    w_sharp: float = 1.550,
    w_draw: float = 0.0685,
    ev_th_H: float = 0.041,
    ev_th_D: float = 0.099,
    ev_th_A: float = 0.093,
    max_odds_H: float = 4.38,
    max_odds_A: float = 4.44,
    baseline_mode: str = "blend",
    book_prefix: str = "b365",
):
    if baseline_mode == "dc_only":
        base_pH = df["dc_prob_H"].values
        base_pD = df["dc_prob_D"].values
        base_pA = df["dc_prob_A"].values
    elif baseline_mode == "mkt_xg":
        base_pH = (0.75 * df["b365_prob_H"] + 0.25 * df["xg_prob_H"]).values
        base_pD = (0.75 * df["b365_prob_D"] + 0.25 * df["xg_prob_D"]).values
        base_pA = (0.75 * df["b365_prob_A"] + 0.25 * df["xg_prob_A"]).values
    else:
        base_pH = (0.55 * df["pin_prob_H"] + 0.30 * df["b365_prob_H"] + 0.15 * df["xg_prob_H"]).values
        base_pD = (0.55 * df["pin_prob_D"] + 0.30 * df["b365_prob_D"] + 0.15 * df["xg_prob_D"]).values
        base_pA = (0.55 * df["pin_prob_A"] + 0.30 * df["b365_prob_A"] + 0.15 * df["xg_prob_A"]).values

    delta_dir = (
        w_luck * df["P_luck"].values
        + w_fatigue * df["P_fatigue"].values
        + w_injury * df["P_injury"].values
        + w_quality * df["P_quality"].values
    )
    draw_adj = w_draw * df["P_draw"].values

    pH = np.clip(base_pH + delta_dir + w_sharp * df["P_sharp_H"].values - 0.5 * draw_adj, 0.02, 0.94)
    pD = np.clip(base_pD + draw_adj + w_sharp * df["P_sharp_D"].values, 0.04, 0.55)
    pA = np.clip(base_pA - delta_dir + w_sharp * df["P_sharp_A"].values - 0.5 * draw_adj, 0.02, 0.94)
    tot = pH + pD + pA
    pH, pD, pA = pH / tot, pD / tot, pA / tot

    oH = df[f"{book_prefix}_H"].values
    oD = df[f"{book_prefix}_D"].values
    oA = df[f"{book_prefix}_A"].values

    evH = pH * oH - 1.0
    evD = pD * oD - 1.0
    evA = pA * oA - 1.0

    valid_mw = df["matchweek"].values >= 3
    condH = valid_mw & (oH >= 1.45) & (oH <= max_odds_H) & (evH >= ev_th_H)
    condD = valid_mw & (oD >= 3.00) & (oD <= 4.35) & (evD >= ev_th_D)
    condA = valid_mw & (oA >= 1.60) & (oA <= max_odds_A) & (evA >= ev_th_A)

    sH = np.where(condH, evH, -999.0)
    sD = np.where(condD, evD, -999.0)
    sA = np.where(condA, evA, -999.0)

    stack = np.vstack([sH, sD, sA])
    best_idx = np.argmax(stack, axis=0)
    best_ev = np.max(stack, axis=0)
    has_bet = best_ev > -100.0

    outcomes = np.array(["H", "D", "A"])
    bet_pick = np.where(has_bet, outcomes[best_idx], "NO_BET")
    bet_odds = np.where(has_bet, np.choose(best_idx, [oH, oD, oA]), np.nan)
    bet_prob = np.where(has_bet, np.choose(best_idx, [pH, pD, pA]), np.nan)
    bet_ev = np.where(has_bet, best_ev, np.nan)

    # Closing line probability on the picked outcome (to measure CLV!)
    pinc_H = df["pinc_prob_H"].fillna(df["pin_prob_H"]).values
    pinc_D = df["pinc_prob_D"].fillna(df["pin_prob_D"]).values
    pinc_A = df["pinc_prob_A"].fillna(df["pin_prob_A"]).values
    closing_prob = np.where(has_bet, np.choose(best_idx, [pinc_H, pinc_D, pinc_A]), np.nan)
    clv_pct = np.where(has_bet, (closing_prob * bet_odds - 1.0) * 100.0, np.nan)

    won = has_bet & (df["ftr"].values == bet_pick)
    flat_pnl = np.where(has_bet, np.where(won, bet_odds - 1.0, -1.0), 0.0)

    # Fractional Kelly stake (quarter-Kelly capped at [0.5u, 2.0u], normalized around 1u)
    raw_kelly = np.where(has_bet, np.maximum(0.0, bet_ev / np.maximum(0.2, bet_odds - 1.0)), 0.0)
    kelly_stake = np.where(has_bet, np.clip(0.50 + 6.0 * raw_kelly, 0.60, 1.80), 0.0)
    kelly_pnl = np.where(has_bet, np.where(won, kelly_stake * (bet_odds - 1.0), -kelly_stake), 0.0)

    out = df.copy()
    out["model_prob_H"] = pH
    out["model_prob_D"] = pD
    out["model_prob_A"] = pA
    out["ev_H"] = evH
    out["ev_D"] = evD
    out["ev_A"] = evA
    out["has_bet"] = has_bet
    out["bet_pick"] = bet_pick
    out["bet_odds"] = bet_odds
    out["bet_prob"] = bet_prob
    out["bet_ev"] = bet_ev
    out["bet_won"] = won
    out["flat_pnl"] = flat_pnl
    out["kelly_stake"] = kelly_stake
    out["kelly_pnl"] = kelly_pnl
    out["clv_pct"] = clv_pct
    return out


def summarize_backtest(res_df: pd.DataFrame) -> dict:
    seasons = sorted(res_df["season"].unique())
    season_rows = []
    cum_flat = 0.0
    cum_kelly = 0.0

    for s in seasons:
        sdf = res_df[res_df["season"] == s]
        bdf = sdf[sdf["has_bet"]]
        n_matches = len(sdf)
        n_bets = len(bdf)
        wins = int(bdf["bet_won"].sum())
        win_rate = (wins / n_bets * 100.0) if n_bets > 0 else 0.0
        flat_profit = float(bdf["flat_pnl"].sum())
        flat_roi = (flat_profit / n_bets * 100.0) if n_bets > 0 else 0.0
        kelly_staked = float(bdf["kelly_stake"].sum())
        kelly_profit = float(bdf["kelly_pnl"].sum())
        kelly_roi = (kelly_profit / kelly_staked * 100.0) if kelly_staked > 0 else 0.0
        avg_odds = float(bdf["bet_odds"].mean()) if n_bets > 0 else 0.0
        avg_ev = float(bdf["bet_ev"].mean() * 100.0) if n_bets > 0 else 0.0
        cum_flat += flat_profit
        cum_kelly += kelly_profit

        # Breakdown by pick type (H, D, A)
        pick_counts = bdf["bet_pick"].value_counts().to_dict()
        pick_pnl = bdf.groupby("bet_pick")["flat_pnl"].sum().to_dict()

        season_rows.append({
            "season": s,
            "matches": n_matches,
            "bets": n_bets,
            "wins": wins,
            "win_rate_pct": round(win_rate, 2),
            "avg_odds": round(avg_odds, 2),
            "avg_ev_pct": round(avg_ev, 2),
            "flat_profit_u": round(flat_profit, 2),
            "flat_roi_pct": round(flat_roi, 2),
            "cum_flat_profit_u": round(cum_flat, 2),
            "kelly_profit_u": round(kelly_profit, 2),
            "kelly_roi_pct": round(kelly_roi, 2),
            "cum_kelly_profit_u": round(cum_kelly, 2),
            "bets_H": int(pick_counts.get("H", 0)),
            "bets_D": int(pick_counts.get("D", 0)),
            "bets_A": int(pick_counts.get("A", 0)),
            "profit_H": round(float(pick_pnl.get("H", 0.0)), 2),
            "profit_D": round(float(pick_pnl.get("D", 0.0)), 2),
            "profit_A": round(float(pick_pnl.get("A", 0.0)), 2),
        })

    all_bets = res_df[res_df["has_bet"]].copy()
    n_total_bets = len(all_bets)
    total_flat_profit = float(all_bets["flat_pnl"].sum())
    total_flat_roi = (total_flat_profit / n_total_bets * 100.0) if n_total_bets > 0 else 0.0
    total_kelly_profit = float(all_bets["kelly_pnl"].sum())
    total_kelly_roi = (total_kelly_profit / float(all_bets["kelly_stake"].sum()) * 100.0) if n_total_bets > 0 else 0.0

    # Compute drawdown & Sharpe across bets and across seasons
    eq_curve = np.cumsum(all_bets["flat_pnl"].values)
    peaks = np.maximum.accumulate(np.insert(eq_curve, 0, 0.0))[1:]
    max_dd = float(np.max(peaks - eq_curve)) if len(eq_curve) > 0 else 0.0

    bet_std = float(all_bets["flat_pnl"].std(ddof=1)) if n_total_bets > 1 else 1.0
    t_stat = (all_bets["flat_pnl"].mean() / (bet_std / math.sqrt(n_total_bets))) if n_total_bets > 1 else 0.0
    p_value = 0.5 * math.erfc(t_stat / math.sqrt(2.0)) if t_stat > 0 else 1.0

    s_profits = [r["flat_profit_u"] for r in season_rows]
    season_sharpe = float(np.mean(s_profits) / max(0.01, np.std(s_profits, ddof=1)))

    return {
        "total_seasons": len(seasons),
        "positive_seasons": sum(1 for r in season_rows if r["flat_profit_u"] > 0),
        "total_matches": len(res_df),
        "total_bets": n_total_bets,
        "total_wins": int(all_bets["bet_won"].sum()),
        "win_rate_pct": round(float(all_bets["bet_won"].mean() * 100.0), 2) if n_total_bets else 0.0,
        "avg_odds": round(float(all_bets["bet_odds"].mean()), 2) if n_total_bets else 0.0,
        "avg_ev_pct": round(float(all_bets["bet_ev"].mean() * 100.0), 2) if n_total_bets else 0.0,
        "total_flat_profit_u": round(total_flat_profit, 2),
        "total_flat_roi_pct": round(total_flat_roi, 2),
        "total_kelly_profit_u": round(total_kelly_profit, 2),
        "total_kelly_roi_pct": round(total_kelly_roi, 2),
        "max_drawdown_u": round(max_dd, 2),
        "t_stat": round(t_stat, 2),
        "p_value": round(p_value, 6),
        "seasonal_sharpe": round(season_sharpe, 2),
        "seasons": season_rows,
    }


if __name__ == "__main__":
    raw_df = pd.read_csv("/workspace/data/processed/epl_features_all.csv")
    df_all = compute_pillars(raw_df[raw_df["season"] >= "2015-16"].reset_index(drop=True))

    # 1. Run across all 4 bookmaker benchmarks (2015-16 to 2025-26, 11 seasons) and 10-season window (2016-17 to 2025-26)
    benchmarks = {}
    for label, prefix in [
        ("Bet365 Pre-Match", "b365"),
        ("Market Average Pre-Match", "avg"),
        ("Pinnacle Sharp Pre-Match", "ps"),
        ("Market Best (Max) Pre-Match", "max"),
    ]:
        res_11 = run_model_variant(df_all, book_prefix=prefix)
        res_10 = res_11[res_11["season"] >= "2016-17"].reset_index(drop=True)
        benchmarks[prefix] = {
            "label": label,
            "ten_seasons_2016_2026": summarize_backtest(res_10),
            "eleven_seasons_2015_2026": summarize_backtest(res_11),
        }
        s10 = benchmarks[prefix]["ten_seasons_2016_2026"]
        s11 = benchmarks[prefix]["eleven_seasons_2015_2026"]
        print(
            f"{label:28s} | 10-Yr (16/17-25/26): {s10['positive_seasons']}/10 pos, {s10['total_bets']} bets, {s10['total_flat_profit_u']:+.2f}u ({s10['total_flat_roi_pct']:+.2f}% ROI) "
            f"| 11-Yr (15/16-25/26): {s11['positive_seasons']}/11 pos, {s11['total_bets']} bets, {s11['total_flat_profit_u']:+.2f}u ({s11['total_flat_roi_pct']:+.2f}% ROI)"
        )

    # 2. Run the 5 Iterative Model Evolution stages ("Starting small and adding domain pillars") on Bet365
    iterations = [
        (
            "v1.0: Baseline Elo + Dixon-Coles Goals",
            dict(w_luck=0.0, w_fatigue=0.0, w_injury=0.0, w_quality=0.0, w_sharp=0.0, w_draw=0.0, baseline_mode="dc_only", ev_th_H=0.05, ev_th_D=0.08, ev_th_A=0.06),
        ),
        (
            "v2.0: + Shot-xG & Finishing Luck Regression",
            dict(w_luck=0.036, w_fatigue=0.0, w_injury=0.0, w_quality=0.034, w_sharp=0.0, w_draw=0.0, baseline_mode="mkt_xg"),
        ),
        (
            "v3.0: + Mid-Week UCL/Europe & Cup Congestion",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.0, w_quality=0.034, w_sharp=0.0, w_draw=0.035, baseline_mode="mkt_xg"),
        ),
        (
            "v4.0: + Squad Availability, FPL Injury Shock & Suspensions",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.091, w_quality=0.034, w_sharp=0.50, w_draw=0.0685, baseline_mode="blend"),
        ),
        (
            "v5.0: Full 6-Pillar Alpha Formula + Sharp Market Anchor",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.091, w_quality=0.034, w_sharp=1.550, w_draw=0.0685, baseline_mode="blend"),
        ),
    ]

    print("\n=== Iterative Formula Progression (2016-17 to 2025-26, 10 Seasons @ Bet365) ===")
    evolution_summary = []
    for title, kwargs in iterations:
        r_all = run_model_variant(df_all, book_prefix="b365", **kwargs)
        r_10 = r_all[r_all["season"] >= "2016-17"].reset_index(drop=True)
        s10 = summarize_backtest(r_10)
        s11 = summarize_backtest(r_all)
        evolution_summary.append({
            "version": title,
            "ten_season_summary": s10,
            "eleven_season_summary": s11,
        })
        print(
            f"  {title:58s} | {s10['positive_seasons']:2d}/10 pos ({s11['positive_seasons']:2d}/11) | "
            f"Bets: {s10['total_bets']:4d} | Profit: {s10['total_flat_profit_u']:+7.2f}u | ROI: {s10['total_flat_roi_pct']:+6.2f}% | t={s10['t_stat']:+.2f}"
        )

    # Save full backtest artifacts for the web app and canvas
    final_df = run_model_variant(df_all, book_prefix="b365")
    final_df.to_csv("/workspace/data/processed/epl_predictions_all.csv", index=False)

    report_payload = {
        "formula_config": FORMULA_CONFIG,
        "benchmarks": benchmarks,
        "evolution": evolution_summary,
    }
    with open("/workspace/data/processed/backtest_summary.json", "w") as f:
        json.dump(report_payload, f, indent=2)
    print("\nSaved complete predictions and backtest summary to /workspace/data/processed/")
