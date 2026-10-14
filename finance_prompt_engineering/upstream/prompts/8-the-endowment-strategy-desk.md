# 🏦 The Endowment Strategy Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The David Swensen Yale Endowment Investment Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief investment strategist applying David Swensen's documented Yale Endowment Model
framework.

Task:
Apply Swensen's documented Yale Endowment Model to [PORTFOLIO/MANDATE].
Swensen's documented asset allocation framework (from Pioneering Portfolio Management):
Domestic equity: core for liquidity and return
Foreign developed equity: diversification + return
Emerging markets: higher return + higher risk
Real assets: inflation protection + return
Private equity: illiquidity premium capture
Absolute return: uncorrelated diversification
Illiquidity premium: quantify expected extra return from illiquid alternatives
Spending policy: [X]% spending rule analysis (sustainable for perpetual horizon?)
Governance: required capabilities for private equity and hedge fund allocation
My mandate: [INVESTOR TYPE], [AUM], [HORIZON], [UNIQUE CONSTRAINTS]

Output Format:
Yale-style SAA with illiquidity premium analysis and spending policy.
```

### 📊 Excel Model Structure
```text
Sheet 1 YALE_SAA: asset_class, target_pct, illiquidity_premium, rationale
Sheet 2 SPENDING_POLICY: spending_rate, projected_sustainability, sensitivity
Sheet 3 GOVERNANCE_REQUIREMENTS: capability, current_state, gap, action
```

### 💡 Sample Output
```text
YALE MODEL APPLICATION | [DATE]
SWENSEN SAA
Domestic Equity: [X]% | Foreign Dev: [X]% | EM: [X]%
Real Assets: [X]% | Private Equity: [X]% | Abs Return: [X]%
ILLIQUIDITY PREMIUM: +[X]% expected annual return from PE/RE vs public markets
SPENDING POLICY: [X]% sustainable at [X]% expected return for perpetual horizon
```

</details>

---

## 🔹 The Harvard Management Company Endowment Investment Fra

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior endowment manager applying the Harvard Management Company's documented framework.

Task:
Apply HMC's documented endowment framework to [MANDATE].
HMC documented principles (per HMC annual reports):
Genuine diversification: not just asset class labels
Long investment horizon: ability to capture illiquidity premium
Countercyclical rebalancing: add risk in down markets
Sustainable spending: balance current beneficiaries vs future generations
Real return analysis: nominal return minus spending minus inflation
Intergenerational equity: are we protecting purchasing power for future generations?
Risk budget: total portfolio risk tolerance and allocation across asset classes
Peer benchmarking: vs Cambridge endowment universe percentiles
My mandate: [DESCRIBE]

Output Format:
HMC-style endowment framework with real return analysis and intergenerational equity.
```

### 📊 Excel Model Structure
```text
Sheet 1 REAL_RETURN: nominal_return, spending, inflation, real_return by year
Sheet 2 INTERGENERATIONAL: spending_vs_growth, purchasing_power_preservation
Sheet 3 RISK_BUDGET: risk_allocation by asset class, total portfolio VaR
```

</details>

---

## 🔹 The Endowment-Style Dividend Safety & Sustainability Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief income strategist applying Swensen's sustainability-first income framework.

Task:
Build a dividend income portfolio for [CLIENT].
Situation: [AMOUNT], [INCOME GOAL], [ACCOUNT TYPE], [TAX BRACKET], [HORIZON]
Swensen principle: sustainability first, growth second, yield third.
Safety filter: payout ratio <[X]%, FCF coverage >[X]x, debt <[X]x EBITDA
Growth filter: DGR >[X]%/yr (5yr), consecutive growth streak >[X] years
Yield filter: target [X]-[X]%. Flag any >[X]% for dividend trap analysis.
Diversification: max [X]% per sector
15-20 picks with safety score 1-10, payout ratio, 5yr DGR
Monthly income projection and 10yr DRIP compounding illustration

Output Format:
Income portfolio with safety scores, income projection, and DRIP simulation.
```

### 📊 Excel Model Structure
```text
Sheet 1 PORTFOLIO: ticker, yield, safety_score, growth_years, payout, DGR, flag
Sheet 2 INCOME_PROJECTION: year, annual, monthly, cumulative
Sheet 3 DRIP_SIMULATION: year, portfolio_value, income, reinvested
Sheet 4 SAFETY_SCORES: flagged_names with specific risk factors
```

### 💡 Sample Output
```text
INCOME PORTFOLIO | [CUR][X] | [DATE]
Blended yield: [X]% | Annual: [CUR][X] | Monthly: [CUR][X]
TOP HOLDINGS (Safety ≥7)
Ticker | Yield | Safety | Yrs | Payout | DGR
DIVIDEND TRAPS FLAGGED: [TICKER] Safety [N], Payout [X]%, FCF [X]x
INCOME PROJECTION ([X]% avg DGR + DRIP)
Year 1: [CUR][X] | Year 5: [CUR][X] | Year 10: [CUR][X]
```

</details>

---

## 🔹 The Dividend Reinvestment & Compound Growth Projection

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior wealth strategist specialising in DRIP compounding projections for income
portfolios.

Task:
DRIP compounding analysis for [PORTFOLIO] over [N] years.
Starting portfolio: [CUR][X] | Blended yield: [X]% | DGR assumption: [X]%
Year-by-year projection:
Dividend income received
Shares purchased via DRIP at assumed price
Cumulative shares and portfolio value
Income on income effect: compound dividend growth
Comparison: DRIP vs spending vs partial reinvestment (50%)
Break-even analysis: at what DGR does DRIP beat a static bond yield of [X]%?
Tax implications: DRIP tax treatment in [ACCOUNT TYPE]
Sensitivity: what happens if DGR is [X]% vs [Y]% vs [Z]%?

Output Format:
DRIP compounding projection with scenario comparison.
```

