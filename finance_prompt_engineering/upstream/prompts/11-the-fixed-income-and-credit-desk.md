# 🏦 The Fixed Income & Credit Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Institutional Yield Curve Positioning & Duration Ma

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior fixed income portfolio manager applying PIMCO's publicly documented rate strategy
framework.

Task:
Yield curve positioning recommendation for [FUND MANDATE] given current macro environment.
PIMCO documented approach (per PIMCO secular and cyclical outlooks):
Secular outlook: where are rates headed over 3-5 years?
Cyclical positioning: near-term tactical duration bet
Curve positioning: bullet vs barbell vs ladder for current environment
Real yield analysis: are real rates cheap or expensive?
Bullet vs barbell vs ladder: which structure and economic rationale
Duration target vs benchmark: active extension/reduction and why
Key rate duration decomposition: 2yr, 5yr, 10yr, 30yr allocation
Recommended trade: specific instruments to buy/sell/swap
Stress test: P&L; impact of 100bps parallel rise, 50bps steepening, 50bps flattening
My macro view: [DESCRIBE GROWTH AND INFLATION OUTLOOK]

Output Format:
Rate strategy brief with positioning recommendation and stress test table.
```

### 📊 Excel Model Structure
```text
Sheet 1 POSITIONING: maturity_bucket, current_duration, target, delta, instrument
Sheet 2 KRD_ANALYSIS: 2yr/5yr/10yr/30yr key rate durations, active vs benchmark
Sheet 3 STRESS_TEST: scenario, P&L;_per_bucket, total_portfolio_impact
```

### 💡 Sample Output
```text
YIELD CURVE STRATEGY | [DATE]
RECOMMENDED STRUCTURE: [BARBELL/BULLET/LADDER]
Rationale: [MACRO VIEW AND WHY THIS STRUCTURE FOLLOWS]
DURATION TARGET: [X]yr (vs benchmark [Y]yr, +/-[Z]yr active)
KRD: 2yr [X]% | 5yr [X]% | 10yr [X]% | 30yr [X]%
STRESS TEST
100bps parallel rise: [X]% | [CUR][Y] P&L;
50bps steepening: [X]% | [CUR][Y] P&L;
50bps flattening: [X]% | [CUR][Y] P&L;
```

</details>

---

## 🔹 The Buy-Side Credit Analysis & Investment Memo Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior credit analyst at an institutional fixed income manager.

Task:
Comprehensive credit memo for [ISSUER] for potential portfolio inclusion.
Annual report and latest quarterly uploaded.
BUSINESS QUALITY
Revenue predictability and customer concentration
Competitive position and barriers to entry
Key risks that could impair cash flow
FINANCIAL PROFILE (3yr trend)
Net Debt/EBITDA | EBITDA/Interest | FCF conversion
Liquidity: cash + undrawn revolver vs near-term maturities
DEBT STRUCTURE
Full maturity profile (flag any maturity walls)
Covenant package: incurrence vs maintenance vs covenant-lite
Security, ranking, structural protections
RATING ASSESSMENT
Current rating and outlook
Specific upgrade trigger | Specific downgrade trigger
RELATIVE VALUE
Z-spread vs comparable issuers
Assessment: tight / fair / cheap

Output Format:
Institutional credit memo. Recommendation: BUY/HOLD/AVOID with spread target.
```

### 📊 Excel Model Structure
```text
Sheet 1 CREDIT_METRICS: ratio, FY-2, FY-1, FY0, trend, limit_flag
Sheet 2 MATURITY_PROFILE: year, amount, type, refinancing_risk
Sheet 3 PEER_SPREADS: issuer, rating, spread, delta_to_subject
```

### 💡 Sample Output
```text
CREDIT MEMO | [ISSUER] [X]% Notes | [DATE]
BUSINESS: [X]% contracted revenue, [X]% retention. Risk: [SPECIFIC]
FINANCIALS
Net Debt/EBITDA: [X]x → [X]x → [X]x [improving/worsening]
EBITDA/Interest: [X]x | FCF conversion: [X]%
RELATIVE VALUE: Spread +[X]bps vs [RATING] peer median +[Y]bps ([WIDE/FAIR/TIGHT])
RECOMMENDATION: [BUY/HOLD/AVOID] at +[X]bps. Target: +[Y]bps (12M).
```

</details>

---

