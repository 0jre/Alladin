# 🏦 The Macro Risk Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Ray Dalio All-Weather Portfolio Environment Assessm

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk analyst applying Ray Dalio's publicly documented All-Weather portfolio
framework.

Task:
Assess my portfolio against Dalio's All-Weather framework (from his public research).
Dalio's four economic environments:
1. Rising growth + rising inflation: commodities, gold, equities
2. Rising growth + falling inflation: equities, corporate bonds
3. Falling growth + rising inflation: gold, commodities, inflation bonds
4. Falling growth + falling inflation: long bonds, gold
Per environment: estimated portfolio return and exposure assessment
Probability of each environment next 12 months (your assessment)
Which environment is my portfolio least protected against?
Rebalancing: how to improve All-Weather balance?
My portfolio: [LIST ASSET CLASSES AND WEIGHTS]
My macro view: [GROWTH AND INFLATION OUTLOOK]

Output Format:
All-Weather matrix with portfolio exposure and rebalancing recommendations.
```

### 📊 Excel Model Structure
```text
Sheet 1 ENVIRONMENT_MATRIX: environment, probability, portfolio_return, ideal_assets
Sheet 2 CURRENT_EXPOSURE: asset_class, weight, return_per_environment
Sheet 3 REBALANCING: current, target, delta, rationale
```

</details>

---

## 🔹 The Macro Hedge Fund Risk Assessment Protocol

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk analyst at a macro hedge fund with expertise in systematic portfolio risk.

Task:
Complete risk assessment of my portfolio.
Factor exposure: growth, value, quality, momentum, rate sensitivity tilts vs benchmark
Correlation clusters: which positions move together and why
Concentration: sector, geography, factor, liquidity dimensions
Liquidity: days-to-exit at normal volume (1=same day, 5=5+ days)
Stress scenarios:
2008 GFC: equities -38%, bonds +8%, gold +12%
2020 COVID: equities -32%, bonds +5%, gold +8%
2022 Rate Shock: equities -18%, bonds -13% simultaneously
Custom: [YOUR SCENARIO]
Top 3 hedging recommendations: instrument, size, cost, rationale
My portfolio: [HOLDINGS, WEIGHTS, TOTAL NAV, CURRENCY]

Output Format:
Risk report with RED/AMBER/GREEN heat map. Stress test by position.
```

### 📊 Excel Model Structure
```text
Sheet 1 RISK_HEATMAP: dimension, RAG, current_level, limit, action
Sheet 2 FACTOR_EXPOSURE: factor, portfolio_tilt, benchmark, active_weight
Sheet 3 STRESS_SCENARIOS: each_position, portfolio_total, currency_PL
Sheet 4 HEDGING_PLAN: instrument, size_pct, cost_pct_NAV, rationale
```

### 💡 Sample Output
```text
RISK REPORT | [DATE] | [CUR][X]
HEAT MAP
Factor Concentration | [R] | [X]% growth vs benchmark [Y]%
2022 Scenario: -[X]% | [CUR]-[Y] | BONDS DID NOT HEDGE
```

</details>

---

## 🔹 The Deep Portfolio Vulnerability & Assumption Challenge

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk analyst applying radical transparency principles to challenge every portfolio
assumption.

Task:
Radical transparency risk review of my portfolio and thesis.
Challenge every assumption in my investment thesis:
5 most confident assumptions — what is the historical evidence each is wrong?
What would have to be true for the entire thesis to fail simultaneously?
Identify blind spots:
Correlation risks: assets assumed uncorrelated that correlated historically
Narrative risk: following consensus without independent verification?
Recency bias: overweighting recent data?
Pre-mortem: simulate -[X]% loss in 12 months. Work backwards. Most plausible path?
My portfolio and thesis: [DESCRIBE]

Output Format:
Assumption challenge table and pre-mortem simulation.
```

### 📊 Excel Model Structure
```text
Sheet 1 ASSUMPTION_CHALLENGE: assumption, confidence, counter_evidence, fragility
Sheet 2 BLIND_SPOTS: risk, why_overlooked, monitoring_signal
Sheet 3 PREMORTEM: assumed_loss, plausible_path, early_warning_signals
```

</details>

---

## 🔹 The Multi-Scenario Historical & Hypothetical Stress Tes

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative risk manager specialising in comprehensive scenario-based stress testing.

Task:
Comprehensive stress test across historical and hypothetical scenarios.
Portfolio: [LIST ASSET CLASSES AND WEIGHTS]
HISTORICAL (calibrated):
2008 GFC: equities -40%, IG bonds +8%, HY -25%, gold +12%
2011 European Debt: equities -20%, peripheral bonds -15%
2020 COVID: equities -32%, bonds +5%, oil -60%
2022 Rate Shock: equities -18%, 10yr bonds -16%, 30yr bonds -28%
HYPOTHETICAL:
China hard landing: GDP -3%, global equities -25%
Stagflation: inflation 8%+, growth -1%, equities -22%, bonds -12%
[YOUR SPECIFIC SCENARIO]
Most severe scenario for THIS portfolio and why

Output Format:
Scenario results by asset class with portfolio total and currency P&L.;
```