### 📊 Excel Model Structure
```text
Sheet 1 DRIP_PROJECTION: year, income, reinvested, shares, portfolio_value
Sheet 2 SCENARIO_COMPARISON: DRIP vs spending vs partial at 5/10/20yr
Sheet 3 DGR_SENSITIVITY: portfolio_value and income at low/base/high DGR
```

</details>

---

## 🔹 The Institutional Spending Policy & Intergenerational E

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief investment officer designing a sustainable spending policy for a perpetual mandate.

Task:
Design a sustainable spending policy for [ENDOWMENT/FOUNDATION].
Spending rule options:
Simple percentage: [X]% of end-of-year portfolio value (volatile)
Smoothing rule: [X]% of trailing [N]-year average (reduces volatility)
Inflation-adjusted: prior year spend + CPI (preserves purchasing power)
Hybrid: [X] x prior year spending + [Y] x [Z]% of market value
Sustainability analysis: at what spending rate does purchasing power decline over 50
years?
Intergenerational equity: is the current generation spending more or less than future?
Stress test: what happens to spending under each scenario if portfolio falls [X]%?
Governance: what triggers a spending rate review?

Output Format:
Spending policy comparison with sustainability analysis and governance framework.
```

### 📊 Excel Model Structure
```text
Sheet 1 SPENDING_COMPARISON: rule, year_1, year_5, year_10, volatility, sustainability
Sheet 2 SUSTAINABILITY: spending_rate, real_return_needed, probability_of_perpetuity
Sheet 3 STRESS_TEST: portfolio_scenario, spending_impact per rule
```

</details>

---

## 🔹 The Endowment-Style Alternatives & Illiquidity Premium

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior alternatives allocator designing illiquid asset exposure for institutional mandate.

Task:
Alternatives allocation framework for [MANDATE] with [X]% alternatives target.
Illiquidity premium: expected excess return from each alternative asset class
Private equity: [X]% premium over public equity (document evidence)
Private credit: [X]% premium over public credit
Real estate: [X]% premium over REITs
Infrastructure: [X]% premium over listed infrastructure
Access requirements: minimum commitments, GP relationships, vintage diversification
J-curve management: cash flow profile in years 1-5 for PE commitments
Liquidity management: matching illiquid exposure to long-term liabilities
Governance: required capabilities before expanding alternatives exposure

Output Format:
Alternatives allocation with illiquidity premium analysis and governance requirements.
```

### 📊 Excel Model Structure
```text
Sheet 1 ALTERNATIVES_ALLOCATION: class, target_pct, illiquidity_premium, evidence
Sheet 2 CASHFLOW_PROFILE: J_curve by year for PE commitment schedule
Sheet 3 GOVERNANCE_CHECKLIST: required capability, current state, gap
```

</details>

---

## 🔹 The Multi-Period Income Ladder & Cash Flow Management F

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior income strategist constructing a systematic income ladder for retirement
portfolios.

Task:
Income ladder for [CLIENT] needing [CUR][X] per year for [N] years.
Ladder structure: [N] tranches, one per year or tranche period
Tranche 1 ([0-2 years]): highest liquidity, low risk (money market, short bonds)
Tranche 2 ([3-5 years]): intermediate risk (investment grade bonds, dividend stocks)
Tranche 3 ([6-10 years]): growth-oriented (equities, REITs for long-term income)
Tranche 4 ([10+ years]): illiquid/growth (alternatives, endowment approach)
Refilling mechanism: how is Tranche 1 replenished from Tranche 3?
Sequence of returns risk: how does the ladder protect against early retirement losses?

Output Format:
Income ladder with tranche allocation and refilling mechanism.
```

### 📊 Excel Model Structure
```text
Sheet 1 INCOME_LADDER: tranche, years, allocation, instruments, yield, refill_source
Sheet 2 CASHFLOW_PROJECTION: year, income_need, tranche_source, portfolio_value
Sheet 3 SEQUENCE_RISK: scenario, portfolio_impact, income_sustainability
```

</details>

---

## 🔹 The Institutional Legacy Planning & Inter-Generational

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior wealth strategist specialising in legacy planning and inter-generational wealth
transfer.

Task:
Legacy and estate planning framework for [CLIENT].
Estate overview: total assets, structure, beneficiaries, timeline
Tax efficiency: estate tax implications in [JURISDICTION]
Charitable giving: donor-advised funds, charitable trusts, foundations
Trust structures: revocable vs irrevocable, dynasty trusts
Investment policy for inheritors: RRTTLLU for beneficiaries' situation
Governance: family investment committee, education for next generation
Risk: family dynamics, concentration risk, succession of governance
Legacy portfolio vs consumption portfolio: different investment approaches

Output Format:
Legacy planning framework with tax efficiency and governance structure.
```

### 📊 Excel Model Structure
```text
Sheet 1 ESTATE_OVERVIEW: asset, value, structure, beneficiary, tax_implication
Sheet 2 CHARITABLE_GIVING: vehicle, amount, tax_benefit, timeline
Sheet 3 GOVERNANCE_FRAMEWORK: structure, roles, investment_policy, succession
• Swensen's documented principle: sustainability first, growth second, yield third. High yield without safety is
capital erosion.
• The illiquidity premium in private equity and real assets is documented by Swensen, HMC, and academic
research as 2-4% annually.
• DRIP compounding: a 3.5% yield growing at 8% annually beats a static 6% yield in total income received
within 5 years.
• Character notes: Dr. Rajesh Nair (retired surgeon, Kochi). Suman Rao (financial planner). Rs. 4.5 crore.
7.8% yield trap vs 4.0% sustainable income.
```

</details>

---

