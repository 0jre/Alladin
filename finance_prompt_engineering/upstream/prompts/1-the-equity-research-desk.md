# 🏦 The Equity Research Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Benjamin Graham Margin of Safety & Net-Net Screen

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior value analyst applying Benjamin Graham's documented Security Analysis methodology.

Task:
Screen [N] stocks in [UNIVERSE] for deep value using Graham's documented criteria.
Graham Net-Net: Current Assets minus Total Liabilities vs Market Cap
Margin of Safety: minimum 33% discount to intrinsic value
Financial strength: current ratio >2x, long-term debt Earnings stability: positive EPS in
each of the last 10 years
Dividend record: uninterrupted payments for at least 20 years
P/E below 15x, P/Book below 1.5x, combined product <22.5
Graham Number = square root of (22.5 x EPS x Book Value Per Share)

Output Format:
Ranked list with Graham Number, margin of safety %, net-net value, one-line thesis.
Base Case Estimates only. Assumption log for top 3 names.
```

### 📊 Excel Model Structure
```text
Sheet 1 GRAHAM_SCREEN: ticker, Graham_Number, MoS_pct, net_net_value, P/E, P/Book
Sheet 2 WATCHLIST: names near threshold with specific gap to qualification
```

### 💡 Sample Output
```text
GRAHAM SCREEN | [DATE] | Universe: [N]
Passing: [X] of [N]
RANK | TICKER | GRAHAM NO. | MoS% | P/E | P/BK | THESIS
1 | [TKR] | [CUR][X] | 42% | 9.2x | 0.8x | [one line]
2 | [TKR] | [CUR][X] | 38% | 11x | 1.1x | [one line]
ASSUMPTION LOG: BCE = Graham Number adjusted for [X] margin of safety
```

</details>

---

## 🔹 The Peter Lynch PEG Ratio & GARP Discovery Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Growth-at-a-reasonable-price analyst applying Peter Lynch's documented GARP methodology.

Task:
Screen [UNIVERSE] for GARP opportunities using Lynch's documented framework.
PEG ratio: P/E divided by earnings growth rate. Target: PEG <1.0
Lynch categories: Stalwarts (8-12% growers), Fast Growers (20-25%), Turnarounds, Cyclicals
Hidden gems: small/mid-cap with <30% institutional ownership
Ten-bagger potential assessment: can this company grow 10x in 10 years?
Avoid: >60% institutional ownership (Lynch's 'overfollowed' warning)
Insider ownership: management skin in the game preferred

Output Format:
Categorised GARP list with PEG ratios, Lynch categories, and ten-bagger assessments.
```

### 📊 Excel Model Structure
```text
Sheet 1 GARP_SCREEN: ticker, Lynch_category, PEG, EPS_growth, inst_ownership_pct
Sheet 2 TEN_BAGGER_CANDIDATES: names with specific 10x mechanism documented
```

</details>

---

## 🔹 The Buffett Owner Earnings & Economic Moat Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Long-term quality investor applying Warren Buffett's documented owner earnings
methodology.

Task:
Evaluate [COMPANY] using Buffett's documented owner earnings and moat framework.
Owner Earnings = Net Income + D&A; - Maintenance Capex (Buffett 1986 annual letter)
Moat types: Brand, Cost advantage, Network effect, Switching cost
ROE consistently above 15% for 10 years without excessive leverage
ROIC above WACC sustained for 10 years
Pricing power: has the company raised prices without losing volume in 5 years?
Intrinsic value: 10-year owner earnings projection discounted at 9-10%

Output Format:
Owner earnings calculation, moat type, durability score, and intrinsic value range.
Base Case Estimates only.
```

### 📊 Excel Model Structure
```text
Sheet 1 OWNER_EARNINGS: 10yr net_income, D&A;, maint_capex, owner_earnings
Sheet 2 MOAT_SCORECARD: moat_type, evidence, durability_1to10
Sheet 3 INTRINSIC_VALUE: 10yr projection at base/bull/bear growth rates
```

</details>

---

## 🔹 The AQR Quality-Value-Momentum Multi-Factor Ranking

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst applying publicly documented multi-factor investing research.

Task:
Apply AQR's documented QVM multi-factor model to rank [UNIVERSE].
Quality factor (per AQR Asness et al. published research):
Profitability: gross profits/assets, ROE, ROA, cash flow/assets
Growth: 5yr growth in profitability measures
Safety: low beta, low leverage, high Altman Z-score
Value factor: book-to-market, earnings yield, cash flow yield
Momentum factor: 12-1 month return (excluding last month)
Composite: equal-weight Quality + Value + Momentum z-scores
Flag: stocks in top quintile of ALL three factors simultaneously

Output Format:
Factor scores, composite ranking, and triple-overlap identification.
```

### 📊 Excel Model Structure
```text
Sheet 1 FACTOR_SCORES: ticker, quality_z, value_z, momentum_z, composite_z, rank
Sheet 2 TRIPLE_OVERLAP: names in top quintile of all three factors
```

</details>

---

## 🔹 The Macro-Aware Equity Risk Premium & Valuation Framewo

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategist applying PIMCO's publicly documented macro-aware equity valuation
approach.

