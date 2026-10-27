import os
import re
import glob
import math
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

CANONICAL_TEAMS = {
    "Arsenal": "Arsenal",
    "Arsenal FC": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Aston Villa FC": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "AFC Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brentford FC": "Brentford",
    "Brighton": "Brighton",
    "Brighton & Hove Albion": "Brighton",
    "Brighton and Hove Albion": "Brighton",
    "Brighton & Hove Albion FC": "Brighton",
    "Burnley": "Burnley",
    "Burnley FC": "Burnley",
    "Cardiff": "Cardiff",
    "Cardiff City": "Cardiff",
    "Cardiff City FC": "Cardiff",
    "Chelsea": "Chelsea",
    "Chelsea FC": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Crystal Palace FC": "Crystal Palace",
    "Everton": "Everton",
    "Everton FC": "Everton",
    "Fulham": "Fulham",
    "Fulham FC": "Fulham",
    "Huddersfield": "Huddersfield",
    "Huddersfield Town": "Huddersfield",
    "Huddersfield Town AFC": "Huddersfield",
    "Hull": "Hull",
    "Hull City": "Hull",
    "Hull City AFC": "Hull",
    "Ipswich": "Ipswich",
    "Ipswich Town": "Ipswich",
    "Ipswich Town FC": "Ipswich",
    "Leeds": "Leeds",
    "Leeds United": "Leeds",
    "Leeds United FC": "Leeds",
    "Leicester": "Leicester",
    "Leicester City": "Leicester",
    "Leicester City FC": "Leicester",
    "Liverpool": "Liverpool",
    "Liverpool FC": "Liverpool",
    "Luton": "Luton",
    "Luton Town": "Luton",
    "Luton Town FC": "Luton",
    "Man City": "Man City",
    "Manchester City": "Man City",
    "Manchester City FC": "Man City",
    "Man United": "Man United",
    "Man Utd": "Man United",
    "Manchester United": "Man United",
    "Manchester United FC": "Man United",
    "Middlesbrough": "Middlesbrough",
    "Middlesbrough FC": "Middlesbrough",
    "Newcastle": "Newcastle",
    "Newcastle United": "Newcastle",
    "Newcastle United FC": "Newcastle",
    "Norwich": "Norwich",
    "Norwich City": "Norwich",
    "Norwich City FC": "Norwich",
    "Nott'm Forest": "Nott'm Forest",
    "Nottingham Forest": "Nott'm Forest",
    "Nottingham Forest FC": "Nott'm Forest",
    "QPR": "QPR",
    "Queens Park Rangers": "QPR",
    "Queens Park Rangers FC": "QPR",
    "Reading": "Reading",
    "Reading FC": "Reading",
    "Sheffield United": "Sheffield United",
    "Sheffield Utd": "Sheffield United",
    "Sheffield United FC": "Sheffield United",
    "Southampton": "Southampton",
    "Southampton FC": "Southampton",
    "Stoke": "Stoke",
    "Stoke City": "Stoke",
    "Stoke City FC": "Stoke",
    "Sunderland": "Sunderland",
    "Sunderland AFC": "Sunderland",
    "Swansea": "Swansea",
    "Swansea City": "Swansea",
    "Swansea City AFC": "Swansea",
    "Tottenham": "Tottenham",
    "Spurs": "Tottenham",
    "Tottenham Hotspur": "Tottenham",
    "Tottenham Hotspur FC": "Tottenham",
    "Watford": "Watford",
    "Watford FC": "Watford",
    "West Brom": "West Brom",
    "West Bromwich Albion": "West Brom",
    "West Bromwich Albion FC": "West Brom",
    "West Ham": "West Ham",
    "West Ham United": "West Ham",
    "West Ham United FC": "West Ham",
    "Wigan": "Wigan",
    "Wigan Athletic": "Wigan",
    "Wigan Athletic FC": "Wigan",
    "Wolves": "Wolves",
    "Wolverhampton Wanderers": "Wolves",
    "Wolverhampton Wanderers FC": "Wolves",
}


def normalize_team_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    cleaned = re.sub(r"\s*\([A-Z]{3}\)\s*$", "", name.strip())
    cleaned = re.sub(r"^#\d+\s+", "", cleaned).strip()
    if cleaned in CANONICAL_TEAMS:
        return CANONICAL_TEAMS[cleaned]
    for suffix in [" FC", " AFC"]:
        if cleaned.endswith(suffix):
            base = cleaned[: -len(suffix)].strip()
            if base in CANONICAL_TEAMS:
                return CANONICAL_TEAMS[base]
    return cleaned


def parse_fd_date(date_str: str) -> datetime:
    s = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {date_str}")


def season_code_to_label(code: str) -> str:
    return f"20{code[:2]}-{code[2:]}"