## 🔹 The Institutional Covenant Package & Creditor Protectio

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Credit analyst reviewing high-yield bond indentures for investor protection quality.

Task:
Covenant package assessment for [ISSUER] [AMOUNT] [COUPON]% Notes. Ask Claude: 'Find the
bond indenture or prospectus for [ISSUER] [COUPON]% Notes from public filings.'
Rate each covenant: STRONG / STANDARD / WEAK / RED FLAG
INCURRENCE COVENANTS
Debt incurrence: leverage test and threshold
Restricted payments: basket size and trigger
Asset sales: proceeds sweep requirement
MAINTENANCE COVENANTS
Explicitly state if NONE exist (covenant-lite = RED FLAG)
STRUCTURAL PROTECTIONS
Change of control: exact trigger and ALL carve-outs
Cross-default threshold
GROWER BASKETS
All mechanisms for additional debt outside leverage test
Calculate total capacity at current EBITDA
OVERALL ASSESSMENT vs market standard for this rating tier

Output Format:
Covenant table with overall creditor protection quality and spread premium recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 COVENANT_TABLE: type, threshold, rating, headroom, key_risk
Sheet 2 BASKET_ANALYSIS: basket_name, fixed_amount, grower_formula, total_capacity
Sheet 3 PEER_COMPARISON: issuer, maintenance_covs, incurrence_test, overall_rating
```

### 💡 Sample Output
```text
COVENANT ANALYSIS | [ISSUER] Notes | [DATE]
Covenant | Rating | Threshold | Key Risk
Debt Incurrence | STANDARD | [X]x Net Lev | [headroom]bps
Restricted Payments | WEAK | [CUR][X] basket | Large, fully available
Maintenance Covenants | RED FLAG | NONE (cov-lite) | Primary creditor risk
GROWER BASKETS: [CUR][X] fixed + [X]% EBITDA = [CUR][Y] total capacity
OVERALL: [BELOW] market standard for [RATING] tier
Spread premium required: +[X]-[Y]bps vs covenanted peers
```

</details>

---

## 🔹 The Distressed Credit Recovery Analysis & Fulcrum Secur

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior distressed credit analyst specialising in recovery analysis and restructuring.

Task:
Recovery waterfall analysis for [COMPANY] in financial distress.
Enterprise value scenarios:
Bear case: [CUR][X] (liquidation value)
Base case: [CUR][X] (going concern, [X]x EBITDA)
Bull case: [CUR][X] (strategic value, [X]x EBITDA)
Capital structure:
Senior secured: [CUR][X] | Senior unsecured: [CUR][X] | Sub: [CUR][X]
Recovery per class at each EV scenario:
Quantify: cents per dollar recovery per class
Flag: fulcrum security (class that gets equity in restructuring)
Trading recommendation: which securities offer best risk-adjusted recovery?
Catalyst: what would move EV toward bull case and by when?

Output Format:
Recovery waterfall with fulcrum security identification and trading recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 WATERFALL: EV_scenario, each_class_recovery_cents, fulcrum_flag
Sheet 2 FULCRUM_ANALYSIS: class, at_which_EV_fulcrum, implied_equity_value
Sheet 3 TRADING_REC: instrument, current_price, recovery_range, risk_reward
```

</details>

---

## 🔹 The Institutional Credit Universe Relative Value & Spre

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior credit portfolio manager screening a credit universe for relative value
opportunities.

Task:
Credit universe relative value screen for [SECTOR/RATING CATEGORY].
For each issuer in the universe:
Current Z-spread or OAS
Sector median spread for same rating
Issuer spread vs sector median: WIDE / FAIR / TIGHT
Spread vs 6-month and 12-month history (Z-score)
Credit trend: improving / stable / deteriorating
Liquidity: bid-ask spread, daily trading volume
Catalyst for spread compression (if WIDE): what drives tightening?
Best ideas: top 5 WIDE names with improving credit trend
Avoid: top 5 TIGHT names with deteriorating credit

