# 🏦 The Portfolio Strategy Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Modern Portfolio Theory Mean-Variance Optimisation

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior quantitative analyst applying Harry Markowitz's Nobel Prize-winning MPT framework.

Task:
Build a mean-variance optimised portfolio using Markowitz's documented framework.
Expected returns per asset class: [PROVIDE OR DERIVE FROM HISTORICAL DATA]
Covariance matrix: historical correlations and volatilities
Efficient frontier: trace the frontier from minimum variance to maximum Sharpe
Optimal portfolios on the frontier:
Minimum variance portfolio: lowest risk regardless of return
Maximum Sharpe portfolio: best risk-adjusted return
Target return portfolio at [X]%: weights and risk
Sensitivity: how do weights change if expected returns shift by +/- 1%?
Critique: Markowitz limitations (sensitivity to inputs, no tail risk)
My asset classes and data: [LIST WITH EXPECTED RETURNS AND RISK]

Output Format:
Efficient frontier with optimal portfolios and input sensitivity.
```

### 📊 Excel Model Structure
```text
Sheet 1 EFFICIENT_FRONTIER: risk, return, Sharpe for 50+ portfolios on frontier
Sheet 2 OPTIMAL_PORTFOLIOS: min_var, max_Sharpe, target_return weights
Sheet 3 SENSITIVITY: weights at +/-1% expected return changes per asset class
```

</details>

---

## 🔹 The Institutional Asset Allocation & IPS Construction F

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio strategist managing multi-asset institutional mandates globally.

Task:
Build a complete Investment Policy Statement for [CLIENT/MANDATE].
My situation: [INVESTOR TYPE], [AUM], [HORIZON], [RISK TOLERANCE],
[ACCOUNT TYPE], [SPENDING REQUIREMENT if any], [TAX CONTEXT], [UNIQUE CONSTRAINTS]
RRTTLLU framework:
Return: required return and derivation
Risk: maximum tolerable drawdown and volatility
Time: investment horizon and liquidity event timeline
Tax: applicable treatment
Liquidity: minimum liquid allocation
Legal: regulatory and fiduciary constraints
Unique: specific constraints not captured above
SAA: exact % per asset class with min/max ranges
Instruments: ETF/fund per class with TER
Rebalancing: quarterly calendar + drift trigger at +/-[X]%
One-page IPS in plain English

Output Format:
Complete IPS with SAA table and rebalancing policy.
```

### 📊 Excel Model Structure
```text
Sheet 1 SAA: class, target_pct, min, max, instrument, TER, expected_return
Sheet 2 REBALANCING_TRACKER: auto-calculates drift from monthly input
Sheet 3 RETURN_PROJECTIONS: 10yr expected return, vol, Sharpe
```

### 💡 Sample Output
```text
IPS | [CLIENT] | [DATE]
SAA
[Asset Class A]: [X]% Instrument: [NAME] Range: [X-Y]%
[Asset Class B]: [X]% Instrument: [NAME] Range: [X-Y]%
Expected return: [X]%/yr | Max drawdown est: -[X]%
Benchmark: [DESCRIBE] | Rebalancing: Quarterly + [X]% drift trigger
```

</details>

---

## 🔹 The Brinson-Hood-Beebower Performance Attribution Frame

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior performance analyst applying the BHB factor attribution methodology.

Task:
BHB performance attribution for [PORTFOLIO] vs [BENCHMARK] over [PERIOD].
Allocation effect: excess return from overweighting outperforming sectors
Selection effect: excess return from stock selection within sectors
Interaction effect: combined allocation and selection
Total active return = Allocation + Selection + Interaction
By sector: which sectors contributed most to each effect?
By time period: where was skill demonstrated vs luck?
Information Ratio: active return / tracking error
Appraisal ratio: alpha / specific risk
My portfolio vs benchmark data: [PROVIDE SECTOR WEIGHTS AND RETURNS]

Output Format:
BHB attribution table with IR and skill assessment.
```

### 📊 Excel Model Structure
```text
Sheet 1 BHB_ATTRIBUTION: sector, alloc_effect, selection_effect, interaction, total
Sheet 2 TIME_SERIES: attribution by quarter showing consistency
Sheet 3 SKILL_ASSESSMENT: IR, appraisal_ratio, consistency_score
```

</details>

---

## 🔹 The Global Investment Performance Standards Compliant R

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior performance analyst preparing GIPS-compliant performance presentations.

Task:
GIPS-compliant performance presentation for [COMPOSITE NAME].
Required GIPS disclosures:
Composite creation date
Number of portfolios (if <5, disclose)
Composite assets and firm total assets
3-yr annualised standard deviation (composite and benchmark)
Internal dispersion of composite returns
Time-weighted returns: 1yr, 3yr, 5yr, 10yr or since inception
Benchmark returns for same periods
Gross vs net of fees: both required
Any significant events affecting the composite

Output Format:
GIPS-compliant performance table with all required disclosures.
```

### 📊 Excel Model Structure
```text
Sheet 1 PERFORMANCE_TABLE: period, gross_return, net_return, benchmark, std_dev
Sheet 2 COMPOSITE_STATS: number_of_portfolios, composite_assets, firm_assets
Sheet 3 DISCLOSURES: all required GIPS disclosure statements
```

