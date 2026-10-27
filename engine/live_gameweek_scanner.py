import argparse
import json
import math
import pandas as pd
import numpy as np
from data_pipeline import devig_power, dixon_coles_probs
from prediction_engine import FORMULA_CONFIG


def load_latest_team_states(features_csv: str = "/workspace/data/processed/epl_features_all.csv") -> dict:
    """
    Extracts the latest walk-forward pre-match state for every Premier League club
    so you can score upcoming fixtures live each Gameweek.
    """
    df = pd.read_csv(features_csv)
    teams = sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    states = {}
    for t in teams:
        sub = df[(df["home_team"] == t) | (df["away_team"] == t)]
        if sub.empty:
            continue
        r = sub.iloc[-1]
        is_h = r["home_team"] == t
        states[t] = {
            "team": t,
            "elo": float(r["elo_home" if is_h else "elo_away"]),
            "pi_rating": float(r["pi_home" if is_h else "pi_away"]),
            "dc_att": float(r["dc_att_home" if is_h else "dc_att_away"]),
            "dc_def": float(r["dc_def_home" if is_h else "dc_def_away"]),
            "finishing_luck5": float(r["finishing_luck5_home" if is_h else "finishing_luck5_away"]),
            "finishing_luck10": float(r["finishing_luck10_home" if is_h else "finishing_luck10_away"]),
            "points_luck5": float(r["points_luck5_home" if is_h else "points_luck5_away"]),
            "venue_ppg5": float(r["venue_ppg5_home" if is_h else "venue_ppg5_away"]),
            "cor_ratio5": float(r["cor_ratio5_home" if is_h else "cor_ratio5_away"]),
            "opp_elo5": float(r["opp_elo5_home" if is_h else "opp_elo5_away"]),
        }
    return states