Output Format:
Relative value screen with WIDE/FAIR/TIGHT classification and best ideas.
```

### 📊 Excel Model Structure
```text
Sheet 1 RV_SCREEN: issuer, rating, spread, sector_median, vs_median, credit_trend, signal
Sheet 2 BEST_IDEAS: WIDE names, improvement catalyst, target_spread, timeline
Sheet 3 AVOID_LIST: TIGHT names, deterioration risk, exit_trigger
```

</details>

---

## 🔹 The Credit Spread Decomposition & Risk Premium Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior credit analyst specialising in credit spread analysis and risk premium
decomposition.

Task:
Credit spread analysis for [ISSUER] [SECURITY].
Spread decomposition:
Expected default loss: probability of default x loss given default
Risk premium: compensation for uncertainty/volatility of default
Liquidity premium: compensation for illiquidity vs comparable liquid security
Residual: unexplained spread (opportunity or red flag?)
Current spread vs fair value: is the issuer cheap or expensive on fundamentals?
Spread drivers: what would cause spread to tighten or widen?
Historical spread Z-score: current spread vs [N]-year history
Cross-currency analysis: USD vs EUR spread for same issuer (arbitrage?)
Recommendation: BUY / HOLD / SELL with target spread

Output Format:
Spread decomposition with fair value assessment and recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 SPREAD_DECOMP: component, basis_points, methodology, confidence
Sheet 2 SPREAD_HISTORY: date, spread, Z_score, context (current in red)
Sheet 3 DRIVER_ANALYSIS: driver, current_impact, scenario_impact
```

</details>

---

## 🔹 The Fixed Income Cross-Sector & Curve Relative Value Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior fixed income analyst specialising in cross-sector and cross-curve relative value.

Task:
Bond relative value analysis for [BOND/SECTOR] vs alternatives.
Cross-sector relative value:
IG corporate vs government: spread vs historical, is compensation fair?
HY vs IG: excess spread per unit of default risk
EM sovereign vs IG corporate: is EM sovereign premium or discount justified?
Financials vs industrials: sector spread differential and rationale
Curve relative value:
Short-end vs long-end: carry and roll-down analysis
Bullet vs callable: option-adjusted spread comparison
On-the-run vs off-the-run: liquidity premium
Recommendations: top 3 relative value switches with rationale

Output Format:
Relative value matrix with cross-sector and cross-curve recommendations.
```

### 📊 Excel Model Structure
```text
Sheet 1 CROSS_SECTOR_RV: sector_pair, spread_differential, historical_avg, signal
Sheet 2 CURVE_RV: maturity_pair, carry, roll_down, total_return, recommendation
Sheet 3 SWITCH_RECOMMENDATIONS: from, to, rationale, spread_pickup, risk
```

</details>

---

## 🔹 The Institutional Investment Grade Bond Portfolio Const

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior fixed income portfolio manager constructing an institutional bond portfolio.

Task:
Construct an institutional bond portfolio for [MANDATE].
Portfolio objectives: [YIELD TARGET], [DURATION TARGET], [CREDIT QUALITY MINIMUM]
Asset class allocation:
Government bonds: % and purpose (duration anchor, liquidity)
Investment grade corporate: % by sector and rating (A, BBB)
High yield: % and rationale (yield enhancement within risk budget)
Securitised (ABS/MBS): % and type
EM debt (if applicable): % and currency hedge
Diversification: maximum per issuer [X]%, per sector [X]%, per country [X]%
Duration construction: how to achieve target duration across the curve
Liquidity reserve: minimum % in government bonds for redemption management

Output Format:
Bond portfolio blueprint with asset class allocation and duration construction.
```

### 📊 Excel Model Structure
```text
Sheet 1 PORTFOLIO_CONSTRUCTION: asset_class, pct, duration_contribution,
yield_contribution
Sheet 2 ISSUER_LIMITS: issuer, max_pct, current_pct, headroom
Sheet 3 DURATION_CONSTRUCTION: maturity_bucket, target_duration, instruments
• The yield curve positioning decision is worth 80-120 basis points of tracking error annually — it is the most
impactful fixed income decision.
• Covenant analysis: maintenance covenants offer active protection. Incurrence covenants offer passive
protection. Covenant-lite = no maintenance = RED FLAG.
• The fulcrum security (the class that gets equity in restructuring) is the most valuable position in distressed
investing.
• Credit relative value screen: WIDE + IMPROVING CREDIT TREND = best risk-adjusted opportunity in any
credit universe.
• Character notes: Nalini Krishnaswami (Credit Analyst, ICICI Prudential AMC). Page 94 of 148. Grower
basket. Covenant-lite. Eight credit prompts.
```

</details>

---

