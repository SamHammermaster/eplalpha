import os
import json
import math
import numpy as np
import pandas as pd
from prediction_engine import compute_pillars, run_model_variant, summarize_backtest, FORMULA_CONFIG


def build_dashboard_json():
    raw_df = pd.read_csv("/workspace/data/processed/epl_features_all.csv")
    df = compute_pillars(raw_df[raw_df["season"] >= "2015-16"].reset_index(drop=True))

    # 1. Benchmarks across all 4 bookmakers
    benchmarks = {}
    for label, prefix in [
        ("Bet365 Pre-Match", "b365"),
        ("Market Average Pre-Match", "avg"),
        ("Pinnacle Sharp Pre-Match", "ps"),
        ("Market Best (Max) Pre-Match", "max"),
    ]:
        res_11 = run_model_variant(df, book_prefix=prefix)
        res_10 = res_11[res_11["season"] >= "2016-17"].reset_index(drop=True)
        benchmarks[prefix] = {
            "label": label,
            "ten_seasons": summarize_backtest(res_10),
            "eleven_seasons": summarize_backtest(res_11),
        }

    # 2. Iterative Evolution (v1.0 -> v5.0)
    iterations = [
        (
            "v1.0",
            "Baseline Elo + Dixon-Coles Goals",
            "Pure historical goals & multi-division Elo vs pre-match odds (no xG, fatigue, or squad context).",
            dict(w_luck=0.0, w_fatigue=0.0, w_injury=0.0, w_quality=0.0, w_sharp=0.0, w_draw=0.0, baseline_mode="dc_only", ev_th_H=0.05, ev_th_D=0.08, ev_th_A=0.06),
        ),
        (
            "v2.0",
            "+ Shot-xG & Finishing Luck Regression",
            "Fades unsustainable clinical goal conversion (Goals - Shot-xG) and rewards territorial dominance & schedule strength.",
            dict(w_luck=0.036, w_fatigue=0.0, w_injury=0.0, w_quality=0.034, w_sharp=0.0, w_draw=0.0, baseline_mode="mkt_xg"),
        ),
        (
            "v3.0",
            "+ Mid-Week UCL/Europe & Cup Congestion",
            "Penalizes clubs playing within 5 days of UEFA Champions/Europa League or domestic cup ties and high 14-day congestion.",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.0, w_quality=0.034, w_sharp=0.0, w_draw=0.035, baseline_mode="mkt_xg"),
        ),
        (
            "v4.0",
            "+ Squad Availability, FPL Injury Shock & Suspensions",
            "Integrates pre-deadline FPL transfer-out shocks on top-5 ICT stars, star minutes missing, and red-card suspensions.",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.091, w_quality=0.034, w_sharp=0.50, w_draw=0.0685, baseline_mode="blend"),
        ),
        (
            "v5.0",
            "Full 6-Pillar Alpha Formula + Sharp Market Anchor",
            "Combines all 6 domain pillars with Pinnacle sharp-vs-retail divergence and regime-calibrated EV thresholds.",
            dict(w_luck=0.036, w_fatigue=0.089, w_injury=0.091, w_quality=0.034, w_sharp=1.550, w_draw=0.0685, baseline_mode="blend"),
        ),
    ]

    evolution = []
    for code, name, desc, kwargs in iterations:
        r11 = run_model_variant(df, book_prefix="b365", **kwargs)
        r10 = r11[r11["season"] >= "2016-17"].reset_index(drop=True)
        s10 = summarize_backtest(r10)
        s11 = summarize_backtest(r11)
        evolution.append({
            "code": code,
            "name": name,
            "description": desc,
            "ten_seasons": s10,
            "eleven_seasons": s11,
        })

    # 3. Domain Pillar Analytics & Ablation Study
    res_main = run_model_variant(df, book_prefix="b365")
    res_H_mkt = (df["ftr"] == "H").astype(float) - df["b365_prob_H"]

    pillar_specs = [
        ("P_luck", "Pillar 1: Finishing & Points Luck Regression", "w_luck = 0.036", "Fades teams scoring above Shot-xG & xPts over prior 5-10 matches"),
        ("P_fatigue", "Pillar 2: Mid-Week UCL/Europe & Cup Fatigue", "w_fatigue = 0.089", "Penalizes mid-week UEFA/Cup turnaround, 14-day congestion & rest deficit"),
        ("P_injury", "Pillar 3: Star Injury Shock & Suspensions", "w_injury = 0.091", "Penalizes top-5 ICT star absences, FPL pre-deadline transfer-out shocks & red cards"),
        ("P_quality", "Pillar 4: Shot-xG, Corners & Schedule Strength", "w_quality = 0.034", "Rewards underlying Shot-xG edge, corner dominance & opponent Elo schedule"),
        ("P_sharp_H", "Pillar 5: Sharp (Pinnacle) vs Soft Divergence", "w_sharp = 1.550", "Captures syndicate money steamed into Pinnacle vs lagging retail bookmakers"),
        ("P_draw", "Pillar 6: Draw Equilibrium & Parity", "w_draw = 0.0685", "Boosts draw probability in low-pi-diff matches with dual-team congestion"),
    ]

    pillar_analytics = []
    for col, title, weight_str, desc in pillar_specs:
        target_res = res_H_mkt if col != "P_draw" else ((df["ftr"] == "D").astype(float) - df["b365_prob_D"])
        corr = float(np.corrcoef(df[col].fillna(0), target_res.fillna(0))[0, 1])
        pos_s = 0
        for _, grp in df.groupby("season"):
            c_s = np.corrcoef(df.loc[grp.index, col].fillna(0), target_res.loc[grp.index].fillna(0))[0, 1]
            if c_s > 0:
                pos_s += 1
        pillar_analytics.append({
            "id": col,
            "title": title,
            "weight": weight_str,
            "description": desc,
            "correlation": round(corr, 4),
            "positive_seasons_11": pos_s,
        })

    # 4. Special Context Breakdowns on Qualified Bets (Bet365, 2015-16 to 2025-26)
    bets_df = res_main[res_main["has_bet"]].copy()

    def slice_stats(mask, name, desc):
        sub = bets_df[mask]
        n = len(sub)
        w = int(sub["bet_won"].sum())
        p = float(sub["flat_pnl"].sum())
        return {
            "slice": name,
            "description": desc,
            "bets": n,
            "wins": w,
            "win_rate_pct": round(w / n * 100.0, 1) if n else 0.0,
            "avg_odds": round(float(sub["bet_odds"].mean()), 2) if n else 0.0,
            "profit_u": round(p, 2),
            "roi_pct": round(p / n * 100.0, 2) if n else 0.0,
        }

    opp_midweek_eur = (
        ((bets_df["bet_pick"] == "H") & ((bets_df["midweek_eur_away"] == 1) | (bets_df["matches_14d_away"] >= 4)))
        | ((bets_df["bet_pick"] == "A") & ((bets_df["midweek_eur_home"] == 1) | (bets_df["matches_14d_home"] >= 4)))
    )
    luck_fade_mask = (
        ((bets_df["bet_pick"] == "H") & (bets_df["P_luck"] > 0.15))
        | ((bets_df["bet_pick"] == "A") & (bets_df["P_luck"] < -0.15))
    )
    injury_edge_mask = (
        ((bets_df["bet_pick"] == "H") & (bets_df["P_injury"] > 0.08))
        | ((bets_df["bet_pick"] == "A") & (bets_df["P_injury"] < -0.08))
    )
    sharp_confirm_mask = (
        ((bets_df["bet_pick"] == "H") & (bets_df["P_sharp_H"] > 0.005))
        | ((bets_df["bet_pick"] == "A") & (bets_df["P_sharp_A"] > 0.005))
        | ((bets_df["bet_pick"] == "D") & (bets_df["P_sharp_D"] > 0.005))
    )

    regime_slices = [
        slice_stats(opp_midweek_eur, "Fading Mid-Week UCL/Europe & Congested Opponent", "Betting against a team returning from midweek UEFA competition or 4+ games in 14d"),
        slice_stats(luck_fade_mask, "Shot-xG Finishing Luck Mean-Reversion", "Betting when finishing luck differential |P_luck| > 0.15 favors our side"),
        slice_stats(injury_edge_mask, "Star Injury / Suspension Asymmetry", "Betting against a club with top-5 ICT star absences, FPL transfer-out shock, or red card"),
        slice_stats(sharp_confirm_mask, "Sharp Pinnacle Steam Confirmation", "Pinnacle de-vigged probability exceeds retail Bet365 implied probability by >0.5%"),
        slice_stats(bets_df["bet_pick"] == "H", "Home Value Selections (1.45 - 4.38)", "All qualified Home win value bets (EV >= +4.1%)"),
        slice_stats(bets_df["bet_pick"] == "A", "Away Value Selections (1.60 - 4.44)", "All qualified Away win value bets (EV >= +9.3%)"),
        slice_stats(bets_df["bet_pick"] == "D", "Draw Equilibrium Selections (3.00 - 4.35)", "High-parity, congested stalemate draw value bets (EV >= +9.9%)"),
    ]

    # 5. Latest Club Ratings Snapshot (entering current state / end of 2025-26) for Interactive Predictor
    df_2526 = df[df["season"] == "2025-26"]
    active_teams = sorted(set(df_2526["home_team"].unique()) | set(df_2526["away_team"].unique()))
    team_profiles = {}
    for t in active_teams:
        t_rows = df[(df["home_team"] == t) | (df["away_team"] == t)].tail(5)
        last_row = t_rows.iloc[-1]
        is_h = last_row["home_team"] == t
        team_profiles[t] = {
            "team": t,
            "elo": round(float(last_row["elo_home" if is_h else "elo_away"]), 1),
            "pi_rating": round(float(last_row["pi_home" if is_h else "pi_away"]), 3),
            "dc_att": round(float(last_row["dc_att_home" if is_h else "dc_att_away"]), 3),
            "dc_def": round(float(last_row["dc_def_home" if is_h else "dc_def_away"]), 3),
            "ppg5": round(float(last_row["ppg5_home" if is_h else "ppg5_away"]), 2),
            "finishing_luck5": round(float(last_row["finishing_luck5_home" if is_h else "finishing_luck5_away"]), 2),
            "cor_ratio5": round(float(last_row["cor_ratio5_home" if is_h else "cor_ratio5_away"]), 3),
            "opp_elo5": round(float(last_row["opp_elo5_home" if is_h else "opp_elo5_away"]), 1),
            "fpl_ict5": round(float(last_row["fpl_ict5_home" if is_h else "fpl_ict5_away"]), 1),
        }

    # 6. Export all 953 qualified value bets for the Bet Ledger Explorer
    bet_ledger = []
    for _, r in bets_df.sort_values("date", ascending=False).iterrows():
        bet_ledger.append({
            "date": r["date"],
            "season": r["season"],
            "mw": int(r["matchweek"]),
            "home": r["home_team"],
            "away": r["away_team"],
            "score": f"{int(r['fthg'])}-{int(r['ftag'])}",
            "ftr": r["ftr"],
            "pick": r["bet_pick"],
            "odds": round(float(r["bet_odds"]), 2),
            "model_prob": round(float(r["bet_prob"] * 100.0), 1),
            "mkt_prob": round(float((1.0 / r["bet_odds"]) * 100.0), 1),
            "ev_pct": round(float(r["bet_ev"] * 100.0), 1),
            "won": bool(r["bet_won"]),
            "pnl": round(float(r["flat_pnl"]), 2),
            "kelly_pnl": round(float(r["kelly_pnl"]), 2),
            "P_luck": round(float(r["P_luck"]), 3),
            "P_fatigue": round(float(r["P_fatigue"]), 3),
            "P_injury": round(float(r["P_injury"]), 3),
            "P_quality": round(float(r["P_quality"]), 3),
            "midweek_eur_h": int(r["midweek_eur_home"]),
            "midweek_eur_a": int(r["midweek_eur_away"]),
            "rest_diff": int(r["rest_diff"]),
        })

    # 7. Compact array of all 4,180 matches so the browser can run live custom formula simulations!
    sim_matches = []
    for _, r in res_main.iterrows():
        sim_matches.append([
            r["season"],
            int(r["matchweek"]),
            r["ftr"],
            round(float(0.55 * r["pin_prob_H"] + 0.30 * r["b365_prob_H"] + 0.15 * r["xg_prob_H"]), 4),
            round(float(0.55 * r["pin_prob_D"] + 0.30 * r["b365_prob_D"] + 0.15 * r["xg_prob_D"]), 4),
            round(float(0.55 * r["pin_prob_A"] + 0.30 * r["b365_prob_A"] + 0.15 * r["xg_prob_A"]), 4),
            round(float(r["P_luck"]), 4),
            round(float(r["P_fatigue"]), 4),
            round(float(r["P_injury"]), 4),
            round(float(r["P_quality"]), 4),
            round(float(r["P_sharp_H"]), 4),
            round(float(r["P_sharp_D"]), 4),
            round(float(r["P_sharp_A"]), 4),
            round(float(r["P_draw"]), 4),
            round(float(r["b365_H"]), 2) if pd.notna(r["b365_H"]) else 0.0,
            round(float(r["b365_D"]), 2) if pd.notna(r["b365_D"]) else 0.0,
            round(float(r["b365_A"]), 2) if pd.notna(r["b365_A"]) else 0.0,
            round(float(r["avg_H"]), 2) if pd.notna(r["avg_H"]) else 0.0,
            round(float(r["avg_D"]), 2) if pd.notna(r["avg_D"]) else 0.0,
            round(float(r["avg_A"]), 2) if pd.notna(r["avg_A"]) else 0.0,
            round(float(r["max_H"]), 2) if pd.notna(r["max_H"]) else 0.0,
            round(float(r["max_D"]), 2) if pd.notna(r["max_D"]) else 0.0,
            round(float(r["max_A"]), 2) if pd.notna(r["max_A"]) else 0.0,
        ])

    payload = {
        "formula_config": FORMULA_CONFIG,
        "benchmarks": benchmarks,
        "evolution": evolution,
        "pillar_analytics": pillar_analytics,
        "regime_slices": regime_slices,
        "team_profiles": team_profiles,
        "bet_ledger": bet_ledger,
        "sim_matches": sim_matches,
    }

    os.makedirs("/workspace/src/data", exist_ok=True)
    out_path = "/workspace/src/data/epl_dashboard_data.json"
    with open(out_path, "w") as f:
        json.dump(payload, f)
    print(f"Exported dashboard data to {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    build_dashboard_json()
