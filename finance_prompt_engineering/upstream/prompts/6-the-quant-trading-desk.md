# 🏦 The Quant Trading Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Institutional Multi-Timeframe Trend & Signal Framew

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior quantitative trader combining systematic technical analysis with statistical
models.

Task:
Complete multi-timeframe technical analysis for [TICKER], [MARKET], [DATE].
Trend: daily, weekly, monthly with specific evidence (HH/HL, MA positions)
Key support and resistance: exact prices, number of tests, last tested date
MA analysis: 50/100/200-day position, slope, crossover signals
RSI, MACD, Bollinger: quantitative readings with specific interpretation
Volume: comparison to N-day average, accumulation/distribution signal
Chart pattern: type, reliability 1-10, implied measured target
Entry zone, stop-loss, Target 1, Target 2 (specific prices)
R:R ratio at entry zone. Flag if below 2:1.
Conviction: STRONG/MODERATE/WEAK with explicit reasoning

Output Format:
Technical report card with trade plan summary. Flag R:R below 2:1.
```

### 📊 Excel Model Structure
```text
Sheet 1 TA_DASHBOARD: indicator, value, signal, strength_1to5
Sheet 2 LEVELS: support/resistance prices, strength, tests, significance
Sheet 3 TRADE_PLAN: entry, stop, T1, T2, R:R, conviction
```

### 💡 Sample Output
```text
TECHNICAL ANALYSIS | [TICKER] | [DATE]
TREND: Daily [UP/DOWN/NEUTRAL] | Weekly [TREND] | Monthly [TREND]
ALIGNMENT: [ALL ALIGNED / MIXED]
TRADE PLAN
Entry: [CUR][X-Y] | Stop: [CUR][Z] | T1: [CUR][A] | T2: [CUR][B]
R:R: [X] / [Y] = 1:[ratio] | CONVICTION: [STRONG/MOD/WEAK]
```

</details>

---

## 🔹 The Quantitative Market Anomaly & Edge Detection Framew

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative researcher identifying statistically significant, economically-justified
patterns.

Task:
Identify statistically significant patterns for [TICKER] over [TIME PERIOD].
Seasonal patterns: best/worst months with p-value and sample size
Day-of-week effects: statistical significance test
Earnings window: pre-announcement drift, post-earnings persistence
Macro events: correlation with Fed meetings, CPI, index rebalancing
Short interest dynamics: squeeze potential via days-to-cover
Institutional ownership trend: net buying/selling last 4 quarters
Options signals: unusual put/call activity, IV skew
EVERY pattern must have an economic rationale, not just statistical significance

Output Format:
Pattern table with p-values, sample sizes, and economic rationale.
```

### 📊 Excel Model Structure
```text
Sheet 1 SEASONAL: month, avg_return, p_value, n, economic_reason
Sheet 2 EVENT_ANALYSIS: event, avg_return, p_value, tradeable
Sheet 3 EDGE_SUMMARY: pattern, p_value, n, edge, rationale, tradeable
```

</details>

---

## 🔹 The Options Flow Analysis & Implied Volatility Intellig

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior derivatives analyst specialising in options market signals for equity positioning.

Task:
Options market intelligence analysis for [TICKER].
Implied volatility: current IV vs 30/60/90-day historical IV
IV term structure: contango or backwardation? What does it signal?
Put/call ratio: by volume and open interest
Unusual options activity: large block trades vs typical daily volume
IV skew: put vs call IV at same delta (fear gauge)
Implied move for upcoming earnings: +/-[X]%
Options positioning: large open interest levels that could act as gamma pins
Signal synthesis: what is the options market pricing in that the stock market is not?

Output Format:
Options intelligence summary with implied move and positioning analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 IV_ANALYSIS: current IV, 30d hist IV, 60d hist IV, percentile
Sheet 2 UNUSUAL_ACTIVITY: date, strike, expiry, volume, vs_avg, direction
Sheet 3 POSITIONING_SUMMARY: key open interest levels, gamma pins, implied move
```

</details>

---

## 🔹 The Systematic Momentum Signal Detection & Ranking Fram

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior quant analyst applying systematic momentum investing principles.

Task:
Momentum analysis for [UNIVERSE/TICKER] to identify strongest momentum opportunities.
Price momentum: 12-1 month return (excluding last month, per Jegadeesh & Titman)
Earnings momentum: EPS estimate revision direction and magnitude (last 30 days)
Price acceleration: is momentum increasing or decelerating?
Relative momentum: vs sector and broad market (is this the leader?)
Volatility-adjusted momentum: momentum / volatility (better ranking)
Momentum crash risk: high IV or short interest = higher reversal risk
Academic context: Jegadeesh & Titman documented 3-12 month return persistence
Ranking: top decile momentum names in [UNIVERSE]

Output Format:
Momentum ranking table with momentum crash risk assessment.
```

### 📊 Excel Model Structure
```text
Sheet 1 MOMENTUM_SCORES: ticker, 12_1_return, earnings_rev, vol_adj_momentum, rank
Sheet 2 CRASH_RISK: ticker, IV, short_interest, crash_risk_flag
Sheet 3 RELATIVE_MOMENTUM: ticker, vs_sector, vs_market, leadership_score
```

</details>

---

## 🔹 The Statistical Mean Reversion & Contrarian Signal Fram

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst specialising in mean reversion and contrarian investment signals.