def load_league_matches(raw_dir: str = "/workspace/data/raw") -> pd.DataFrame:
    frames = []
    for div, sub in [("E0", "epl"), ("E1", "championship")]:
        paths = sorted(glob.glob(os.path.join(raw_dir, sub, f"{div}_*.csv")))
        for p in paths:
            code = os.path.basename(p).split("_")[1].replace(".csv", "")
            season_label = season_code_to_label(code)
            df = pd.read_csv(p, encoding="latin1", low_memory=False)
            df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]).copy()
            df["date"] = df["Date"].apply(parse_fd_date)
            df["season"] = season_label
            df["season_code"] = code
            df["division"] = div
            df["home_team"] = df["HomeTeam"].apply(normalize_team_name)
            df["away_team"] = df["AwayTeam"].apply(normalize_team_name)
            df["fthg"] = pd.to_numeric(df["FTHG"], errors="coerce").fillna(0).astype(int)
            df["ftag"] = pd.to_numeric(df["FTAG"], errors="coerce").fillna(0).astype(int)
            df["ftr"] = df["FTR"].str.strip()
            for stat_col, out_col in [
                ("HS", "hs"), ("AS", "as_"),
                ("HST", "hst"), ("AST", "ast"),
                ("HC", "hc"), ("AC", "ac"),
                ("HF", "hf"), ("AF", "af"),
                ("HY", "hy"), ("AY", "ay"),
                ("HR", "hr"), ("AR", "ar"),
            ]:
                if stat_col in df.columns:
                    df[out_col] = pd.to_numeric(df[stat_col], errors="coerce").fillna(0.0)
                else:
                    df[out_col] = 0.0

            # Extract unified pre-match and closing odds
            for outcome in ["H", "D", "A"]:
                df[f"b365_{outcome}"] = pd.to_numeric(df.get(f"B365{outcome}"), errors="coerce")
                df[f"ps_{outcome}"] = pd.to_numeric(
                    df.get(f"PS{outcome}", df.get(f"P{outcome}")), errors="coerce"
                )
                df[f"wh_{outcome}"] = pd.to_numeric(df.get(f"WH{outcome}"), errors="coerce")
                df[f"bw_{outcome}"] = pd.to_numeric(df.get(f"BW{outcome}"), errors="coerce")
                max_col = f"Max{outcome}" if f"Max{outcome}" in df.columns else f"BbMx{outcome}"
                avg_col = f"Avg{outcome}" if f"Avg{outcome}" in df.columns else f"BbAv{outcome}"
                df[f"max_{outcome}"] = pd.to_numeric(df.get(max_col), errors="coerce")
                df[f"avg_{outcome}"] = pd.to_numeric(df.get(avg_col), errors="coerce")
                df[f"psc_{outcome}"] = pd.to_numeric(df.get(f"PSC{outcome}"), errors="coerce")
                df[f"b365c_{outcome}"] = pd.to_numeric(df.get(f"B365C{outcome}"), errors="coerce")

            # Over/Under 2.5 pre-match odds
            over_col = "Avg>2.5" if "Avg>2.5" in df.columns else ("BbAv>2.5" if "BbAv>2.5" in df.columns else "B365>2.5")
            under_col = "Avg<2.5" if "Avg<2.5" in df.columns else ("BbAv<2.5" if "BbAv<2.5" in df.columns else "B365<2.5")
            df["odds_over25"] = pd.to_numeric(df.get(over_col, df.get("B365>2.5")), errors="coerce")
            df["odds_under25"] = pd.to_numeric(df.get(under_col, df.get("B365<2.5")), errors="coerce")

            keep_cols = [
                "date", "season", "season_code", "division",
                "home_team", "away_team", "fthg", "ftag", "ftr",
                "hs", "as_", "hst", "ast", "hc", "ac", "hf", "af", "hy", "ay", "hr", "ar",
                "b365_H", "b365_D", "b365_A",
                "ps_H", "ps_D", "ps_A",
                "wh_H", "wh_D", "wh_A",
                "bw_H", "bw_D", "bw_A",
                "max_H", "max_D", "max_A",
                "avg_H", "avg_D", "avg_A",
                "psc_H", "psc_D", "psc_A",
                "b365c_H", "b365c_D", "b365c_A",
                "odds_over25", "odds_under25",
            ]
            frames.append(df[keep_cols])

    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.sort_values(["date", "division", "home_team"]).reset_index(drop=True)
    return all_df