</details>

---

## 🔹 The Institutional Portfolio Rebalancing Policy & Execut

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager designing systematic rebalancing policy for institutional
mandates.

Task:
Design a rebalancing policy and execution protocol for [PORTFOLIO].
Rebalancing approaches compared:
Calendar: quarterly/monthly regardless of drift
Threshold: rebalance when any asset drifts [X]% from target
Range: rebalance when outside min/max band
Hybrid: calendar plus threshold trigger
Cost analysis: transaction costs vs tracking error of each approach
Tax efficiency: harvest losses during rebalancing where applicable
Execution: which assets to rebalance first? New money vs sells?
Governance: IC approval required at what threshold?
My SAA and current allocation: [DESCRIBE]

Output Format:
Rebalancing policy with cost/benefit analysis and execution protocol.
```

### 📊 Excel Model Structure
```text
Sheet 1 APPROACH_COMPARISON: method, tracking_error, transaction_cost, tax_impact
Sheet 2 DRIFT_MONITOR: asset, target, current, drift, trigger_flag
Sheet 3 EXECUTION_PROTOCOL: sequence, approval_required, documentation
```

</details>

---

## 🔹 The Institutional Benchmark Construction & Appropriaten

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio strategist specialising in benchmark design and performance measurement.

Task:
Design an appropriate benchmark for [PORTFOLIO/STRATEGY].
Benchmark criteria (Bailey's documented properties):
Unambiguous: clearly defined, reproducible
Investable: can be replicated passively
Measurable: daily/monthly prices available
Appropriate: reflects investment strategy
Reflective of current investment opinions
Specified in advance
Benchmark options: single index, blended, liability benchmark, absolute return
Blended benchmark construction: which indices in what weights?
Back-test: how has the portfolio performed vs proposed benchmark historically?
My strategy: [DESCRIBE]

Output Format:
Benchmark comparison with Bailey criteria assessment and back-test.
```

### 📊 Excel Model Structure
```text
Sheet 1 BENCHMARK_OPTIONS: option, Bailey_criteria_score, rationale
Sheet 2 BLENDED_CONSTRUCTION: index, weight, TER, liquidity
Sheet 3 HISTORICAL_COMPARISON: portfolio, benchmark, active_return by period
```

</details>

---

## 🔹 The Institutional Portfolio Construction Quality Assess

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio analyst conducting a comprehensive portfolio construction review.

Task:
Full portfolio construction review for [PORTFOLIO].
Position count: is the portfolio adequately or over-diversified?
Concentration: top 5 and top 10 holdings as % of portfolio
Factor tilts: unintended factor bets vs stated investment philosophy
Conviction alignment: are largest positions the highest-conviction ideas?
Liquidity profile: days-to-exit across the portfolio
Sector/geography/currency balance
Cost efficiency: total TER of the portfolio
Turnover: is trading frequency appropriate for the stated horizon?
My portfolio: [LIST HOLDINGS AND WEIGHTS]

Output Format:
Portfolio construction scorecard with specific improvement recommendations.
```

### 📊 Excel Model Structure
```text
Sheet 1 CONSTRUCTION_SCORECARD: dimension, current, benchmark, rating, recommendation
Sheet 2 FACTOR_TILTS: factor, unintended_tilt, direction, action
Sheet 3 POSITION_ANALYSIS: holding, pct, conviction_rank, liquidity, flag
```

</details>

---

## 🔹 The Institutional Risk-Adjusted Return Analysis Framewo

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior performance analyst applying Sharpe, Sortino, and Calmar risk-adjusted frameworks.

Task:
Comprehensive risk-adjusted performance analysis for [PORTFOLIO] vs [BENCHMARK].
Sharpe ratio: (return - RF) / total standard deviation
Sortino ratio: (return - MAR) / downside deviation (penalises downside only)
Calmar ratio: annual return / maximum drawdown
Information ratio: active return / tracking error
Treynor ratio: (return - RF) / beta
Jensen's alpha: actual return vs CAPM-predicted return
M2 measure: portfolio return scaled to same risk as benchmark
Omega ratio: probability-weighted ratio of gains to losses
My performance data: [PROVIDE RETURNS, BENCHMARK, RF RATE]

Output Format:
Complete risk-adjusted performance table with interpretation.
```

### 📊 Excel Model Structure
```text
Sheet 1 RATIOS: Sharpe, Sortino, Calmar, IR, Treynor, alpha for each period
Sheet 2 PEER_COMPARISON: portfolio ratios vs peer universe
Sheet 3 INTERPRETATION: what each ratio signals about skill vs luck
• The IPS is the contract between the investor and the investment process: without it, every market event
becomes an emotional decision.
• RRTTLLU produces completely different portfolios for different investor types from the same AUM —
framework first, allocation second.
• Markowitz optimisation is sensitive to expected return inputs: a small change in assumptions can produce
very different allocations.
• Character notes: Elena Fernandez (CIO, Sunrise University Endowment). Chairman Venkataraman. Rs.
3,000 crore. No IPS for 11 years.
```

</details>

---

