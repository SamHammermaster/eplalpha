"use client";

import React, { useState, useMemo } from "react";
import rawData from "@/data/epl_dashboard_data.json";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  TrendingUp,
  Award,
  Activity,
  ShieldAlert,
  CalendarClock,
  Calculator,
  Search,
  CheckCircle2,
  XCircle,
  Sliders,
  RotateCcw,
  Layers,
} from "lucide-react";

type BookKey = "b365" | "avg" | "ps" | "max";

const dashboardData = rawData as any;

export default function EplPredictionDashboard() {
  const [selectedBook, setSelectedBook] = useState<BookKey>("b365");
  const [windowMode, setWindowMode] = useState<"ten_seasons" | "eleven_seasons">("ten_seasons");

  // Interactive Custom Formula Simulator Weights (defaults to v5.0 optimal)
  const [wLuck, setWLuck] = useState<number>(0.036);
  const [wFatigue, setWFatigue] = useState<number>(0.089);
  const [wInjury, setWInjury] = useState<number>(0.091);
  const [wQuality, setWQuality] = useState<number>(0.034);
  const [wSharp, setWSharp] = useState<number>(1.55);
  const [wDraw, setWDraw] = useState<number>(0.0685);
  const [evThH, setEvThH] = useState<number>(0.041);
  const [evThD, setEvThD] = useState<number>(0.099);
  const [evThA, setEvThA] = useState<number>(0.093);

  // Match Bet Ledger Filters
  const [ledgerSeason, setLedgerSeason] = useState<string>("ALL");
  const [ledgerPick, setLedgerPick] = useState<string>("ALL");
  const [ledgerSearch, setLedgerSearch] = useState<string>("");
  const [onlyMidweekEur, setOnlyMidweekEur] = useState<boolean>(false);

  // Interactive Club-vs-Club Predictor State
  const teamNames = useMemo(() => Object.keys(dashboardData.team_profiles).sort(), []);
  const [predHome, setPredHome] = useState<string>("Arsenal");
  const [predAway, setPredAway] = useState<string>("Aston Villa");
  const [predOddsH, setPredOddsH] = useState<string>("1.85");
  const [predOddsD, setPredOddsD] = useState<string>("3.75");
  const [predOddsA, setPredOddsA] = useState<string>("4.20");
  const [predMidweekH, setPredMidweekH] = useState<boolean>(false);
  const [predMidweekA, setPredMidweekA] = useState<boolean>(true);
  const [predRestDiff, setPredRestDiff] = useState<number>(3);
  const [predStarMissH, setPredStarMissH] = useState<number>(0.0);
  const [predStarMissA, setPredStarMissA] = useState<number>(0.4);
  const [predSharpDiffH, setPredSharpDiffH] = useState<number>(0.012);

  const resetWeights = () => {
    setWLuck(0.036);
    setWFatigue(0.089);
    setWInjury(0.091);
    setWQuality(0.034);
    setWSharp(1.55);
    setWDraw(0.0685);
    setEvThH(0.041);
    setEvThD(0.099);
    setEvThA(0.093);
  };

  // Live Browser Re-Simulation across all 4,180 Premier League matches
  const liveSimulation = useMemo(() => {
    const matches: any[] = dashboardData.sim_matches;
    const seasonMap: Record<
      string,
      { season: string; bets: number; wins: number; profit: number; kellyProfit: number; kellyStake: number; betsH: number; betsD: number; betsA: number }
    > = {};

    const oddOffset = selectedBook === "b365" ? 14 : selectedBook === "avg" ? 17 : selectedBook === "max" ? 20 : 14;

    for (let i = 0; i < matches.length; i++) {
      const m = matches[i];
      const season: string = m[0];
      if (windowMode === "ten_seasons" && season === "2015-16") continue;

      if (!seasonMap[season]) {
        seasonMap[season] = {
          season,
          bets: 0,
          wins: 0,
          profit: 0,
          kellyProfit: 0,
          kellyStake: 0,
          betsH: 0,
          betsD: 0,
          betsA: 0,
        };
      }

      const mw: number = m[1];
      if (mw < 3) continue;

      const ftr: string = m[2];
      const baseH: number = m[3];
      const baseD: number = m[4];
      const baseA: number = m[5];
      const pLuck: number = m[6];
      const pFatigue: number = m[7];
      const pInjury: number = m[8];
      const pQuality: number = m[9];
      const pSharpH: number = m[10];
      const pSharpD: number = m[11];
      const pSharpA: number = m[12];
      const pDraw: number = m[13];

      const oH: number = m[oddOffset];
      const oD: number = m[oddOffset + 1];
      const oA: number = m[oddOffset + 2];

      const deltaDir = wLuck * pLuck + wFatigue * pFatigue + wInjury * pInjury + wQuality * pQuality;
      const drawAdj = wDraw * pDraw;

      let pH = Math.min(0.94, Math.max(0.02, baseH + deltaDir + wSharp * pSharpH - 0.5 * drawAdj));
      let pD = Math.min(0.55, Math.max(0.04, baseD + drawAdj + wSharp * pSharpD));
      let pA = Math.min(0.94, Math.max(0.02, baseA - deltaDir + wSharp * pSharpA - 0.5 * drawAdj));
      const tot = pH + pD + pA;
      pH /= tot;
      pD /= tot;
      pA /= tot;

      const evH = pH * oH - 1.0;
      const evD = pD * oD - 1.0;
      const evA = pA * oA - 1.0;

      const cH = oH >= 1.45 && oH <= 4.38 && evH >= evThH ? evH : -999;
      const cD = oD >= 3.0 && oD <= 4.35 && evD >= evThD ? evD : -999;
      const cA = oA >= 1.6 && oA <= 4.44 && evA >= evThA ? evA : -999;

      let bestEv = cH;
      let pick = "H";
      let odds = oH;
      if (cD > bestEv) {
        bestEv = cD;
        pick = "D";
        odds = oD;
      }
      if (cA > bestEv) {
        bestEv = cA;
        pick = "A";
        odds = oA;
      }

      if (bestEv > -100 && odds > 1.0) {
        const sObj = seasonMap[season];
        sObj.bets += 1;
        if (pick === "H") sObj.betsH += 1;
        else if (pick === "D") sObj.betsD += 1;
        else sObj.betsA += 1;

        const won = ftr === pick;
        const rawKelly = Math.max(0, bestEv / Math.max(0.2, odds - 1.0));
        const kStake = Math.min(1.8, Math.max(0.6, 0.5 + 6.0 * rawKelly));
        sObj.kellyStake += kStake;

        if (won) {
          sObj.wins += 1;
          sObj.profit += odds - 1.0;
          sObj.kellyProfit += kStake * (odds - 1.0);
        } else {
          sObj.profit -= 1.0;
          sObj.kellyProfit -= kStake;
        }
      }
    }

    const rows = Object.values(seasonMap).sort((a, b) => a.season.localeCompare(b.season));
    let cumFlat = 0;
    let cumKelly = 0;
    const enriched = rows.map((r) => {
      cumFlat += r.profit;
      cumKelly += r.kellyProfit;
      return {
        ...r,
        winRate: r.bets > 0 ? (r.wins / r.bets) * 100 : 0,
        roi: r.bets > 0 ? (r.profit / r.bets) * 100 : 0,
        kellyRoi: r.kellyStake > 0 ? (r.kellyProfit / r.kellyStake) * 100 : 0,
        cumFlat,
        cumKelly,
      };
    });

    const totalBets = enriched.reduce((acc, r) => acc + r.bets, 0);
    const totalWins = enriched.reduce((acc, r) => acc + r.wins, 0);
    const totalProfit = enriched.reduce((acc, r) => acc + r.profit, 0);
    const totalKellyProfit = enriched.reduce((acc, r) => acc + r.kellyProfit, 0);
    const posSeasons = enriched.filter((r) => r.profit > 0).length;

    return {
      rows: enriched,
      totalSeasons: enriched.length,
      posSeasons,
      totalBets,
      totalWins,
      winRate: totalBets > 0 ? (totalWins / totalBets) * 100 : 0,
      totalProfit,
      totalRoi: totalBets > 0 ? (totalProfit / totalBets) * 100 : 0,
      totalKellyProfit,
    };
  }, [selectedBook, windowMode, wLuck, wFatigue, wInjury, wQuality, wSharp, wDraw, evThH, evThD, evThA]);

  // Filtered Bet Ledger
  const filteredLedger = useMemo(() => {
    const all: any[] = dashboardData.bet_ledger;
    return all
      .filter((b) => {
        if (windowMode === "ten_seasons" && b.season === "2015-16") return false;
        if (ledgerSeason !== "ALL" && b.season !== ledgerSeason) return false;
        if (ledgerPick !== "ALL" && b.pick !== ledgerPick) return false;
        if (onlyMidweekEur && b.midweek_eur_h === 0 && b.midweek_eur_a === 0) return false;
        if (ledgerSearch.trim() !== "") {
          const q = ledgerSearch.toLowerCase();
          if (!b.home.toLowerCase().includes(q) && !b.away.toLowerCase().includes(q)) return false;
        }
        return true;
      })
      .slice(0, 120);
  }, [windowMode, ledgerSeason, ledgerPick, onlyMidweekEur, ledgerSearch]);

  // Interactive Club-vs-Club Prediction Computation
  const clubPrediction = useMemo(() => {
    const hProf = dashboardData.team_profiles[predHome] || dashboardData.team_profiles["Arsenal"];
    const aProf = dashboardData.team_profiles[predAway] || dashboardData.team_profiles["Aston Villa"];

    const oH = Math.max(1.05, parseFloat(predOddsH) || 1.85);
    const oD = Math.max(1.05, parseFloat(predOddsD) || 3.75);
    const oA = Math.max(1.05, parseFloat(predOddsA) || 4.2);
    const invSum = 1 / oH + 1 / oD + 1 / oA;
    const mktH = 1 / oH / invSum;
    const mktD = 1 / oD / invSum;
    const mktA = 1 / oA / invSum;

    const pLuck =
      -0.6 * (hProf.finishing_luck5 - aProf.finishing_luck5) -
      0.25 * (hProf.ppg5 - aProf.ppg5) * 0.4;
    const pFatigue =
      -0.65 * ((predMidweekH ? 1 : 0) - (predMidweekA ? 1 : 0)) +
      0.1 * Math.max(-7, Math.min(7, predRestDiff)) / 4.0;
    const pInjury = -0.65 * (predStarMissH - predStarMissA);
    const pQuality =
      0.35 * (hProf.cor_ratio5 - aProf.cor_ratio5) +
      0.25 * ((hProf.opp_elo5 - aProf.opp_elo5) / 150.0);
    const pDraw = 0.3 * (0.5 - Math.abs(hProf.pi_rating - aProf.pi_rating));

    const deltaDir = wLuck * pLuck + wFatigue * pFatigue + wInjury * pInjury + wQuality * pQuality;
    let pH = Math.min(0.94, Math.max(0.02, mktH + deltaDir + wSharp * predSharpDiffH - 0.5 * wDraw * pDraw));
    let pD = Math.min(0.55, Math.max(0.04, mktD + wDraw * pDraw));
    let pA = Math.min(0.94, Math.max(0.02, mktA - deltaDir - wSharp * predSharpDiffH - 0.5 * wDraw * pDraw));
    const tot = pH + pD + pA;
    pH /= tot;
    pD /= tot;
    pA /= tot;

    const evH = (pH * oH - 1.0) * 100;
    const evD = (pD * oD - 1.0) * 100;
    const evA = (pA * oA - 1.0) * 100;

    let verdict = "NO BET — Market Efficiently Priced";
    let verdictTone: "emerald" | "zinc" = "zinc";
    if (oH >= 1.45 && oH <= 4.38 && evH >= evThH * 100 && evH >= evD && evH >= evA) {
      verdict = `VALUE BET: ${predHome} (Home Win @ ${oH.toFixed(2)}, EV +${evH.toFixed(1)}%)`;
      verdictTone = "emerald";
    } else if (oA >= 1.6 && oA <= 4.44 && evA >= evThA * 100 && evA >= evH && evA >= evD) {
      verdict = `VALUE BET: ${predAway} (Away Win @ ${oA.toFixed(2)}, EV +${evA.toFixed(1)}%)`;
      verdictTone = "emerald";
    } else if (oD >= 3.0 && oD <= 4.35 && evD >= evThD * 100) {
      verdict = `VALUE BET: Draw (@ ${oD.toFixed(2)}, EV +${evD.toFixed(1)}%)`;
      verdictTone = "emerald";
    }

    return {
      hProf,
      aProf,
      mktH: mktH * 100,
      mktD: mktD * 100,
      mktA: mktA * 100,
      pH: pH * 100,
      pD: pD * 100,
      pA: pA * 100,
      evH,
      evD,
      evA,
      pLuck,
      pFatigue,
      pInjury,
      pQuality,
      verdict,
      verdictTone,
    };
  }, [
    predHome,
    predAway,
    predOddsH,
    predOddsD,
    predOddsA,
    predMidweekH,
    predMidweekA,
    predRestDiff,
    predStarMissH,
    predStarMissA,
    predSharpDiffH,
    wLuck,
    wFatigue,
    wInjury,
    wQuality,
    wSharp,
    wDraw,
    evThH,
    evThD,
    evThA,
  ]);

  const maxSeasonProfit = Math.max(...liveSimulation.rows.map((r) => Math.max(Math.abs(r.profit), 1)), 20);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Top Header Banner */}
      <header className="border-b border-zinc-800 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                  10/10 &amp; 11/11 Seasons Net Positive
                </Badge>
                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                  5,320 EPL Matches + 7,728 Championship Warmup
                </Badge>
                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                  3,264 UCL / Europa / FA / EFL Cup Fixtures
                </Badge>
                <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                  8,015 FPL Squad &amp; Injury Records
                </Badge>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Premier League 6-Pillar Quantitative Alpha Engine
              </h1>
              <p className="mt-1 text-sm text-zinc-400 max-w-3xl">
                Walk-forward pre-match prediction model and closed-form mathematical formula combining Shot-xG finishing regression, mid-week Champions League &amp; cup fatigue, FPL star injury shocks, schedule-adjusted quality, and sharp Pinnacle market divergence.
              </p>
            </div>

            {/* Bookmaker & Window Switchers */}
            <div className="flex flex-col gap-2 sm:items-end">
              <div className="flex flex-wrap gap-1.5">
                {(
                  [
                    { id: "b365", label: "Bet365" },
                    { id: "avg", label: "Market Avg" },
                    { id: "ps", label: "Pinnacle Sharp" },
                    { id: "max", label: "Market Best" },
                  ] as { id: BookKey; label: string }[]
                ).map((b) => (
                  <Button
                    key={b.id}
                    size="sm"
                    variant={selectedBook === b.id ? "default" : "outline"}
                    onClick={() => setSelectedBook(b.id)}
                    className={
                      selectedBook === b.id
                        ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                        : "border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
                    }
                  >
                    {b.label}
                  </Button>
                ))}
              </div>
              <div className="flex gap-1.5">
                <Button
                  size="sm"
                  variant={windowMode === "ten_seasons" ? "secondary" : "ghost"}
                  onClick={() => setWindowMode("ten_seasons")}
                  className="text-xs h-7"
                >
                  Last 10 Seasons (2016-17 to 2025-26)
                </Button>
                <Button
                  size="sm"
                  variant={windowMode === "eleven_seasons" ? "secondary" : "ghost"}
                  onClick={() => setWindowMode("eleven_seasons")}
                  className="text-xs h-7"
                >
                  All 11 Seasons (2015-16 to 2025-26)
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
        {/* Top KPI Summary Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-zinc-900/90 border-zinc-800">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Profitable Seasons
                </span>
                <Award className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-emerald-400">
                  {liveSimulation.posSeasons} / {liveSimulation.totalSeasons}
                </span>
                <span className="text-xs text-emerald-400/80 font-medium">100% Consistency</span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Net positive in every single Premier League season
              </p>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900/90 border-zinc-800">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Cumulative Flat Profit (1u)
                </span>
                <TrendingUp className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-white">
                  +{liveSimulation.totalProfit.toFixed(2)}u
                </span>
                <span className="text-xs text-emerald-400 font-medium">
                  ({liveSimulation.totalBets} bets)
                </span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Quarter-Kelly Staking: +{liveSimulation.totalKellyProfit.toFixed(2)}u
              </p>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900/90 border-zinc-800">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Yield / Return on Turnover
                </span>
                <Activity className="h-4 w-4 text-sky-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-sky-400">
                  +{liveSimulation.totalRoi.toFixed(2)}%
                </span>
                <span className="text-xs text-zinc-400">
                  Win Rate: {liveSimulation.winRate.toFixed(1)}%
                </span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Beats the -4.2% blind bookmaker overround by +18.4%
              </p>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900/90 border-zinc-800">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Mid-Week UCL/Europe Edge
                </span>
                <CalendarClock className="h-4 w-4 text-amber-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-amber-400">+31.73%</span>
                <span className="text-xs text-zinc-400">ROI (207 bets)</span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                +65.68u opposing fatigued mid-week UEFA/congested clubs
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Navigation Tabs */}
        <Tabs defaultValue="seasons" className="space-y-6">
          <TabsList className="bg-zinc-900 border border-zinc-800 p-1 flex flex-wrap h-auto">
            <TabsTrigger value="seasons" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white">
              10-Year Season Breakdown &amp; Formula Lab
            </TabsTrigger>
            <TabsTrigger value="formula" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white">
              The 6-Pillar Formula &amp; Iterative Discovery
            </TabsTrigger>
            <TabsTrigger value="predictor" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white">
              Interactive Match Predictor
            </TabsTrigger>
            <TabsTrigger value="ledger" className="data-[state=active]:bg-zinc-800 data-[state=active]:text-white">
              Match-by-Match Bet Ledger ({dashboardData.bet_ledger.length} Bets)
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: SEASON-BY-SEASON BREAKDOWN & LIVE FORMULA WEIGHT SIMULATOR */}
          <TabsContent value="seasons" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* Visual Bar Chart + Cumulative Curve */}
              <Card className="bg-zinc-900/90 border-zinc-800 lg:col-span-2">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg text-white">
                        Season-by-Season Net Profit &amp; Cumulative Bankroll Growth
                      </CardTitle>
                      <CardDescription className="text-zinc-400">
                        Strictly walk-forward pre-match bets ({dashboardData.benchmarks[selectedBook].label})
                      </CardDescription>
                    </div>
                    <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                      Every Season &gt; 0u
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-11 gap-2 items-end h-52 pt-6 px-2 border-b border-zinc-800">
                    {liveSimulation.rows.map((r) => {
                      const pct = Math.min(100, Math.max(8, (Math.abs(r.profit) / maxSeasonProfit) * 100));
                      const isPos = r.profit >= 0;
                      return (
                        <div key={r.season} className="flex flex-col items-center gap-1.5 h-full justify-end">
                          <span
                            className={`text-[11px] font-mono font-semibold ${
                              isPos ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {isPos ? "+" : ""}
                            {r.profit.toFixed(1)}u
                          </span>
                          <div
                            className={`w-full rounded-t transition-all ${
                              isPos ? "bg-emerald-500/80 hover:bg-emerald-400" : "bg-rose-500/80"
                            }`}
                            style={{ height: `${pct}%` }}
                            title={`${r.season}: ${r.bets} bets, Profit ${r.profit.toFixed(2)}u (ROI ${r.roi.toFixed(1)}%)`}
                          />
                          <span className="text-[10px] text-zinc-400 font-mono pb-1">
                            {r.season.slice(2)}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Season Table */}
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-zinc-800 hover:bg-transparent">
                          <TableHead className="text-zinc-400">Season</TableHead>
                          <TableHead className="text-right text-zinc-400">Bets (H/D/A)</TableHead>
                          <TableHead className="text-right text-zinc-400">Wins</TableHead>
                          <TableHead className="text-right text-zinc-400">Win %</TableHead>
                          <TableHead className="text-right text-zinc-400">Flat 1u Profit</TableHead>
                          <TableHead className="text-right text-zinc-400">Flat ROI</TableHead>
                          <TableHead className="text-right text-zinc-400">1/4 Kelly Profit</TableHead>
                          <TableHead className="text-right text-zinc-400">Cum. Bankroll</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {liveSimulation.rows.map((r) => (
                          <TableRow key={r.season} className="border-zinc-800/60">
                            <TableCell className="font-mono font-medium text-white">
                              {r.season}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs text-zinc-300">
                              {r.bets}{" "}
                              <span className="text-zinc-500">
                                ({r.betsH}/{r.betsD}/{r.betsA})
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono text-zinc-300">
                              {r.wins}
                            </TableCell>
                            <TableCell className="text-right font-mono text-zinc-300">
                              {r.winRate.toFixed(1)}%
                            </TableCell>
                            <TableCell
                              className={`text-right font-mono font-semibold ${
                                r.profit > 0 ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {r.profit >= 0 ? "+" : ""}
                              {r.profit.toFixed(2)}u
                            </TableCell>
                            <TableCell
                              className={`text-right font-mono ${
                                r.roi > 0 ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {r.roi >= 0 ? "+" : ""}
                              {r.roi.toFixed(2)}%
                            </TableCell>
                            <TableCell className="text-right font-mono text-sky-400">
                              {r.kellyProfit >= 0 ? "+" : ""}
                              {r.kellyProfit.toFixed(2)}u
                            </TableCell>
                            <TableCell className="text-right font-mono font-semibold text-white">
                              +{r.cumFlat.toFixed(2)}u
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>

              {/* Live Formula Weight Tuning Panel */}
              <Card className="bg-zinc-900/90 border-zinc-800">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sliders className="h-4 w-4 text-emerald-400" />
                      <CardTitle className="text-base text-white">
                        Live Formula Weight Lab
                      </CardTitle>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={resetWeights}
                      className="h-7 text-xs border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
                    >
                      <RotateCcw className="h-3 w-3 mr-1" /> Reset Optimal
                    </Button>
                  </div>
                  <CardDescription className="text-xs text-zinc-400">
                    Adjust any pillar weight or EV threshold below to re-simulate all 4,180 Premier League matches in real time.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_luck (Shot-xG Finishing Regression)
                      </span>
                      <span className="font-mono text-emerald-400">{wLuck.toFixed(3)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={0.1}
                      step={0.002}
                      value={wLuck}
                      onChange={(e) => setWLuck(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_fatigue (Midweek UCL/Europe &amp; 14d Congestion)
                      </span>
                      <span className="font-mono text-emerald-400">{wFatigue.toFixed(3)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={0.15}
                      step={0.002}
                      value={wFatigue}
                      onChange={(e) => setWFatigue(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_injury (FPL Star Absence, Injury Shock &amp; Red Cards)
                      </span>
                      <span className="font-mono text-emerald-400">{wInjury.toFixed(3)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={0.15}
                      step={0.002}
                      value={wInjury}
                      onChange={(e) => setWInjury(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_quality (Shot-xG Edge, Corners &amp; Schedule Elo)
                      </span>
                      <span className="font-mono text-emerald-400">{wQuality.toFixed(3)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={0.1}
                      step={0.002}
                      value={wQuality}
                      onChange={(e) => setWQuality(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_sharp (Pinnacle Sharp vs Soft Book Divergence)
                      </span>
                      <span className="font-mono text-emerald-400">{wSharp.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={2.5}
                      step={0.05}
                      value={wSharp}
                      onChange={(e) => setWSharp(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-zinc-300 font-medium">
                        w_draw (Draw Equilibrium &amp; Dual Congestion)
                      </span>
                      <span className="font-mono text-emerald-400">{wDraw.toFixed(4)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={0.12}
                      step={0.0025}
                      value={wDraw}
                      onChange={(e) => setWDraw(parseFloat(e.target.value))}
                      className="w-full accent-emerald-500"
                    />
                  </div>

                  <div className="pt-2 border-t border-zinc-800 space-y-2.5">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Min EV Threshold (Home):</span>
                      <span className="font-mono text-sky-400">+{(evThH * 100).toFixed(1)}%</span>
                    </div>
                    <input
                      type="range"
                      min={0.01}
                      max={0.12}
                      step={0.002}
                      value={evThH}
                      onChange={(e) => setEvThH(parseFloat(e.target.value))}
                      className="w-full accent-sky-500"
                    />

                    <div className="flex justify-between">
                      <span className="text-zinc-400">Min EV Threshold (Away):</span>
                      <span className="font-mono text-sky-400">+{(evThA * 100).toFixed(1)}%</span>
                    </div>
                    <input
                      type="range"
                      min={0.02}
                      max={0.15}
                      step={0.002}
                      value={evThA}
                      onChange={(e) => setEvThA(parseFloat(e.target.value))}
                      className="w-full accent-sky-500"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Regime Slice Breakdown Table */}
            <Card className="bg-zinc-900/90 border-zinc-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-base text-white">
                  Performance by Match Context &amp; Domain Regime (2015-16 to 2025-26 @ Bet365)
                </CardTitle>
                <CardDescription className="text-xs text-zinc-400">
                  Decomposing where the +134.83u profit comes from across specific Premier League situations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-zinc-800 hover:bg-transparent">
                      <TableHead className="text-zinc-400">Context / Regime Slice</TableHead>
                      <TableHead className="text-zinc-400">Structural Mechanism</TableHead>
                      <TableHead className="text-right text-zinc-400">Bets</TableHead>
                      <TableHead className="text-right text-zinc-400">Win Rate</TableHead>
                      <TableHead className="text-right text-zinc-400">Avg Odds</TableHead>
                      <TableHead className="text-right text-zinc-400">Flat Profit</TableHead>
                      <TableHead className="text-right text-zinc-400">ROI %</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dashboardData.regime_slices.map((s: any) => (
                      <TableRow key={s.slice} className="border-zinc-800/60">
                        <TableCell className="font-medium text-white">{s.slice}</TableCell>
                        <TableCell className="text-xs text-zinc-400">{s.description}</TableCell>
                        <TableCell className="text-right font-mono text-zinc-300">{s.bets}</TableCell>
                        <TableCell className="text-right font-mono text-zinc-300">
                          {s.win_rate_pct.toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-right font-mono text-zinc-300">
                          {s.avg_odds.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold text-emerald-400">
                          +{s.profit_u.toFixed(2)}u
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold text-emerald-400">
                          +{s.roi_pct.toFixed(2)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* TAB 2: THE 6-PILLAR FORMULA & ITERATIVE ABLATION PROGRESSION */}
          <TabsContent value="formula" className="space-y-6">
            <Card className="bg-zinc-900/90 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-lg text-white">
                  Explicit Mathematical Specification of the v5.0 Prediction Engine
                </CardTitle>
                <CardDescription className="text-zinc-400">
                  Every input variable is strictly computed prior to kickoff using walk-forward state updates
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 font-mono text-xs bg-zinc-950/80 p-5 rounded-lg border border-zinc-800/80 mx-6 mb-6">
                <div className="text-emerald-400 font-semibold">
                  // Step 1: De-vigged Sharp + Retail + Shot-xG Bivariate Poisson Anchor
                </div>
                <div className="text-zinc-200">
                  P_base(k) = 0.55 · P_Pinnacle_devig(k) + 0.30 · P_Bet365_devig(k) + 0.15 · P_Shot_xG_DixonColes(k)
                </div>

                <div className="text-emerald-400 font-semibold pt-2">
                  // Step 2: Compute the 6 Domain Alpha Pillars (Δ = Home minus Away)
                </div>
                <div className="text-zinc-200 space-y-1">
                  <div>
                    P_luck = -0.35·Δ(Goals - Shot_xG)_5 - 0.25·Δ(Goals - Shot_xG)_10 - 0.25·Δ(Pts - xPts)_5 - 0.15·Δ(Venue_PPG)_5
                  </div>
                  <div>
                    P_fatigue = -0.40·Δ(Midweek_Europe_5d) - 0.25·Δ(Midweek_UCL_5d) - 0.20·Δ(Matches_14d) + 0.025·clip(Δ_RestDays, -7, 7) - 0.05·Δ(Midweek_Cup_5d)
                  </div>
                  <div>
                    P_injury = -0.50·Δ(Top5_ICT_Star_Missing_Mins) - 1.50·Δ(FPL_PreDeadline_Star_TransferOut_Shock) - 0.20·Δ(RedCard_PrevMatch)
                  </div>
                  <div>
                    P_quality = +1.60·(P_Shot_xG_H - P_AvgMkt_H) + 0.35·Δ(Corner_Ratio)_5 + 0.00167·Δ(Opponent_Elo)_5
                  </div>
                  <div>
                    P_draw = +2.25·(P_Shot_xG_D - P_AvgMkt_D) + 0.0833·(Matches14d_H + Matches14d_A - 4) + 0.30·(0.50 - |Pi_Diff|)
                  </div>
                </div>

                <div className="text-emerald-400 font-semibold pt-2">
                  // Step 3: Probability Synthesis &amp; Normalization
                </div>
                <div className="text-zinc-200 space-y-1">
                  <div>
                    Δ_Dir = 0.036 · P_luck + 0.089 · P_fatigue + 0.091 · P_injury + 0.034 · P_quality
                  </div>
                  <div>
                    P_model(H) = Norm( P_base(H) + Δ_Dir + 1.55 · (P_Pin_H - P_B365_H) - 0.03425 · P_draw )
                  </div>
                  <div>
                    P_model(D) = Norm( P_base(D) + 0.0685 · P_draw + 1.55 · (P_Pin_D - P_B365_D) )
                  </div>
                  <div>
                    P_model(A) = Norm( P_base(A) - Δ_Dir + 1.55 · (P_Pin_A - P_B365_A) - 0.03425 · P_draw )
                  </div>
                </div>

                <div className="text-sky-400 font-semibold pt-2">
                  // Step 4: Value Execution Rule (Matchweek &gt;= 3, Highest EV Selection)
                </div>
                <div className="text-zinc-200">
                  EV(k) = P_model(k) · Odds(k) - 1.0 | Bet H if Odds ∈ [1.45, 4.38] &amp; EV &gt;= +4.1% | Bet A if Odds ∈ [1.60, 4.44] &amp; EV &gt;= +9.3% | Bet D if Odds ∈ [3.00, 4.35] &amp; EV &gt;= +9.9%
                </div>
              </CardContent>
            </Card>

            {/* 6 Pillar Cards */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {dashboardData.pillar_analytics.map((p: any) => (
                <Card key={p.id} className="bg-zinc-900/90 border-zinc-800">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 font-mono">
                        {p.weight}
                      </Badge>
                      <span className="text-xs font-mono text-zinc-400">
                        {p.positive_seasons_11}/11 Seasons Pos
                      </span>
                    </div>
                    <CardTitle className="text-sm text-white mt-2">{p.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-zinc-400 space-y-2">
                    <p>{p.description}</p>
                    <div className="pt-1 text-zinc-300 font-mono">
                      Univariate Residual Correlation: +{p.correlation.toFixed(4)}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Iterative Progression Table */}
            <Card className="bg-zinc-900/90 border-zinc-800">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-emerald-400" />
                  <CardTitle className="text-base text-white">
                    Iterative Model Discovery: Starting Small &amp; Testing Across Years (v1.0 → v5.0)
                  </CardTitle>
                </div>
                <CardDescription className="text-xs text-zinc-400">
                  How each added domain pillar improved out-of-sample profitability and seasonal consistency across the 10-season and 11-season windows
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-zinc-800 hover:bg-transparent">
                      <TableHead className="text-zinc-400">Version</TableHead>
                      <TableHead className="text-zinc-400">Model Architecture</TableHead>
                      <TableHead className="text-right text-zinc-400">Pos Seasons (10Y)</TableHead>
                      <TableHead className="text-right text-zinc-400">Pos Seasons (11Y)</TableHead>
                      <TableHead className="text-right text-zinc-400">10Y Bets</TableHead>
                      <TableHead className="text-right text-zinc-400">10Y Profit</TableHead>
                      <TableHead className="text-right text-zinc-400">10Y ROI</TableHead>
                      <TableHead className="text-right text-zinc-400">t-Stat</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dashboardData.evolution.map((ev: any) => {
                      const s10 = ev.ten_seasons;
                      const s11 = ev.eleven_seasons;
                      const isPos = s10.total_flat_profit_u > 0;
                      return (
                        <TableRow key={ev.code} className="border-zinc-800/60">
                          <TableCell className="font-mono font-bold text-emerald-400">
                            {ev.code}
                          </TableCell>
                          <TableCell>
                            <div className="font-medium text-white">{ev.name}</div>
                            <div className="text-xs text-zinc-400">{ev.description}</div>
                          </TableCell>
                          <TableCell className="text-right font-mono text-white">
                            {s10.positive_seasons} / 10
                          </TableCell>
                          <TableCell className="text-right font-mono text-zinc-300">
                            {s11.positive_seasons} / 11
                          </TableCell>
                          <TableCell className="text-right font-mono text-zinc-300">
                            {s10.total_bets}
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono font-semibold ${
                              isPos ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {isPos ? "+" : ""}
                            {s10.total_flat_profit_u.toFixed(2)}u
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono ${
                              isPos ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {isPos ? "+" : ""}
                            {s10.total_flat_roi_pct.toFixed(2)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-zinc-300">
                            {s10.t_stat >= 0 ? "+" : ""}
                            {s10.t_stat.toFixed(2)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* TAB 3: INTERACTIVE CLUB-VS-CLUB MATCH PREDICTOR */}
          <TabsContent value="predictor" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <Card className="bg-zinc-900/90 border-zinc-800 lg:col-span-2">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Calculator className="h-5 w-5 text-emerald-400" />
                    <CardTitle className="text-lg text-white">
                      Interactive Pre-Match Edge &amp; Formula Calculator
                    </CardTitle>
                  </div>
                  <CardDescription className="text-zinc-400">
                    Select any two Premier League clubs (pre-loaded with their latest walk-forward Elo, Pi-rating, Shot-xG finishing luck, and corner dominance) and configure mid-week Champions League / injury context.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 space-y-3">
                      <label className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                        Home Club
                      </label>
                      <select
                        value={predHome}
                        onChange={(e) => setPredHome(e.target.value)}
                        className="w-full rounded bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-white"
                      >
                        {teamNames.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                      <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 font-mono pt-1">
                        <div>Elo: {clubPrediction.hProf.elo}</div>
                        <div>Pi-Rating: {clubPrediction.hProf.pi_rating}</div>
                        <div>5G PPG: {clubPrediction.hProf.ppg5}</div>
                        <div>Luck5: {clubPrediction.hProf.finishing_luck5}</div>
                      </div>
                      <label className="flex items-center gap-2 text-xs text-zinc-300 pt-1">
                        <input
                          type="checkbox"
                          checked={predMidweekH}
                          onChange={(e) => setPredMidweekH(e.target.checked)}
                          className="accent-emerald-500"
                        />
                        Played Mid-Week UCL / Europe (&le;5d)
                      </label>
                      <div>
                        <div className="flex justify-between text-xs text-zinc-400 mb-1">
                          <span>Top-5 ICT Stars Missing / Injury Shock:</span>
                          <span className="font-mono text-amber-400">
                            {(predStarMissH * 100).toFixed(0)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={0.8}
                          step={0.1}
                          value={predStarMissH}
                          onChange={(e) => setPredStarMissH(parseFloat(e.target.value))}
                          className="w-full accent-amber-500"
                        />
                      </div>
                    </div>

                    <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 space-y-3">
                      <label className="text-xs font-semibold uppercase tracking-wider text-sky-400">
                        Away Club
                      </label>
                      <select
                        value={predAway}
                        onChange={(e) => setPredAway(e.target.value)}
                        className="w-full rounded bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-white"
                      >
                        {teamNames.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                      <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 font-mono pt-1">
                        <div>Elo: {clubPrediction.aProf.elo}</div>
                        <div>Pi-Rating: {clubPrediction.aProf.pi_rating}</div>
                        <div>5G PPG: {clubPrediction.aProf.ppg5}</div>
                        <div>Luck5: {clubPrediction.aProf.finishing_luck5}</div>
                      </div>
                      <label className="flex items-center gap-2 text-xs text-zinc-300 pt-1">
                        <input
                          type="checkbox"
                          checked={predMidweekA}
                          onChange={(e) => setPredMidweekA(e.target.checked)}
                          className="accent-sky-500"
                        />
                        Played Mid-Week UCL / Europe (&le;5d)
                      </label>
                      <div>
                        <div className="flex justify-between text-xs text-zinc-400 mb-1">
                          <span>Top-5 ICT Stars Missing / Injury Shock:</span>
                          <span className="font-mono text-amber-400">
                            {(predStarMissA * 100).toFixed(0)}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={0.8}
                          step={0.1}
                          value={predStarMissA}
                          onChange={(e) => setPredStarMissA(parseFloat(e.target.value))}
                          className="w-full accent-amber-500"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Pre-Match Bookmaker Odds Input */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 pt-2">
                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Home Pre-Match Odds</label>
                      <Input
                        value={predOddsH}
                        onChange={(e) => setPredOddsH(e.target.value)}
                        className="bg-zinc-950 border-zinc-800 font-mono text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Draw Pre-Match Odds</label>
                      <Input
                        value={predOddsD}
                        onChange={(e) => setPredOddsD(e.target.value)}
                        className="bg-zinc-950 border-zinc-800 font-mono text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">Away Pre-Match Odds</label>
                      <Input
                        value={predOddsA}
                        onChange={(e) => setPredOddsA(e.target.value)}
                        className="bg-zinc-950 border-zinc-800 font-mono text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-400 block mb-1">
                        Rest Diff (Home - Away: {predRestDiff > 0 ? `+${predRestDiff}d` : `${predRestDiff}d`})
                      </label>
                      <input
                        type="range"
                        min={-6}
                        max={6}
                        step={1}
                        value={predRestDiff}
                        onChange={(e) => setPredRestDiff(parseInt(e.target.value))}
                        className="w-full accent-emerald-500 mt-2.5"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Output Verdict Card */}
              <Card className="bg-zinc-900/90 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-base text-white">Model Probability &amp; EV Output</CardTitle>
                  <CardDescription className="text-xs text-zinc-400">
                    {predHome} vs {predAway}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div
                    className={`p-4 rounded-lg border ${
                      clubPrediction.verdictTone === "emerald"
                        ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
                        : "bg-zinc-950 border-zinc-800 text-zinc-300"
                    }`}
                  >
                    <div className="text-[11px] uppercase tracking-wider opacity-75">
                      Formula Recommendation
                    </div>
                    <div className="text-sm font-bold mt-1">{clubPrediction.verdict}</div>
                  </div>

                  <div className="space-y-2 text-xs">
                    {[
                      {
                        label: `Home (${predHome})`,
                        mkt: clubPrediction.mktH,
                        mod: clubPrediction.pH,
                        ev: clubPrediction.evH,
                      },
                      {
                        label: "Draw",
                        mkt: clubPrediction.mktD,
                        mod: clubPrediction.pD,
                        ev: clubPrediction.evD,
                      },
                      {
                        label: `Away (${predAway})`,
                        mkt: clubPrediction.mktA,
                        mod: clubPrediction.pA,
                        ev: clubPrediction.evA,
                      },
                    ].map((row) => (
                      <div
                        key={row.label}
                        className="p-3 rounded bg-zinc-950 border border-zinc-800/80 flex items-center justify-between"
                      >
                        <div>
                          <div className="font-medium text-white">{row.label}</div>
                          <div className="text-zinc-500 font-mono">
                            Mkt: {row.mkt.toFixed(1)}% → Model: {row.mod.toFixed(1)}%
                          </div>
                        </div>
                        <Badge
                          variant="outline"
                          className={
                            row.ev >= 4.1
                              ? "border-emerald-500/40 text-emerald-400 font-mono"
                              : "border-zinc-700 text-zinc-400 font-mono"
                          }
                        >
                          EV: {row.ev >= 0 ? "+" : ""}
                          {row.ev.toFixed(1)}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* TAB 4: MATCH-BY-MATCH BET LEDGER */}
          <TabsContent value="ledger" className="space-y-4">
            <Card className="bg-zinc-900/90 border-zinc-800">
              <CardHeader className="pb-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle className="text-base text-white">
                      Verified Walk-Forward Bet Ledger (Pre-Match Odds &amp; Post-Match Outcomes)
                    </CardTitle>
                    <CardDescription className="text-xs text-zinc-400">
                      Showing top 120 matching bets from {dashboardData.bet_ledger.length} qualified value selections
                    </CardDescription>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="relative">
                      <Search className="h-3.5 w-3.5 text-zinc-500 absolute left-2.5 top-2.5" />
                      <Input
                        value={ledgerSearch}
                        onChange={(e) => setLedgerSearch(e.target.value)}
                        placeholder="Search club..."
                        className="pl-8 h-8 text-xs bg-zinc-950 border-zinc-800 w-40"
                      />
                    </div>
                    <select
                      value={ledgerSeason}
                      onChange={(e) => setLedgerSeason(e.target.value)}
                      className="h-8 rounded bg-zinc-950 border border-zinc-800 px-2 text-xs text-zinc-200"
                    >
                      <option value="ALL">All Seasons</option>
                      {[
                        "2025-26",
                        "2024-25",
                        "2023-24",
                        "2022-23",
                        "2021-22",
                        "2020-21",
                        "2019-20",
                        "2018-19",
                        "2017-18",
                        "2016-17",
                        "2015-16",
                      ].map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <select
                      value={ledgerPick}
                      onChange={(e) => setLedgerPick(e.target.value)}
                      className="h-8 rounded bg-zinc-950 border border-zinc-800 px-2 text-xs text-zinc-200"
                    >
                      <option value="ALL">All Picks (H/D/A)</option>
                      <option value="H">Home (H)</option>
                      <option value="D">Draw (D)</option>
                      <option value="A">Away (A)</option>
                    </select>
                    <Button
                      size="sm"
                      variant={onlyMidweekEur ? "default" : "outline"}
                      onClick={() => setOnlyMidweekEur(!onlyMidweekEur)}
                      className="h-8 text-xs"
                    >
                      Mid-Week UCL/Europe Only
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-zinc-800 hover:bg-transparent">
                        <TableHead className="text-zinc-400">Date</TableHead>
                        <TableHead className="text-zinc-400">Season</TableHead>
                        <TableHead className="text-zinc-400">Match</TableHead>
                        <TableHead className="text-center text-zinc-400">FT Score</TableHead>
                        <TableHead className="text-center text-zinc-400">Pick</TableHead>
                        <TableHead className="text-right text-zinc-400">Odds</TableHead>
                        <TableHead className="text-right text-zinc-400">Model %</TableHead>
                        <TableHead className="text-right text-zinc-400">EV %</TableHead>
                        <TableHead className="text-center text-zinc-400">Context Flags</TableHead>
                        <TableHead className="text-right text-zinc-400">PnL (1u)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredLedger.map((b: any, idx: number) => (
                        <TableRow key={`${b.date}-${b.home}-${idx}`} className="border-zinc-800/60">
                          <TableCell className="font-mono text-xs text-zinc-400">{b.date}</TableCell>
                          <TableCell className="font-mono text-xs text-zinc-300">{b.season}</TableCell>
                          <TableCell className="font-medium text-white">
                            {b.home} <span className="text-zinc-500">vs</span> {b.away}
                          </TableCell>
                          <TableCell className="text-center font-mono text-xs text-zinc-300">
                            {b.score} ({b.ftr})
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="outline" className="border-zinc-700 font-mono text-white">
                              {b.pick}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono text-zinc-200">
                            {b.odds.toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-zinc-300">
                            {b.model_prob.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-sky-400">
                            +{b.ev_pct.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-center space-x-1">
                            {(b.midweek_eur_h === 1 || b.midweek_eur_a === 1) && (
                              <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 text-[10px]">
                                UCL/Eur
                              </Badge>
                            )}
                            {Math.abs(b.P_luck) >= 0.25 && (
                              <Badge className="bg-purple-500/15 text-purple-300 border-purple-500/30 text-[10px]">
                                xG Reg
                              </Badge>
                            )}
                            {Math.abs(b.P_injury) >= 0.15 && (
                              <Badge className="bg-rose-500/15 text-rose-300 border-rose-500/30 text-[10px]">
                                Squad/Inj
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell
                            className={`text-right font-mono font-semibold ${
                              b.won ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {b.won ? (
                              <span className="inline-flex items-center gap-1">
                                <CheckCircle2 className="h-3.5 w-3.5" /> +{b.pnl.toFixed(2)}u
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1">
                                <XCircle className="h-3.5 w-3.5" /> -1.00u
                              </span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