def evaluate_live_fixture(fixture: dict, team_states: dict) -> dict:
    """
    Scores a single upcoming Premier League fixture using the v5.0 6-Pillar Formula.
    """
    h = fixture["home_team"]
    a = fixture["away_team"]
    sh = team_states.get(h, {
        "elo": 1500.0, "pi_rating": 0.0, "dc_att": 1.0, "dc_def": 1.0,
        "finishing_luck5": 0.0, "finishing_luck10": 0.0, "points_luck5": 0.0,
        "venue_ppg5": 1.40, "cor_ratio5": 0.50, "opp_elo5": 1500.0,
    })
    sa = team_states.get(a, {
        "elo": 1500.0, "pi_rating": 0.0, "dc_att": 1.0, "dc_def": 1.0,
        "finishing_luck5": 0.0, "finishing_luck10": 0.0, "points_luck5": 0.0,
        "venue_ppg5": 1.20, "cor_ratio5": 0.50, "opp_elo5": 1500.0,
    })

    b365_H, b365_D, b365_A = float(fixture["b365_H"]), float(fixture["b365_D"]), float(fixture["b365_A"])
    pin_H = float(fixture.get("pin_H", b365_H))
    pin_D = float(fixture.get("pin_D", b365_D))
    pin_A = float(fixture.get("pin_A", b365_A))

    b365_pH, b365_pD, b365_pA = devig_power(b365_H, b365_D, b365_A)
    pin_pH, pin_pD, pin_pA = devig_power(pin_H, pin_D, pin_A)

    elo_diff = sh["elo"] - sa["elo"]
    lam_h = 1.52 * sh["dc_att"] * sa["dc_def"] * (10.0 ** (elo_diff / 1800.0))
    lam_a = 1.24 * sa["dc_att"] * sh["dc_def"] * (10.0 ** (-elo_diff / 1800.0))
    xg_pH, xg_pD, xg_pA, _ = dixon_coles_probs(lam_h, lam_a, rho=-0.11)

    # Pillar 1: Clinical Finishing & Points Luck Fade
    p_luck = (
        -0.35 * (sh["finishing_luck5"] - sa["finishing_luck5"])
        -0.25 * (sh["finishing_luck10"] - sa["finishing_luck10"])
        -0.25 * (sh["points_luck5"] - sa["points_luck5"])
        -0.15 * (sh["venue_ppg5"] - sa["venue_ppg5"])
    )

    # Pillar 2: Mid-Week Champions League / Europe / Cup Congestion & Rest Asymmetry
    mid_eur_h = int(fixture.get("midweek_eur_home", 0))
    mid_eur_a = int(fixture.get("midweek_eur_away", 0))
    mid_ucl_h = int(fixture.get("midweek_ucl_home", 0))
    mid_ucl_a = int(fixture.get("midweek_ucl_away", 0))
    mid_cup_h = int(fixture.get("midweek_cup_home", 0))
    mid_cup_a = int(fixture.get("midweek_cup_away", 0))
    m14_h = int(fixture.get("matches_14d_home", 2))
    m14_a = int(fixture.get("matches_14d_away", 2))
    rest_diff = float(fixture.get("rest_days_home", 7) - fixture.get("rest_days_away", 7))

    p_fatigue = (
        -0.40 * (mid_eur_h - mid_eur_a)
        -0.25 * (mid_ucl_h - mid_ucl_a)
        -0.20 * (m14_h - m14_a)
        +0.10 * np.clip(rest_diff, -7, 7) / 4.0
        -0.05 * (mid_cup_h - mid_cup_a)
    )

    # Pillar 3: Squad Availability, FPL Star Injury Transfer Shock & Red Card Suspension
    star_abs_h = float(fixture.get("star_absence_home", 0.0))
    star_abs_a = float(fixture.get("star_absence_away", 0.0))
    inj_shock_h = float(fixture.get("fpl_injury_shock_home", 0.0))
    inj_shock_a = float(fixture.get("fpl_injury_shock_away", 0.0))
    red_h = int(fixture.get("red_last_home", 0))
    red_a = int(fixture.get("red_last_away", 0))

    p_injury = (
        -0.50 * (star_abs_h - star_abs_a)
        -0.30 * (inj_shock_h - inj_shock_a) * 5.0
        -0.20 * (red_h - red_a)
    )

    # Pillar 4: Underlying Shot-xG, Corner Dominance & Opponent Elo Schedule
    p_quality = (
        +0.40 * (xg_pH - b365_pH) * 4.0
        +0.35 * (sh["cor_ratio5"] - sa["cor_ratio5"])
        +0.25 * (sh["opp_elo5"] - sa["opp_elo5"]) / 150.0
    )

    # Pillar 5: Sharp Pinnacle vs Soft Bookmaker Divergence
    p_sharp_H = pin_pH - b365_pH
    p_sharp_D = pin_pD - b365_pD
    p_sharp_A = pin_pA - b365_pA

    # Pillar 6: Draw Equilibrium
    pi_diff = sh["pi_rating"] - sa["pi_rating"]
    p_draw = (
        +0.45 * (xg_pD - b365_pD) * 5.0
        +0.25 * ((m14_h + m14_a - 4.0) / 3.0)
        +0.30 * (0.50 - abs(pi_diff))
    )

    base_pH = 0.55 * pin_pH + 0.30 * b365_pH + 0.15 * xg_pH
    base_pD = 0.55 * pin_pD + 0.30 * b365_pD + 0.15 * xg_pD
    base_pA = 0.55 * pin_pA + 0.30 * b365_pA + 0.15 * xg_pA

    w = FORMULA_CONFIG["pillar_weights"]
    delta_dir = (
        w["w_luck"] * p_luck
        + w["w_fatigue"] * p_fatigue
        + w["w_injury"] * p_injury
        + w["w_quality"] * p_quality
    )
    draw_adj = w["w_draw"] * p_draw

    pH = float(np.clip(base_pH + delta_dir + w["w_sharp"] * p_sharp_H - 0.5 * draw_adj, 0.02, 0.94))
    pD = float(np.clip(base_pD + draw_adj + w["w_sharp"] * p_sharp_D, 0.04, 0.55))
    pA = float(np.clip(base_pA - delta_dir + w["w_sharp"] * p_sharp_A - 0.5 * draw_adj, 0.02, 0.94))
    tot = pH + pD + pA
    pH, pD, pA = pH / tot, pD / tot, pA / tot

    evH = pH * b365_H - 1.0
    evD = pD * b365_D - 1.0
    evA = pA * b365_A - 1.0

    th = FORMULA_CONFIG["thresholds"]
    candidates = []
    if th["odds_range_H"][0] <= b365_H <= th["odds_range_H"][1] and evH >= th["ev_threshold_H"]:
        candidates.append((evH, "H", b365_H, pH))
    if th["odds_range_D"][0] <= b365_D <= th["odds_range_D"][1] and evD >= th["ev_threshold_D"]:
        candidates.append((evD, "D", b365_D, pD))
    if th["odds_range_A"][0] <= b365_A <= th["odds_range_A"][1] and evA >= th["ev_threshold_A"]:
        candidates.append((evA, "A", b365_A, pA))

    reasons = []
    if abs(p_fatigue) >= 0.20:
        reasons.append("Mid-Week UCL/Europe Fatigue" if p_fatigue > 0 else "Home Mid-Week Europe Fatigue")
    if abs(p_luck) >= 0.20:
        reasons.append("xG Finishing Luck Mean-Reversion")
    if abs(p_injury) >= 0.15:
        reasons.append("Key Star Injury/Suspension Asymmetry")
    if max(abs(p_sharp_H), abs(p_sharp_A)) >= 0.008:
        reasons.append("Pinnacle Sharp Money Steam")

    if candidates:
        candidates.sort(reverse=True)
        best_ev, pick, odds, prob = candidates[0]
        return {
            "match": f"{h} vs {a}",
            "action": f"BET {pick} ({h if pick == 'H' else (a if pick == 'A' else 'Draw')})",
            "pick": pick,
            "odds": odds,
            "model_prob_pct": round(prob * 100.0, 1),
            "mkt_prob_pct": round((1.0 / odds) * 100.0, 1),
            "ev_pct": round(best_ev * 100.0, 2),
            "drivers": ", ".join(reasons) if reasons else "Multi-Pillar Composite Edge",
            "qualified": True,
        }
    else:
        in_range_evs = []
        if th["odds_range_H"][0] <= b365_H <= th["odds_range_H"][1]:
            in_range_evs.append(evH * 100.0)
        if th["odds_range_D"][0] <= b365_D <= th["odds_range_D"][1]:
            in_range_evs.append(evD * 100.0)
        if th["odds_range_A"][0] <= b365_A <= th["odds_range_A"][1]:
            in_range_evs.append(evA * 100.0)

        if not in_range_evs:
            pass_reason = f"Odds Guardrail Filter (Heavy Fav {b365_H:.2f} < 1.45 / Longshot {b365_A:.2f} > 4.44)"
            best_raw_ev = 0.0
        else:
            best_raw_ev = max(in_range_evs)
            pass_reason = "Market Efficiently Priced (Below +4.1% / +9.3% EV Threshold)"

        return {
            "match": f"{h} vs {a}",
            "action": "PASS (No Bet)",
            "pick": "PASS",
            "odds": 0.0,
            "model_prob_pct": round(pH * 100.0, 1),
            "mkt_prob_pct": round(b365_pH * 100.0, 1),
            "ev_pct": round(best_raw_ev, 2),
            "drivers": pass_reason,
            "qualified": False,
        }