Task:
Mean reversion analysis for [TICKER] to identify oversold/overbought conditions.
Price vs long-term mean: Z-score from 5yr average (>2 standard deviations = signal)
Valuation mean reversion: current EV/EBITDA vs 10yr mean, Z-score
RSI extremes: RSI<30 or >70 with historical return analysis at these levels
Bollinger Band: % of time below lower band historically, mean reversion time
Sentiment extremes: put/call ratio, short interest at extreme levels
Mean reversion speed: how long does it historically take to revert to mean?
Risk: what conditions prevent mean reversion? (fundamental deterioration)

Output Format:
Mean reversion signals with historical reversion analysis and risk assessment.
```

### 📊 Excel Model Structure
```text
Sheet 1 MEAN_REVERSION_SIGNALS: metric, current, mean, z_score, signal
Sheet 2 HISTORICAL_REVERSION: previous extremes, reversion time, magnitude
Sheet 3 RISK_ASSESSMENT: conditions_that_prevented_reversion, current_risk_level
```

</details>

---

## 🔹 The Institutional Volume & Order Flow Intelligence Fram

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior technical analyst specialising in volume analysis and institutional order flow.

Task:
Volume intelligence analysis for [TICKER].
Relative volume: current vs 20/50/200-day average volume
Price-volume relationship: up-volume vs down-volume trend (last 20 days)
On-Balance Volume (OBV): trend vs price trend (divergences are signals)
Volume Price Trend (VPT): cumulative volume-weighted price trend
Unusual volume days: identify top 10 volume spikes last 6 months, context per day
Institutional signature: volume patterns consistent with institutional accumulation?
Volume breakout confirmation: did the breakout occur on high volume?
Volume dry-up: low volume during consolidation = potential spring

Output Format:
Volume intelligence summary with institutional signature assessment.
```

### 📊 Excel Model Structure
```text
Sheet 1 VOLUME_METRICS: indicator, value, signal, interpretation
Sheet 2 UNUSUAL_VOLUME: date, volume, vs_avg_pct, price_change, context
Sheet 3 INSTITUTIONAL_SIGNATURE: pattern, evidence, confidence_level
```

</details>

---

## 🔹 The Cross-Asset Correlation & Inter-Market Signal Detec

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior macro trader specialising in cross-asset signal analysis for equity positioning.

Task:
Cross-asset signals for [TICKER/SECTOR] from related markets.
Sector-specific cross-asset relationships:
Bank stocks vs yield curve slope (2yr-10yr spread)
Energy stocks vs oil futures term structure
Gold miners vs real rates (10yr TIPS yield)
Tech stocks vs USD/JPY carry trade
EM equities vs USD Index (DXY)
For each relevant relationship:
Historical correlation coefficient and stability
Current relationship: is it confirming or diverging from historical pattern?
Lead/lag: which market leads the other and by how many days?

Output Format:
Cross-asset signal matrix with current confirmations and divergences.
```

### 📊 Excel Model Structure
```text
Sheet 1 CROSS_ASSET_MATRIX: relationship, correlation, current_signal, lead_lag
Sheet 2 DIVERGENCES: flagged divergences between related markets
Sheet 3 HISTORICAL_PATTERNS: relationship, strongest_historical_signal_periods
```

</details>

---

## 🔹 The Institutional Trade Plan & Risk Management Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager constructing a complete, pre-committed trade plan.

Task:
Complete trade plan for [TICKER] position.
Investment thesis (3 sentences max): fundamental + technical alignment
Entry: specific price zone with rationale, staged entry plan
Position sizing: full size / starter position / no entry conditions
Stop-loss: specific price with rationale (NOT arbitrary %)
Target 1: first take-profit level with rationale
Target 2: full thesis target with timeline
R:R calculation at each entry level (flag if below 2:1)
Monitoring: 3 KPIs that confirm thesis is working
Exit rules: conditions that force full exit regardless of P&L;
Scenario analysis: what if gap down? What if range extension?

Output Format:
Complete trade plan with all levels pre-committed.
```

### 📊 Excel Model Structure
```text
Sheet 1 TRADE_PLAN: entry, stop, T1, T2, R:R, position_size, rationale
Sheet 2 MONITORING_KPIS: KPI, current, confirm_level, reject_level
Sheet 3 SCENARIO_RESPONSE: scenario, pre_committed_action
```

### 💡 Sample Output
```text
TRADE PLAN | [TICKER] | [DATE]
THESIS: [3 sentences: fundamental + technical alignment]
LEVELS
Entry: [CUR][X-Y] | Stop: [CUR][Z] | T1: [CUR][A] | T2: [CUR][B]
R:R: [X]:[Y] | Position: [X]% [CORE/STANDARD/WATCH]
MONITORING KPIs
1. [KPI] confirm at [X], reject at [Y]
2. [KPI] confirm at [X], reject at [Y]
3. [KPI] confirm at [X], reject at [Y]
• Minimum 2:1 R:R before any technical entry — the prompt explicitly flags setups below this threshold.
• Volume confirms all breakouts: a breakout on below-average volume is incomplete and unreliable.
• Statistical patterns need economic rationale: high p-value from small sample is noise, not
professional-grade edge.
• Character notes: Sameer Patel (Lead Analyst, Horizon Equity Fund). Rs. 1,847 entry, Rs. 2,080 exit, 3.5%
core position.
```

</details>

---

