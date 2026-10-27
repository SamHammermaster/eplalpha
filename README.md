# Premier League 10-Year Quantitative Prediction Engine & Betting Formula (`2015-16` to `2025-26`)

A strictly walk-forward, zero-lookahead quantitative Premier League prediction engine and closed-form mathematical formula built on **14 seasons of English league football (`2012-13` through `2025-26`, 5,320 Premier League matches + 7,728 Championship warmup matches)**, **3,264 UEFA Champions League / Europa League / Conference League / FA Cup / EFL Cup team-dates**, and **8,015 Fantasy Premier League (FPL) pre-deadline squad availability & injury shock records**.

## Headline Backtest Results

The **v5.0 6-Pillar Alpha Formula** is net positive in **10 out of 10 seasons (`2016-17` to `2025-26`)** and **11 out of 11 seasons (`2015-16` to `2025-26`)** across **all four pre-match bookmaker benchmarks** under both **1u Flat Staking** and **Quarter-Kelly Staking**:

| Pre-Match Odds Benchmark | 10-Season Window (`2016-17` to `2025-26`) | 11-Season Window (`2015-16` to `2025-26`) | Flat ROI | Statistical Significance |
| :--- | :--- | :--- | :--- | :--- |
| **Bet365 (`B365H/D/A`)** | **10 / 10 seasons positive** (`832` bets, **+118.50u**) | **11 / 11 seasons positive** (`953` bets, **+134.83u**) | **+14.15%** | $t = +2.93$ ($p = 0.0017$) |
| **Market Consensus Average (`AvgH/D/A`)** | **10 / 10 seasons positive** (`807` bets, **+108.56u**) | **11 / 11 seasons positive** (`885` bets, **+122.80u**) | **+13.88%** | $t = +2.81$ ($p = 0.0025$) |
| **Pinnacle Sharp (`PSH/D/A`)** | **10 / 10 seasons positive** (`915` bets, **+114.21u**) | **11 / 11 seasons positive** (`1,034` bets, **+129.18u**) | **+12.49%** | $t = +2.76$ ($p = 0.0029$) |
| **Market Best Price (`MaxH/D/A`)** | **10 / 10 seasons positive** (`1,326` bets, **+156.30u**) | **11 / 11 seasons positive** (`1,495` bets, **+173.33u**) | **+11.59%** | $t = +3.12$ ($p = 0.0009$) |

## Running the Project Locally

### 1. Re-run the Python Data Pipeline & Walk-Forward Backtest Engine

```bash
pip install -r requirements.txt
python3 engine/data_pipeline.py
python3 engine/prediction_engine.py
python3 engine/export_dashboard_data.py
```

### 2. Run the Interactive Next.js Analytics Dashboard & Formula Simulator

```bash
npm install
npm run dev -- -p 43123
```

Open `http://127.0.0.1:43123` to explore the 10-year season-by-season backtest, interactive formula simulator, match-by-match bet ledger, and pre-match edge calculator.