def load_cup_and_europe_schedule(raw_dir: str = "/workspace/data/raw/cups") -> list:
    """
    Returns a list of (date, team_name, comp_type) records for English clubs
    across UCL, UEL, UECL, FA Cup, and EFL Cup.
    comp_type in {'UCL', 'EUROPE_OTHER', 'DOMESTIC_CUP'}
    """
    records = []

    # 1. engsoccerdata CSVs (champs.csv, facup.csv, leaguecup.csv)
    champs_path = os.path.join(raw_dir, "champs.csv")
    if os.path.exists(champs_path):
        cdf = pd.read_csv(champs_path, low_memory=False)
        cdf = cdf[cdf["Season"] >= 2012].dropna(subset=["Date", "home", "visitor"])
        for _, row in cdf.iterrows():
            try:
                dt = datetime.strptime(str(row["Date"]).strip(), "%Y-%m-%d")
            except ValueError:
                continue
            for side, ccol in [("home", "hcountry"), ("visitor", "vcountry")]:
                t = normalize_team_name(str(row[side]))
                if row.get(ccol) == "ENG" or t in CANONICAL_TEAMS.values():
                    records.append((dt, t, "UCL"))

    for fn in ["facup.csv", "leaguecup.csv"]:
        fpath = os.path.join(raw_dir, fn)
        if os.path.exists(fpath):
            cdf = pd.read_csv(fpath, low_memory=False)
            cdf = cdf[cdf["Season"] >= 2012].dropna(subset=["Date", "home", "visitor"])
            for _, row in cdf.iterrows():
                try:
                    dt = datetime.strptime(str(row["Date"]).strip(), "%Y-%m-%d")
                except ValueError:
                    continue
                for side in ["home", "visitor"]:
                    t = normalize_team_name(str(row[side]))
                    if t in CANONICAL_TEAMS.values():
                        records.append((dt, t, "DOMESTIC_CUP"))

    # 2. openfootball text files
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    date_re = re.compile(
        r"^(?:\[)?(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?(?:\])?"
    )

    for root_sub, default_comp in [
        ("openfootball_england", "DOMESTIC_CUP"),
        ("openfootball_europe", "EUROPE"),
    ]:
        pattern = os.path.join(raw_dir, root_sub, "*", "*.txt")
        for p in sorted(glob.glob(pattern)):
            season_folder = os.path.basename(os.path.dirname(p))
            start_year = int(season_folder.split("-")[0])
            fname = os.path.basename(p)
            if default_comp == "EUROPE":
                comp_type = "UCL" if fname.startswith("cl") else "EUROPE_OTHER"
            else:
                comp_type = "DOMESTIC_CUP"

            current_date = None
            with open(p, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or s.startswith("=") or s.startswith("▪"):
                        continue
                    m_date = date_re.match(s)
                    if m_date:
                        mon_str, day_str, yr_str = m_date.groups()
                        mon = month_map.get(mon_str)
                        day = int(day_str)
                        if yr_str:
                            yr = int(yr_str)
                        else:
                            yr = start_year if mon >= 7 else start_year + 1
                        try:
                            current_date = datetime(yr, mon, day)
                        except ValueError:
                            current_date = None
                        continue

                    if current_date and " v " in s and "[cancelled]" not in s:
                        # Remove leading time if present
                        s_notime = re.sub(r"^\d{1,2}[:.]\d{2}\s+", "", s)
                        parts = s_notime.split(" v ", 1)
                        if len(parts) == 2:
                            t1_raw = parts[0].strip()
                            # Second part has team2 followed by score or @
                            rest = parts[1].strip()
                            t2_raw = re.split(r"\s{2,}|\s+\d+-\d+|\s+@\s+", rest)[0].strip()
                            for traw in (t1_raw, t2_raw):
                                is_eng = "(ENG)" in traw
                                tnorm = normalize_team_name(traw)
                                if is_eng or tnorm in CANONICAL_TEAMS.values():
                                    records.append((current_date, tnorm, comp_type))

    # Deduplicate by (date, team, comp_type)
    dedup = sorted(set(records), key=lambda x: (x[0], x[1], x[2]))
    return dedup


def load_fpl_team_gameweeks(raw_dir: str = "/workspace/data/raw/fpl") -> dict:
    """
    Parses 10 seasons (2016-17 to 2025-26) of FPL merged_gw_{season}.csv.
    Computes strictly pre-match signals per (team, kickoff_date):
      - fpl_injury_shock: weighted transfer-out shock among the team's top-5 established stars
      - fpl_star_absence_prev: fraction of top-5 stars' minutes missing in the team's previous match
      - fpl_rolling_threat: rolling 5-match team Threat + Creativity
      - fpl_rolling_ict: rolling 5-match team ICT index
    """
    mt_path = os.path.join(raw_dir, "master_team_list.csv")
    mt_df = pd.read_csv(mt_path) if os.path.exists(mt_path) else pd.DataFrame()
    season_id_to_team = {}
    if not mt_df.empty:
        for _, r in mt_df.iterrows():
            season_id_to_team[(str(r["season"]), int(r["team"]))] = normalize_team_name(str(r["team_name"]))

    team_match_records = {}  # (season, team, date_str) -> dict of pre-match FPL features

    for s in [
        "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
        "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"
    ]:
        gw_path = os.path.join(raw_dir, f"merged_gw_{s}.csv")
        pr_path = os.path.join(raw_dir, f"players_raw_{s}.csv")
        if not os.path.exists(gw_path):
            continue

        elem_to_team = {}
        if os.path.exists(pr_path):
            pr = pd.read_csv(pr_path, low_memory=False)
            if "id" in pr.columns and "team" in pr.columns:
                for _, r in pr.iterrows():
                    tid = int(r["team"]) if pd.notna(r["team"]) else -1
                    tname = season_id_to_team.get((s, tid))
                    if tname:
                        elem_to_team[int(r["id"])] = tname

        df = pd.read_csv(gw_path, encoding="latin1", low_memory=False)
        if "team" in df.columns:
            df["team_norm"] = df["team"].apply(normalize_team_name)
        else:
            df["team_norm"] = df["element"].map(elem_to_team)
            # Fallback via fixture opponent inversion if any missing
            if df["team_norm"].isna().any() and "fixture" in df.columns and "opponent_team" in df.columns:
                df["opp_norm"] = df["opponent_team"].apply(
                    lambda x: season_id_to_team.get((s, int(x)), "") if pd.notna(x) else ""
                )
                fix_map = {}
                for (fix_id, was_h), grp in df.groupby(["fixture", "was_home"]):
                    opps = [o for o in grp["opp_norm"].unique() if o]
                    if opps:
                        fix_map[(fix_id, not bool(was_h))] = opps[0]
                mask = df["team_norm"].isna() | (df["team_norm"] == "")
                df.loc[mask, "team_norm"] = [
                    fix_map.get((f, bool(h)), "") for f, h in zip(df.loc[mask, "fixture"], df.loc[mask, "was_home"])
                ]

        df = df.dropna(subset=["team_norm", "kickoff_time"]).copy()
        df = df[df["team_norm"] != ""].copy()
        df["match_date"] = df["kickoff_time"].astype(str).str.slice(0, 10)
        for col in ["minutes", "ict_index", "threat", "creativity", "influence", "transfers_balance", "transfers_out", "selected", "total_points"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            else:
                df[col] = 0.0

        # Process each team's fixtures chronologically within the season
        for team, tdf in df.groupby("team_norm"):
            cum_player_ict = {}
            cum_player_mins = {}
            prev_top5_missing = 0.0
            hist_ict = []
            hist_threat_creat = []

            for mdate, mdf in tdf.groupby("match_date", sort=True):
                # Aggregate per player in case of duplicate rows
                pdf = mdf.groupby("element", as_index=False).agg({
                    "minutes": "sum",
                    "ict_index": "sum",
                    "threat": "sum",
                    "creativity": "sum",
                    "transfers_balance": "first",
                    "transfers_out": "first",
                    "selected": "first",
                })

                # Identify top 5 stars entering this match based on prior cumulative ICT
                if len(cum_player_ict) >= 5:
                    top5_elems = [
                        el for el, _ in sorted(cum_player_ict.items(), key=lambda x: x[1], reverse=True)[:5]
                    ]
                    top5_rows = pdf[pdf["element"].isin(top5_elems)]
                    # Pre-deadline transfer-out shock on top 5 stars (strictly known before gameweek deadline!)
                    shock_vals = []
                    for _, prow in top5_rows.iterrows():
                        sel = max(float(prow["selected"]), 5000.0)
                        net_out = max(0.0, -float(prow["transfers_balance"]))
                        shock_vals.append(min(1.0, net_out / sel))
                    injury_shock = float(np.mean(shock_vals)) if shock_vals else 0.0
                else:
                    top5_elems = []
                    injury_shock = 0.0

                avg_ict_5 = float(np.mean(hist_ict[-5:])) if hist_ict else 180.0
                avg_tc_5 = float(np.mean(hist_threat_creat[-5:])) if hist_threat_creat else 250.0

                team_match_records[(s, team, mdate)] = {
                    "fpl_injury_shock": injury_shock,
                    "fpl_star_absence_prev": prev_top5_missing,
                    "fpl_ict_5": avg_ict_5,
                    "fpl_tc_5": avg_tc_5,
                }

                # Now update post-match state for subsequent fixtures
                if top5_elems:
                    top5_rows = pdf[pdf["element"].isin(top5_elems)]
                    playing_top5 = sum(1 for _, r in top5_rows.iterrows() if r["minutes"] >= 45)
                    prev_top5_missing = max(0.0, (5.0 - playing_top5) / 5.0)
                else:
                    prev_top5_missing = 0.0

                for _, prow in pdf.iterrows():
                    el = int(prow["element"])
                    cum_player_ict[el] = cum_player_ict.get(el, 0.0) + float(prow["ict_index"])
                    cum_player_mins[el] = cum_player_mins.get(el, 0.0) + float(prow["minutes"])

                hist_ict.append(float(pdf["ict_index"].sum()))
                hist_threat_creat.append(float(pdf["threat"].sum() + pdf["creativity"].sum()))

    return team_match_records


def devig_power(odds_h: float, odds_d: float, odds_a: float):
    """
    Power method de-vigging (with multiplicative fallback) to obtain true market-implied probabilities.
    """
    if any(pd.isna(x) or x <= 1.0 for x in (odds_h, odds_d, odds_a)):
        return np.nan, np.nan, np.nan
    inv = np.array([1.0 / odds_h, 1.0 / odds_d, 1.0 / odds_a], dtype=float)
    overround = inv.sum()
    if overround <= 0:
        return np.nan, np.nan, np.nan
    # Solve sum(inv_i ^ k) = 1 via Newton-Raphson
    k = 1.0
    for _ in range(8):
        p = np.power(inv, k)
        f = p.sum() - 1.0
        if abs(f) < 1e-7:
            break
        df_dk = np.sum(p * np.log(np.clip(inv, 1e-9, 1.0)))
        if abs(df_dk) < 1e-9:
            break
        k = max(0.5, min(2.0, k - f / df_dk))
    p = np.power(inv, k)
    p = p / p.sum()
    return float(p[0]), float(p[1]), float(p[2])


def dixon_coles_probs(lam_h: float, lam_a: float, rho: float = -0.11, max_goals: int = 8):
    """
    Computes 1X2 and Over 2.5 probabilities under the Dixon-Coles (1997) bivariate Poisson scoreline model.
    """
    lam_h = max(0.25, min(4.5, float(lam_h)))
    lam_a = max(0.20, min(4.5, float(lam_a)))
    goals = np.arange(max_goals + 1)
    pmf_h = np.exp(-lam_h) * np.power(lam_h, goals) / np.array([math.factorial(int(g)) for g in goals])
    pmf_a = np.exp(-lam_a) * np.power(lam_a, goals) / np.array([math.factorial(int(g)) for g in goals])
    mat = np.outer(pmf_h, pmf_a)

    # Low-score dependency adjustment tau(x, y)
    mat[0, 0] *= max(0.0, 1.0 - lam_h * lam_a * rho)
    mat[0, 1] *= max(0.0, 1.0 + lam_h * rho)
    mat[1, 0] *= max(0.0, 1.0 + lam_a * rho)
    mat[1, 1] *= max(0.0, 1.0 - rho)

    total = mat.sum()
    if total > 0:
        mat /= total

    p_h = float(np.tril(mat, -1).sum())
    p_d = float(np.trace(mat))
    p_a = float(np.triu(mat, 1).sum())
    p_over25 = float(
        sum(mat[i, j] for i in range(max_goals + 1) for j in range(max_goals + 1) if (i + j) >= 3)
    )
    return p_h, p_d, p_a, p_over25


def build_feature_dataset() -> pd.DataFrame:
    print("Loading 14 seasons of EPL (E0) and Championship (E1) matches...")
    league_df = load_league_matches()
    print(f"Loaded {len(league_df)} total league matches.")

    print("Loading European (UCL/UEL/UECL) and Domestic Cup (FA/EFL Cup) schedules...")
    cup_records = load_cup_and_europe_schedule()
    print(f"Loaded {len(cup_records)} cup/European team-date appearances.")

    print("Loading 10 seasons of FPL gameweek squad/injury/ICT data...")
    fpl_records = load_fpl_team_gameweeks()
    print(f"Loaded {len(fpl_records)} FPL team-match records.")

    # Build per-team timeline of non-league matches for fast rest/midweek/lookahead lookup
    team_cup_dates = {}
    for dt, team, ctype in cup_records:
        team_cup_dates.setdefault(team, []).append((dt, ctype))

    # Walk-forward team state trackers
    elo = {}
    pi_home_rating = {}
    pi_away_rating = {}
    dc_att = {}
    dc_def = {}
    xg_att = {}
    xg_def = {}
    team_history = {}  # team -> list of past league match dicts
    last_league_date = {}
    h2h_history = {}   # (teamA, teamB) -> list of (date, home_team, fthg, ftag)

    current_season = None
    epl_rows = []

    for idx, row in league_df.iterrows():
        season = row["season"]
        div = row["division"]
        dt = row["date"]
        h = row["home_team"]
        a = row["away_team"]

        # Season transition: regress Elo, Pi, and Attack/Defense ratings slightly toward division prior
        if season != current_season:
            if current_season is not None:
                # Identify teams in E0 vs E1 this season
                e0_teams_season = set(
                    league_df[(league_df["season"] == season) & (league_df["division"] == "E0")]["home_team"].unique()
                )
                for t in list(elo.keys()):
                    target_elo = 1520.0 if t in e0_teams_season else 1360.0
                    elo[t] = 0.80 * elo[t] + 0.20 * target_elo
                    pi_home_rating[t] = 0.82 * pi_home_rating.get(t, 0.0)
                    pi_away_rating[t] = 0.82 * pi_away_rating.get(t, 0.0)
                    dc_att[t] = 0.78 * dc_att.get(t, 1.0) + 0.22 * 1.0
                    dc_def[t] = 0.78 * dc_def.get(t, 1.0) + 0.22 * 1.0
                    xg_att[t] = 0.78 * xg_att.get(t, 1.0) + 0.22 * 1.0
                    xg_def[t] = 0.78 * xg_def.get(t, 1.0) + 0.22 * 1.0
            current_season = season

        # Initialize unseen teams based on division
        for t in (h, a):
            if t not in elo:
                elo[t] = 1500.0 if div == "E0" else 1350.0
                pi_home_rating[t] = 0.0 if div == "E0" else -0.25
                pi_away_rating[t] = 0.0 if div == "E0" else -0.25
                dc_att[t] = 1.0 if div == "E0" else 0.82
                dc_def[t] = 1.0 if div == "E0" else 1.18
                xg_att[t] = 1.0 if div == "E0" else 0.82
                xg_def[t] = 1.0 if div == "E0" else 1.18
                team_history[t] = []

        # Pre-match Elo & expected scores
        eh = elo[h]
        ea = elo[a]
        elo_diff = eh - ea
        elo_home_adv = 58.0
        exp_h_elo = 1.0 / (1.0 + 10.0 ** (-(elo_diff + elo_home_adv) / 400.0))

        # Pre-match Pi-ratings
        pih = pi_home_rating[h]
        pia = pi_away_rating[a]
        pi_diff = pih - pia

        # Pre-match Dixon-Coles & Shot-xG Poisson expectations
        base_home_goals = 1.52
        base_away_goals = 1.24
        lam_dc_h = base_home_goals * dc_att[h] * dc_def[a] * (10.0 ** (elo_diff / 1800.0))
        lam_dc_a = base_away_goals * dc_att[a] * dc_def[h] * (10.0 ** (-elo_diff / 1800.0))
        dc_pH, dc_pD, dc_pA, dc_pO25 = dixon_coles_probs(lam_dc_h, lam_dc_a, rho=-0.11)

        lam_xg_h = base_home_goals * xg_att[h] * xg_def[a] * (10.0 ** (elo_diff / 1800.0))
        lam_xg_a = base_away_goals * xg_att[a] * xg_def[h] * (10.0 ** (-elo_diff / 1800.0))
        xg_pH, xg_pD, xg_pA, xg_pO25 = dixon_coles_probs(lam_xg_h, lam_xg_a, rho=-0.11)

        # If this is an EPL (E0) match, compute full pre-match feature vector
        if div == "E0":
            def get_rolling_stats(t: str, is_home_Context: bool):
                hist = team_history[t]
                # Season-to-date matches in current season
                cur_s_hist = [m for m in hist if m["season"] == season]
                last3 = hist[-3:]
                last5 = hist[-5:]
                last10 = hist[-10:]
                venue_hist = [m for m in hist if m["was_home"] == is_home_Context][-5:]

                ppg_3 = float(np.mean([m["pts"] for m in last3])) if last3 else 1.35
                ppg_5 = float(np.mean([m["pts"] for m in last5])) if last5 else 1.35
                ppg_10 = float(np.mean([m["pts"] for m in last10])) if last10 else 1.35
                venue_ppg_5 = float(np.mean([m["pts"] for m in venue_hist])) if venue_hist else ppg_5

                # Opponent-adjusted form (actual points minus Elo-expected points over last 5 & 10)
                opp_adj_5 = float(np.mean([m["pts"] - m["exp_pts"] for m in last5])) if last5 else 0.0
                opp_adj_10 = float(np.mean([m["pts"] - m["exp_pts"] for m in last10])) if last10 else 0.0
                avg_opp_elo_5 = float(np.mean([m["opp_elo"] for m in last5])) if last5 else 1500.0

                # Goal diff & Shot-xG diff
                gd_5 = float(np.mean([m["gf"] - m["ga"] for m in last5])) if last5 else 0.0
                xgd_5 = float(np.mean([m["xgf"] - m["xga"] for m in last5])) if last5 else 0.0
                xgd_10 = float(np.mean([m["xgf"] - m["xga"] for m in last10])) if last10 else 0.0

                # Shot-on-target dominance & corner dominance
                sot_ratio_5 = float(np.mean([m["sot_for"] / max(1.0, m["sot_for"] + m["sot_against"]) for m in last5])) if last5 else 0.5
                cor_ratio_5 = float(np.mean([m["cor_for"] / max(1.0, m["cor_for"] + m["cor_against"]) for m in last5])) if last5 else 0.5

                # Finishing overperformance (Goals Scored - Shot xG): positive = running hot/lucky, negative = due for positive regression
                finishing_luck_5 = float(np.mean([m["gf"] - m["xgf"] for m in last5])) if last5 else 0.0
                finishing_luck_10 = float(np.mean([m["gf"] - m["xgf"] for m in last10])) if last10 else 0.0
                def_luck_5 = float(np.mean([m["xga"] - m["ga"] for m in last5])) if last5 else 0.0
                points_luck_5 = float(np.mean([m["pts"] - m["xg_pts"] for m in last5])) if last5 else 0.0

                # Draw propensity
                draw_rate_10 = float(np.mean([1.0 if m["pts"] == 1 else 0.0 for m in last10])) if len(last10) >= 4 else 0.25

                # Red card in previous match (suspension carryover)
                red_last = 1 if (hist and hist[-1]["red_for"] > 0) else 0

                # Promoted team indicator (played in E1 in previous match/season)
                promoted = 1 if (any(m["div"] == "E1" for m in hist[-15:]) and len(cur_s_hist) <= 12) else 0

                # Rest days, midweek UCL / Europe / Cup congestion, and lookahead Europe
                prev_league_dt = last_league_date.get(t)
                cup_list = team_cup_dates.get(t, [])
                recent_cups = [(cdt, ctype) for (cdt, ctype) in cup_list if timedelta(days=0) < (dt - cdt) <= timedelta(days=21)]
                upcoming_cups = [(cdt, ctype) for (cdt, ctype) in cup_list if timedelta(days=0) < (cdt - dt) <= timedelta(days=5)]

                all_prev_dates = ([prev_league_dt] if prev_league_dt else []) + [cdt for cdt, _ in recent_cups]
                if all_prev_dates:
                    most_recent_dt = max(all_prev_dates)
                    rest_days = float(min(14, max(1, (dt - most_recent_dt).days)))
                else:
                    rest_days = 7.0

                midweek_ucl = 1 if any(ctype == "UCL" and (dt - cdt).days <= 5 for cdt, ctype in recent_cups) else 0
                midweek_eur = 1 if any(ctype in ("UCL", "EUROPE_OTHER") and (dt - cdt).days <= 5 for cdt, ctype in recent_cups) else 0
                midweek_cup = 1 if any(ctype == "DOMESTIC_CUP" and (dt - cdt).days <= 5 for cdt, ctype in recent_cups) else 0
                lookahead_ucl = 1 if any(ctype == "UCL" and (cdt - dt).days <= 4 for cdt, ctype in upcoming_cups) else 0
                lookahead_eur = 1 if any(ctype in ("UCL", "EUROPE_OTHER") and (cdt - dt).days <= 4 for cdt, ctype in upcoming_cups) else 0

                league_14d = sum(1 for m in hist[-5:] if 0 < (dt - m["date"]).days <= 14)
                cups_14d = sum(1 for cdt, _ in recent_cups if 0 < (dt - cdt).days <= 14)
                matches_14d = league_14d + cups_14d

                return {
                    "matchweek": len(cur_s_hist) + 1,
                    "ppg_3": ppg_3,
                    "ppg_5": ppg_5,
                    "ppg_10": ppg_10,
                    "venue_ppg_5": venue_ppg_5,
                    "opp_adj_5": opp_adj_5,
                    "opp_adj_10": opp_adj_10,
                    "avg_opp_elo_5": avg_opp_elo_5,
                    "gd_5": gd_5,
                    "xgd_5": xgd_5,
                    "xgd_10": xgd_10,
                    "sot_ratio_5": sot_ratio_5,
                    "cor_ratio_5": cor_ratio_5,
                    "finishing_luck_5": finishing_luck_5,
                    "finishing_luck_10": finishing_luck_10,
                    "def_luck_5": def_luck_5,
                    "points_luck_5": points_luck_5,
                    "draw_rate_10": draw_rate_10,
                    "red_last": red_last,
                    "promoted": promoted,
                    "rest_days": rest_days,
                    "midweek_ucl": midweek_ucl,
                    "midweek_eur": midweek_eur,
                    "midweek_cup": midweek_cup,
                    "lookahead_ucl": lookahead_ucl,
                    "lookahead_eur": lookahead_eur,
                    "matches_14d": matches_14d,
                }

            sh = get_rolling_stats(h, True)
            sa = get_rolling_stats(a, False)

            # H2H history over last 6 meetings
            pair_key = tuple(sorted([h, a]))
            past_h2h = h2h_history.get(pair_key, [])[-6:]
            if past_h2h:
                h2h_pts = []
                for _, h_team, hg, ag in past_h2h:
                    if hg == ag:
                        h2h_pts.append(1.0)
                    elif (h_team == h and hg > ag) or (h_team == a and ag > hg):
                        h2h_pts.append(3.0)
                    else:
                        h2h_pts.append(0.0)
                h2h_home_ppg = float(np.mean(h2h_pts))
            else:
                h2h_home_ppg = 1.45

            # FPL injury/news/ICT signals
            d_str = dt.strftime("%Y-%m-%d")
            fpl_h = fpl_records.get((season, h, d_str), {})
            fpl_a = fpl_records.get((season, a, d_str), {})

            # De-vigged pre-match probabilities
            pin_pH, pin_pD, pin_pA = devig_power(row["ps_H"], row["ps_D"], row["ps_A"])
            b365_pH, b365_pD, b365_pA = devig_power(row["b365_H"], row["b365_D"], row["b365_A"])
            avg_pH, avg_pD, avg_pA = devig_power(row["avg_H"], row["avg_D"], row["avg_A"])
            pinc_pH, pinc_pD, pinc_pA = devig_power(row["psc_H"], row["psc_D"], row["psc_A"])

            # Fallback if Pinnacle opening is missing on a handful of matches
            if pd.isna(pin_pH):
                pin_pH, pin_pD, pin_pA = avg_pH, avg_pD, avg_pA
            if pd.isna(avg_pH):
                avg_pH, avg_pD, avg_pA = b365_pH, b365_pD, b365_pA

            epl_rows.append({
                "date": d_str,
                "season": season,
                "matchweek": max(sh["matchweek"], sa["matchweek"]),
                "home_team": h,
                "away_team": a,
                "fthg": int(row["fthg"]),
                "ftag": int(row["ftag"]),
                "ftr": row["ftr"],
                "hs": float(row["hs"]),
                "as": float(row["as_"]),
                "hst": float(row["hst"]),
                "ast": float(row["ast"]),
                "hc": float(row["hc"]),
                "ac": float(row["ac"]),
                # Ratings
                "elo_home": eh,
                "elo_away": ea,
                "elo_diff": elo_diff,
                "elo_exp_home": exp_h_elo,
                "pi_home": pih,
                "pi_away": pia,
                "pi_diff": pi_diff,
                "dc_att_home": dc_att[h],
                "dc_def_home": dc_def[h],
                "dc_att_away": dc_att[a],
                "dc_def_away": dc_def[a],
                "dc_lam_home": lam_dc_h,
                "dc_lam_away": lam_dc_a,
                "dc_prob_H": dc_pH,
                "dc_prob_D": dc_pD,
                "dc_prob_A": dc_pA,
                "dc_prob_O25": dc_pO25,
                "xg_lam_home": lam_xg_h,
                "xg_lam_away": lam_xg_a,
                "xg_prob_H": xg_pH,
                "xg_prob_D": xg_pD,
                "xg_prob_A": xg_pA,
                "xg_prob_O25": xg_pO25,
                # Form & Opposing Strength
                "ppg3_home": sh["ppg_3"],
                "ppg3_away": sa["ppg_3"],
                "ppg5_home": sh["ppg_5"],
                "ppg5_away": sa["ppg_5"],
                "ppg10_home": sh["ppg_10"],
                "ppg10_away": sa["ppg_10"],
                "venue_ppg5_home": sh["venue_ppg_5"],
                "venue_ppg5_away": sa["venue_ppg_5"],
                "opp_adj5_home": sh["opp_adj_5"],
                "opp_adj5_away": sa["opp_adj_5"],
                "opp_adj10_home": sh["opp_adj_10"],
                "opp_adj10_away": sa["opp_adj_10"],
                "opp_elo5_home": sh["avg_opp_elo_5"],
                "opp_elo5_away": sa["avg_opp_elo_5"],
                "gd5_home": sh["gd_5"],
                "gd5_away": sa["gd_5"],
                "xgd5_home": sh["xgd_5"],
                "xgd5_away": sa["xgd_5"],
                "xgd10_home": sh["xgd_10"],
                "xgd10_away": sa["xgd_10"],
                "sot_ratio5_home": sh["sot_ratio_5"],
                "sot_ratio5_away": sa["sot_ratio_5"],
                "cor_ratio5_home": sh["cor_ratio_5"],
                "cor_ratio5_away": sa["cor_ratio_5"],
                "finishing_luck5_home": sh["finishing_luck_5"],
                "finishing_luck5_away": sa["finishing_luck_5"],
                "finishing_luck10_home": sh["finishing_luck_10"],
                "finishing_luck10_away": sa["finishing_luck_10"],
                "def_luck5_home": sh["def_luck_5"],
                "def_luck5_away": sa["def_luck_5"],
                "points_luck5_home": sh["points_luck_5"],
                "points_luck5_away": sa["points_luck_5"],
                "draw_rate10_home": sh["draw_rate_10"],
                "draw_rate10_away": sa["draw_rate_10"],
                "h2h_home_ppg": h2h_home_ppg,
                # Injuries, Suspensions, Promoted, Midweek Europe/Cup & Fatigue
                "red_last_home": sh["red_last"],
                "red_last_away": sa["red_last"],
                "promoted_home": sh["promoted"],
                "promoted_away": sa["promoted"],
                "rest_days_home": sh["rest_days"],
                "rest_days_away": sa["rest_days"],
                "rest_diff": sh["rest_days"] - sa["rest_days"],
                "midweek_ucl_home": sh["midweek_ucl"],
                "midweek_ucl_away": sa["midweek_ucl"],
                "midweek_eur_home": sh["midweek_eur"],
                "midweek_eur_away": sa["midweek_eur"],
                "midweek_cup_home": sh["midweek_cup"],
                "midweek_cup_away": sa["midweek_cup"],
                "lookahead_ucl_home": sh["lookahead_ucl"],
                "lookahead_ucl_away": sa["lookahead_ucl"],
                "lookahead_eur_home": sh["lookahead_eur"],
                "lookahead_eur_away": sa["lookahead_eur"],
                "matches_14d_home": sh["matches_14d"],
                "matches_14d_away": sa["matches_14d"],
                "fpl_injury_shock_home": fpl_h.get("fpl_injury_shock", 0.0),
                "fpl_injury_shock_away": fpl_a.get("fpl_injury_shock", 0.0),
                "fpl_star_absence_home": fpl_h.get("fpl_star_absence_prev", 0.0),
                "fpl_star_absence_away": fpl_a.get("fpl_star_absence_prev", 0.0),
                "fpl_ict5_home": fpl_h.get("fpl_ict_5", 180.0),
                "fpl_ict5_away": fpl_a.get("fpl_ict_5", 180.0),
                "fpl_tc5_home": fpl_h.get("fpl_tc_5", 250.0),
                "fpl_tc5_away": fpl_a.get("fpl_tc_5", 250.0),
                # Pre-match Bookmaker Odds
                "b365_H": float(row["b365_H"]) if pd.notna(row["b365_H"]) else np.nan,
                "b365_D": float(row["b365_D"]) if pd.notna(row["b365_D"]) else np.nan,
                "b365_A": float(row["b365_A"]) if pd.notna(row["b365_A"]) else np.nan,
                "ps_H": float(row["ps_H"]) if pd.notna(row["ps_H"]) else np.nan,
                "ps_D": float(row["ps_D"]) if pd.notna(row["ps_D"]) else np.nan,
                "ps_A": float(row["ps_A"]) if pd.notna(row["ps_A"]) else np.nan,
                "avg_H": float(row["avg_H"]) if pd.notna(row["avg_H"]) else np.nan,
                "avg_D": float(row["avg_D"]) if pd.notna(row["avg_D"]) else np.nan,
                "avg_A": float(row["avg_A"]) if pd.notna(row["avg_A"]) else np.nan,
                "max_H": float(row["max_H"]) if pd.notna(row["max_H"]) else np.nan,
                "max_D": float(row["max_D"]) if pd.notna(row["max_D"]) else np.nan,
                "max_A": float(row["max_A"]) if pd.notna(row["max_A"]) else np.nan,
                "psc_H": float(row["psc_H"]) if pd.notna(row["psc_H"]) else np.nan,
                "psc_D": float(row["psc_D"]) if pd.notna(row["psc_D"]) else np.nan,
                "psc_A": float(row["psc_A"]) if pd.notna(row["psc_A"]) else np.nan,
                "odds_over25": float(row["odds_over25"]) if pd.notna(row["odds_over25"]) else np.nan,
                "odds_under25": float(row["odds_under25"]) if pd.notna(row["odds_under25"]) else np.nan,
                # De-vigged market probabilities
                "pin_prob_H": pin_pH,
                "pin_prob_D": pin_pD,
                "pin_prob_A": pin_pA,
                "b365_prob_H": b365_pH,
                "b365_prob_D": b365_pD,
                "b365_prob_A": b365_pA,
                "avg_prob_H": avg_pH,
                "avg_prob_D": avg_pD,
                "avg_prob_A": avg_pA,
                "pinc_prob_H": pinc_pH,
                "pinc_prob_D": pinc_pD,
                "pinc_prob_A": pinc_pA,
            })

        # === POST-MATCH STATE UPDATES (Strictly after pre-match prediction features are recorded!) ===
        hg = int(row["fthg"])
        ag = int(row["ftag"])
        actual_h = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
        gd = abs(hg - ag)
        k_factor = 22.0 * (1.0 + 0.55 * math.log(gd + 1))
        elo_delta = k_factor * (actual_h - exp_h_elo)
        elo[h] += elo_delta
        elo[a] -= elo_delta

        # Update Pi-ratings (Constantinou & Fenton venue-specific ratings)
        exp_gd = (pih - pia) + 0.28
        err_gd = (hg - ag) - exp_gd
        pi_step = 0.055 * math.copysign(math.log1p(abs(err_gd)), err_gd)
        pi_home_rating[h] += pi_step
        pi_away_rating[a] -= pi_step * 0.85
        # Cross-venue spillover
        pi_away_rating[h] += pi_step * 0.30
        pi_home_rating[a] -= pi_step * 0.30

        # Shot-based xG proxy for this match
        # Calibration on EPL shots: SoT ~ 0.31 xG, off-target shot ~ 0.045 xG
        hst_val = float(row["hst"])
        ast_val = float(row["ast"])
        hs_val = max(hst_val, float(row["hs"]))
        as_val = max(ast_val, float(row["as_"]))
        if hs_val > 0 or as_val > 0:
            xg_h = 0.30 * hst_val + 0.045 * (hs_val - hst_val) + 0.12
            xg_a = 0.30 * ast_val + 0.045 * (as_val - ast_val) + 0.10
        else:
            xg_h = float(hg)
            xg_a = float(ag)

        # Update Dixon-Coles and Shot-xG attack/defense multipliers
        alpha_dc = 0.065
        exp_h_raw = max(0.4, base_home_goals * dc_att[h] * dc_def[a])
        exp_a_raw = max(0.4, base_away_goals * dc_att[a] * dc_def[h])
        dc_att[h] = max(0.45, min(2.2, (1.0 - alpha_dc) * dc_att[h] + alpha_dc * (hg / max(0.5, base_home_goals * dc_def[a]))))
        dc_def[a] = max(0.45, min(2.2, (1.0 - alpha_dc) * dc_def[a] + alpha_dc * (hg / max(0.5, base_home_goals * dc_att[h]))))
        dc_att[a] = max(0.45, min(2.2, (1.0 - alpha_dc) * dc_att[a] + alpha_dc * (ag / max(0.5, base_away_goals * dc_def[h]))))
        dc_def[h] = max(0.45, min(2.2, (1.0 - alpha_dc) * dc_def[h] + alpha_dc * (ag / max(0.5, base_away_goals * dc_att[a]))))

        alpha_xg = 0.085
        xg_att[h] = max(0.45, min(2.2, (1.0 - alpha_xg) * xg_att[h] + alpha_xg * (xg_h / max(0.5, base_home_goals * xg_def[a]))))
        xg_def[a] = max(0.45, min(2.2, (1.0 - alpha_xg) * xg_def[a] + alpha_xg * (xg_h / max(0.5, base_home_goals * xg_att[h]))))
        xg_att[a] = max(0.45, min(2.2, (1.0 - alpha_xg) * xg_att[a] + alpha_xg * (xg_a / max(0.5, base_away_goals * xg_def[h]))))
        xg_def[h] = max(0.45, min(2.2, (1.0 - alpha_xg) * xg_def[h] + alpha_xg * (xg_a / max(0.5, base_away_goals * xg_att[a]))))

        # Expected points from Elo & from xG
        exp_pts_h = 2.75 * exp_h_elo + 0.25 * (1.0 - abs(2.0 * exp_h_elo - 1.0))
        exp_pts_a = 2.75 * (1.0 - exp_h_elo) + 0.25 * (1.0 - abs(2.0 * exp_h_elo - 1.0))
        xg_p_h, xg_p_d, xg_p_a, _ = dixon_coles_probs(xg_h, xg_a, rho=-0.10)
        xg_pts_h = 3.0 * xg_p_h + 1.0 * xg_p_d
        xg_pts_a = 3.0 * xg_p_a + 1.0 * xg_p_d

        pts_h = 3.0 if hg > ag else (1.0 if hg == ag else 0.0)
        pts_a = 3.0 if ag > hg else (1.0 if hg == ag else 0.0)

        team_history[h].append({
            "date": dt,
            "season": season,
            "div": div,
            "was_home": True,
            "gf": float(hg),
            "ga": float(ag),
            "xgf": xg_h,
            "xga": xg_a,
            "pts": pts_h,
            "exp_pts": exp_pts_h,
            "xg_pts": xg_pts_h,
            "opp_elo": ea,
            "sot_for": hst_val,
            "sot_against": ast_val,
            "cor_for": float(row["hc"]),
            "cor_against": float(row["ac"]),
            "red_for": int(row["hr"]),
        })
        team_history[a].append({
            "date": dt,
            "season": season,
            "div": div,
            "was_home": False,
            "gf": float(ag),
            "ga": float(hg),
            "xgf": xg_a,
            "xga": xg_h,
            "pts": pts_a,
            "exp_pts": exp_pts_a,
            "xg_pts": xg_pts_a,
            "opp_elo": eh,
            "sot_for": ast_val,
            "sot_against": hst_val,
            "cor_for": float(row["ac"]),
            "cor_against": float(row["hc"]),
            "red_for": int(row["ar"]),
        })
        last_league_date[h] = dt
        last_league_date[a] = dt

        pair_key = tuple(sorted([h, a]))
        h2h_history.setdefault(pair_key, []).append((dt, h, hg, ag))

    out_df = pd.DataFrame(epl_rows)
    os.makedirs("/workspace/data/processed", exist_ok=True)
    out_path = "/workspace/data/processed/epl_features_all.csv"
    out_df.to_csv(out_path, index=False)
    print(f"Saved {len(out_df)} EPL match feature records to {out_path}")
    return out_df


if __name__ == "__main__":
    df = build_feature_dataset()
    print(df.groupby("season").size())