### 📊 Excel Model Structure
```text
Sheet 1 SCENARIO_RESULTS: asset classes as columns, scenarios as rows
Sheet 2 PL_ATTRIBUTION: each holding's contribution per scenario
Sheet 3 WORST_SCENARIOS: top 3 most damaging with driver analysis
```

</details>

---

## 🔹 The Institutional Tail Risk Quantification & Hedging Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk manager specialising in tail risk quantification and systematic hedging.

Task:
Quantify and develop tail risk protection for my portfolio.
Tail risk metrics:
VaR 95% and 99% over 1-day and 10-day horizons
Expected Shortfall (CVaR): average loss beyond VaR
Maximum drawdown: historical and forward estimate
Skewness and kurtosis: is distribution fat-tailed?
Hedging options:
Put options: cost, protection level, optimal strike/expiry
Put spreads: buy/sell structure, cost vs protection trade-off
Gold allocation: crisis correlation benefit
Optimal hedge within [X]% NAV annual budget

Output Format:
Tail risk metrics, hedging options, and optimal hedge recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 TAIL_METRICS: VaR_95, VaR_99, CVaR, max_drawdown, skewness, kurtosis
Sheet 2 HEDGING_OPTIONS: instrument, cost_pct_NAV, protection_level, pros, cons
Sheet 3 OPTIMAL_HEDGE: selected instruments, combined cost, combined protection
```

</details>

---

## 🔹 The Multi-Currency Portfolio FX Exposure & Hedging Stra

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk manager specialising in currency risk for multi-currency institutional
portfolios.

Task:
FX exposure and hedging strategy for my multi-currency portfolio.
Exposure mapping: direct (foreign-denominated assets), economic (foreign revenue),
translation
Correlation: how does each currency pair correlate with equity positions?
Optimal hedge ratio: academic research on institutional FX hedging
Hedging instruments: FX forwards (carry cost), FX options (premium vs protection)
Natural hedges: matching revenue and cost currencies
Recommended strategy: hedge ratio, instruments, review frequency
My FX exposure: [LIST CURRENCIES AND EXPOSURE %]

Output Format:
FX exposure map, hedging cost analysis, and recommended strategy.
```

### 📊 Excel Model Structure
```text
Sheet 1 FX_EXPOSURE: currency, direct_pct, economic_pct, correlation_to_equity
Sheet 2 HEDGING_COST: currency, forward_cost_bps, option_premium, carry
Sheet 3 HEDGE_RECOMMENDATION: currency, exposure, ratio, instrument, rationale
```

</details>

---

## 🔹 The Portfolio Liquidity Profile & Redemption Risk Analy

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior risk manager specialising in liquidity risk for open-end and closed-end funds.

Task:
Comprehensive liquidity risk assessment for my portfolio.
Position-level: ADTV per holding, position as % ADTV (flag >10%)
Days-to-exit at 20% ADTV participation: classify 1-day, 3-day, 7-day, >7-day
Portfolio profile: % liquidatable in 1/3/7 days
Redemption mismatch: fund terms vs underlying liquidity
Crisis scenario: if ADTV halves, how long to liquidate?
Recommendations: positions to reduce for liquidity improvement
My portfolio: [HOLDINGS, SIZES, ADTV IF KNOWN]

Output Format:
Liquidity profile by position with days-to-exit and crisis scenario.
```

### 📊 Excel Model Structure
```text
Sheet 1 LIQUIDITY_PROFILE: ticker, position, ADTV, pct_ADTV, days_to_exit, bucket
Sheet 2 PORTFOLIO_LIQUIDITY: pct_1day, pct_3day, pct_7day, pct_over7day
Sheet 3 ILLIQUID_FLAGS: positions >10% ADTV with reduction recommendations
```

</details>

---

## 🔹 The Portfolio Drawdown Attribution & Recovery Analysis

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio analyst specialising in drawdown attribution and recovery strategy.

Task:
Drawdown attribution and recovery analysis for my portfolio.
Current drawdown: from peak [CUR][X] to trough [CUR][Y] on [DATE]
Attribution: % of drawdown from factor exposure, stock selection, sector, currency
Which positions contributed most? Quantify each.
Historical recovery: comparable drawdowns — average recovery time
What market conditions were present at the start of prior recoveries?
Recovery positioning: which changes would accelerate recovery?
Opportunity cost: hold vs realise losses and reposition
My portfolio: [LIST] | Peak: [CUR][X] | Current: [CUR][Y]

Output Format:
Drawdown attribution table with recovery analysis and repositioning recommendations.
```

### 📊 Excel Model Structure
```text
Sheet 1 ATTRIBUTION: factor, pct_of_drawdown, by_position
Sheet 2 POSITION_ATTRIBUTION: ticker, contribution, recovery_likelihood
Sheet 3 RECOVERY_SCENARIOS: scenario, assumptions, timeline, signals
• Dalio's All-Weather framework is the best antidote to scenario blindness: it forces you to think about all four
macro environments, not just your base case.
• The 2022 Rate Shock is the most important scenario to run: it is the one where bonds failed to hedge
equities.
• Tail risk hedging is an insurance cost, not a return drag: budget 0.5-1.0% of NAV annually.
• Character notes: Ravi Mehta (Portfolio Manager). Arun Kumar (CRO). Rs. 200 crore. 71% growth factor tilt.
8 risk prompts. Friday approval.
```

</details>

---