Task:
Assess the equity risk premium and relative value of [MARKET/SECTOR/COMPANY].
Equity Risk Premium calculation: earnings yield minus risk-free rate
Historical ERP: current vs 20-year average (is equity cheap or expensive vs bonds?)
Implied ERP from current market levels: back-solve from DCF
PIMCO's documented framework: secular outlook vs cyclical positioning
Real yield analysis: nominal yield minus inflation expectations
Cross-asset relative value: equities vs credit vs bonds vs commodities
Positioning recommendation: overweight / underweight equities vs bonds

Output Format:
ERP analysis with cross-asset relative value and positioning recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 ERP_ANALYSIS: date, earnings_yield, RF_rate, ERP, historical_avg, z_score
Sheet 2 RELATIVE_VALUE: asset_class, yield, real_yield, vs_history, recommendation
```

</details>

---

## 🔹 The Quantitative Pattern & Market Anomaly Detection Fra

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative researcher identifying statistically significant, economically-justified
patterns.

Task:
Identify statistically significant patterns for [TICKER] over [TIME PERIOD].
Seasonal patterns: best/worst calendar months with p-value and sample size
Earnings window: pre-announcement drift, post-earnings persistence, reversal
Macro event correlations: Fed meetings, CPI releases, index rebalancing
Short interest dynamics: squeeze potential via days-to-cover ratio
Institutional ownership trend: net buying/selling last 4 quarters
Statistical edge summary: highest p-value pattern with economic rationale
CRITICAL: every pattern must have an economic rationale, not just statistical significance

Output Format:
Pattern table with p-values, sample sizes, and economic rationale per pattern.
```

### 📊 Excel Model Structure
```text
Sheet 1 SEASONAL_PATTERNS: month, avg_return, p_value, sample_n, economic_reason
Sheet 2 EVENT_ANALYSIS: event_type, avg_return, p_value, tradeable
Sheet 3 EDGE_SUMMARY: pattern, p_value, n, edge_size, economic_rationale
```

</details>

---

## 🔹 The Macro-Driven Sector Rotation & Cycle Positioning Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief equity strategist with expertise in economic cycle analysis and sector allocation.

Task:
Optimal sector positioning for next 6-12 months given current macro environment.
Economic cycle stage: Early / Mid / Late expansion or Contraction
For each of the 11 GICS sectors:
Historical performance in current cycle stage
Current EV/EBITDA vs 5yr historical average (cheap or expensive?)
NTM EPS growth consensus estimate
Specific macro catalyst with timing estimate
Specific invalidating condition
Conviction: HIGH / MEDIUM / LOW
Recommend: 3 overweights, 2 underweights
My macro view: [DESCRIBE IN 2-3 SENTENCES]

Output Format:
Sector rotation brief. Overweight/underweight table with conviction levels.
```

### 📊 Excel Model Structure
```text
Sheet 1 ROTATION_TABLE: sector, OW_UW, current_mult, 5yr_avg, NTM_EPS, conviction
Sheet 2 CATALYST_TRACKER: sector, catalyst, timeline, invalidating_condition
```

</details>

---

## 🔹 The Buy-Side Full Due Diligence Research Note

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior buy-side equity analyst preparing a full IC package for a new position.

Task:
Full institutional due diligence on [COMPANY], [TICKER]. Ask Claude: 'Using the latest
publicly available financials for [COMPANY]:'
Business quality: revenue model, moat type, moat trajectory
Financial quality: Revenue CAGR 3yr, EBITDA margin, FCF conversion, leverage
Management: capital allocation track record, insider ownership, succession
Valuation: DCF with WACC + TGR sensitivity, EV/EBITDA vs peers, P/FCF vs history
Three 12-month catalysts with magnitude and probability each
Two bear cases: specific mechanistic path to loss, probability, magnitude
Position size: core 3-5%, standard 1-3%, watch <1%
Pre-mortem: most credible path to being wrong

Output Format:
IC-ready research note. Base Case Estimates only. Assumption log required.
```

### 📊 Excel Model Structure
```text
Sheet 1 FINANCIAL_MODEL: 5yr P&L;, FCF schedule (all with formulas)
Sheet 2 DCF_SENSITIVITY: WACC x TGR 3x3 grid (auto-calculating)
Sheet 3 PEER_COMPS: 6 peers, all multiples, target vs median
Sheet 4 ASSUMPTION_LOG: assumption, base, bull, bear, sensitivity_rating
```

### 💡 Sample Output
```text
DEEP DIVE | [COMPANY] ([TICKER]) | [DATE]
THESIS: [Company] trades at [X]% discount to intrinsic value because [SPECIFIC REASON].
[STRUCTURAL DRIVER] provides durable tailwind. Initiating [X]% [CORE/STANDARD].
BCE: [CUR][X] | Bull: [CUR][Y] | Bear: [CUR][Z]
ASSUMPTION LOG
1. Revenue growth [X]% — HIGH sensitivity
2. WACC [X]% (RF [X]%, ERP [X]%) — HIGH
3. TGR [X]% — MEDIUM
• Graham's margin of safety (minimum 33%) remains the most durable protection against analytical error in
any market environment.
• Lynch's PEG ratio unifies growth and value: a PEG below 1.0 means you are paying less than the growth
rate.
• Published factor research shows Quality + Value + Momentum combined outperforms any single factor
over long horizons.
• Statistical edges must have economic rationale — high p-value from small sample is noise, not signal.
• Character notes: Arjun Singh (Head of Research, Sterling Capital). Roshani Kapoor (CIO). 180 stocks, 11
minutes, 8 frameworks.
```

</details>

---