def run_demo_gameweek_scan(bankroll: float = 180.0, total_deposited: float = 100.0, peak_profit: float = 80.0):
    states = load_latest_team_states()
    sample_slate = [
        {
            "home_team": "Brighton", "away_team": "Aston Villa",
            "b365_H": 2.15, "b365_D": 3.60, "b365_A": 3.25,
            "pin_H": 2.04, "pin_D": 3.65, "pin_A": 3.55,
            "midweek_eur_home": 0, "midweek_eur_away": 1, "midweek_ucl_away": 1,
            "matches_14d_home": 2, "matches_14d_away": 4,
            "rest_days_home": 7, "rest_days_away": 3,
            "star_absence_home": 0.0, "star_absence_away": 0.20,
        },
        {
            "home_team": "Brentford", "away_team": "Newcastle",
            "b365_H": 2.75, "b365_D": 3.50, "b365_A": 2.50,
            "pin_H": 2.58, "pin_D": 3.55, "pin_A": 2.72,
            "midweek_eur_home": 0, "midweek_eur_away": 1,
            "matches_14d_home": 2, "matches_14d_away": 4,
            "rest_days_home": 7, "rest_days_away": 3,
            "star_absence_home": 0.0, "star_absence_away": 0.40,
        },
        {
            "home_team": "Arsenal", "away_team": "Everton",
            "b365_H": 1.33, "b365_D": 5.25, "b365_A": 9.50,
            "pin_H": 1.34, "pin_D": 5.30, "pin_A": 9.40,
            "midweek_eur_home": 1, "midweek_eur_away": 0,
            "matches_14d_home": 3, "matches_14d_away": 2,
            "rest_days_home": 4, "rest_days_away": 7,
        },
        {
            "home_team": "Fulham", "away_team": "Wolves",
            "b365_H": 1.95, "b365_D": 3.50, "b365_A": 3.90,
            "pin_H": 1.96, "pin_D": 3.52, "pin_A": 3.95,
            "midweek_eur_home": 0, "midweek_eur_away": 0,
            "matches_14d_home": 2, "matches_14d_away": 2,
            "rest_days_home": 7, "rest_days_away": 7,
        },
        {
            "home_team": "Crystal Palace", "away_team": "Bournemouth",
            "b365_H": 2.40, "b365_D": 3.30, "b365_A": 3.00,
            "pin_H": 2.42, "pin_D": 3.22, "pin_A": 3.05,
            "midweek_eur_home": 0, "midweek_eur_away": 0,
            "matches_14d_home": 3, "matches_14d_away": 3,
            "rest_days_home": 4, "rest_days_away": 4,
        },
    ]

    print("==========================================================================================")
    print("  LIVE PREMIER LEAGUE GAMEWEEK SCANNER — v5.0 6-PILLAR ALPHA ENGINE")
    print("==========================================================================================")
    cur_profit = max(0.0, bankroll - total_deposited)
    vault_locked = 0.50 * max(peak_profit, cur_profit)
    reinvest_pool = max(0.0, cur_profit - vault_locked)
    unlocked_cash = max(10.0, bankroll - vault_locked)
    per_bet_stake = round(4.50 + 0.06 * reinvest_pool, 2)

    print(f"  Bankroll: ${bankroll:.2f} | Total Cash Put In: ${total_deposited:.2f} | Net Profit: +${cur_profit:.2f}")
    print(f"  Locked in 50% Safety Vault: ${vault_locked:.2f} | Active Unlocked Pot: ${unlocked_cash:.2f}")
    print(f"  Recommended Stake Per Qualified Bet: ${per_bet_stake:.2f} (Weekly Risk Cap: ${unlocked_cash * 0.30:.2f})")
    print("------------------------------------------------------------------------------------------")

    results = [evaluate_live_fixture(f, states) for f in sample_slate]
    for r in results:
        if r["qualified"]:
            print(
                f"  [ACTION: {r['action']:20s}] {r['match']:28s} | Odds: {r['odds']:.2f} | "
                f"Model: {r['model_prob_pct']:4.1f}% vs Mkt: {r['mkt_prob_pct']:4.1f}% | "
                f"EV: +{r['ev_pct']:5.2f}% | Stake: ${per_bet_stake:.2f} | Why: {r['drivers']}"
            )
        else:
            print(
                f"  [PASS  : {r['action']:20s}] {r['match']:28s} | Best EV: {r['ev_pct']:+5.2f}% | Why: {r['drivers']}"
            )
    print("==========================================================================================")


if __name__ == "__main__":
    run_demo_gameweek_scan()
