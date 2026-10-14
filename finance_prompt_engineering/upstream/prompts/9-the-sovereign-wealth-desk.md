# 🏦 The Sovereign Wealth Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The NBIM Norway Government Pension Fund Global Investme

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
CIO of a commodity-funded sovereign wealth fund applying NBIM/Norway GPFG documented
principles.

Task:
Design a strategic asset allocation applying Norway GPFG/NBIM documented framework.
AUM: [CUR][X] | Mandate: intergenerational preservation + [X]% annual withdrawal
NBIM documented principles (per NBIM annual reports and Norwegian government white
papers):
Zero home-country equity bias (oil economy holds oil risk through GDP)
Passive equity core (low cost, transparent, scalable)
Responsible investment at scale (ESG integration, engagement, exclusions)
Long investment horizon (patient capital, illiquidity tolerance)
Transparency and accountability to Norwegian public
SAA: global equity/bonds/real estate/infrastructure with rationale
Currency policy: hedge or not? At this scale?
NBIM vs CPPIB Canada model comparison for this mandate

Output Format:
NBIM-style SAA with home-country rationale and Norway vs Canada comparison.
```

### 📊 Excel Model Structure
```text
Sheet 1 SAA: class, target_pct, benchmark, rationale
Sheet 2 HOME_COUNTRY_ANALYSIS: economic_argument, recommended_exposure
Sheet 3 NBIM_VS_CPPIB: expected_return, cost, governance, scale_threshold
```

### 💡 Sample Output
```text
NBIM FRAMEWORK | [DATE] | [CUR][X] AUM
SAA
Global Equity: [X]% | Fixed Income: [X]% | Real Estate: [X]% | Infrastructure: [X]%
HOME COUNTRY: [ZERO / LIMITED TO X%]
Rationale: Commodity economy holds oil risk through GDP. Fund purpose: diversify away.
NBIM vs CPPIB: Norway passive [X]bps vs Canada direct [X]bps
Scale threshold for CPPIB viability: [CUR][X] minimum
```

</details>

---

## 🔹 The CPPIB Canada Pension Plan Total Portfolio Approach

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
CIO applying CPPIB Canada Pension Plan's publicly documented total portfolio approach.

Task:
Apply CPPIB's documented total portfolio approach to [MANDATE].
CPPIB documented principles (per CPP Investments annual reports):
Total portfolio approach: all assets evaluated for absolute and relative contribution
Internal management: build in-house expertise vs external managers
Direct investing: own assets directly vs fund exposure
Leverage within fixed income: amplify return without adding equity risk
Long-horizon orientation: perpetual capital, illiquidity tolerance
Reference portfolio: simple passive benchmark for governance comparison
vs Norway model: when does Canada approach add value?
AUM requirement: minimum scale for Canada model to be cost-effective
My mandate: [AUM], [HORIZON], [GOVERNANCE CAPACITY]

Output Format:
CPPIB-style framework with total portfolio approach and scale analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 TOTAL_PORTFOLIO: asset_class, absolute_contribution, relative_to_ref_portfolio
Sheet 2 BUILD_VS_BUY: activity, internal_cost, external_cost, break_even_AUM
Sheet 3 REFERENCE_PORTFOLIO: passive_benchmark, performance_vs_reference, value_added
```

### 💡 Sample Output
```text
AI advanced reasoning model
```

</details>

---

## 🔹 The Liability-Driven Investing & Glidepath Design Frame

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
CIO of a defined benefit pension fund designing an LDI strategy.

Task:
LDI transition plan for [MANDATE].
Fund: Assets [CUR][X] | Liabilities PV [CUR][X] | Funding ratio [X]%
Asset duration [X]yr | Liability duration [X]yr | Plan: [open/closed/frozen]
Duration mismatch: funded status at risk per 100bps rate decline (in currency terms)
Liability-hedging portfolio: instruments (physical bonds vs swaps), target duration
Return-seeking portfolio: asset classes with rationale
Trigger-based glidepath: allocation at each funded ratio milestone
Governance: IC approval timeline per trigger level
End-state: conditions for bulk annuity buy-out consideration

Output Format:
LDI plan with glidepath table and funded status stress test.
```

### 📊 Excel Model Structure
```text
Sheet 1 LDI_GLIDEPATH: FR_trigger, equity_pct, LHP_pct, alts_pct, hedge_ratio
Sheet 2 STRESS_TEST: rate_scenarios, funded_status_impact in currency
Sheet 3 INSTRUMENT_SCHEDULE: instrument, duration_contribution, notional, cost
```

### 💡 Sample Output
```text
LDI PLAN | [DATE] | [CUR][X] DB Pension
DURATION GAP
Assets [X]yr | Liabilities [Y]yr | GAP: [Z]yr
[X]bps rate fall: Assets +[CUR][A] | Liabilities +[CUR][B] | Net: -[CUR][C]
GLIDEPATH
FR | Equities | LHP | Alts | Hedge %
<[X]% | [A]% | [B]% | [C]% | [D]%
[X-Y]% | [A]% | [B]% | [C]% | [D]%
>[Y]% | Buy-out consideration
```

</details>

---

## 🔹 The Solvency II Asset-Liability Management & SCR Optimi

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief Investment Officer of a Solvency II-regulated insurance company.

Task:
Solvency II ALM framework for [INSURANCE COMPANY].
Liability profile: [ANNUITIES / LIFE / PROPERTY] | Duration [X]yr | [CUR][X] reserves
Matching Adjustment analysis (if applicable to annuity book):
MA-eligible assets: qualifying criteria (fixed cash flows, no optionality)
MA spread benefit: credit spread minus fundamental spread = MA benefit
Impact on Solvency II ratio: MA vs without MA
SCR optimisation:
Equity SCR: 39% charge. Diversification benefit with bonds?
Credit SCR: spread duration x notional
Property SCR: 25% charge
Asset classes ranked by: yield / SCR capital charge
Target Solvency II ratio: [X]% | Current: [X]% | Headroom: [X]pp

Output Format:
Solvency II ALM framework with SCR analysis and MA benefit quantification.
```

### 📊 Excel Model Structure
```text
Sheet 1 ALM_FRAMEWORK: asset_class, yield, SCR_charge, yield_per_SCR_unit
Sheet 2 MA_ANALYSIS: MA_eligible_portfolio, credit_spread, fundamental_spread, MA_benefit
Sheet 3 SCR_OPTIMISATION: scenario, solvency_ratio, impact_of_changes
```

### 💡 Sample Output
```text
AI advanced reasoning model
```

</details>

---

## 🔹 The GIC Singapore Sovereign Wealth Fund Investment Appr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategist applying GIC Singapore's publicly documented long-term investment
framework.

Task:
Apply GIC's documented investment framework to [MANDATE].
GIC documented principles (per GIC annual reports):
Long investment horizon: 20-year return focus
Diversification as primary risk management tool
Active management in less efficient markets
Total portfolio return: real return above global inflation
Singapore-specific constraint: cannot invest in Singapore assets (conflict of interest)
GIC's documented risk framework: Policy Portfolio as benchmark
Target real return vs actual: GIC publishes 5yr, 10yr, 20yr rolling returns
Asset class allocation: public equity, fixed income, real estate, PE, infrastructure
My mandate: [AUM], [RETURN TARGET], [CONSTRAINTS]

Output Format:
GIC-style framework with long-horizon SAA and real return analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 GIC_SAA: asset_class, target_pct, expected_real_return, rationale
Sheet 2 REAL_RETURN_ANALYSIS: nominal, inflation, real_return by period
Sheet 3 POLICY_PORTFOLIO: reference_benchmark, actual_vs_benchmark
```

</details>

---

## 🔹 The Temasek Holdings Portfolio Construction Approach

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategist applying Temasek's publicly documented investment framework.

Task:
Apply Temasek's documented framework to [MANDATE].
Temasek documented principles (per Temasek Review annual publication):
Transformation: invest in businesses being transformed by technology and trends
Growth: concentrate in high-growth sectors and geographies
Resilience: balance sheets and business models built for resilience
Embedded liquidity: [X]% of portfolio in highly liquid assets
Net portfolio value vs intrinsic value: how Temasek measures performance
Wealth Added metric: total returns minus opportunity cost of capital
Concentration vs diversification: Temasek's willingness to hold large positions
Active vs passive: Temasek's direct portfolio company involvement
My mandate: [DESCRIBE]

Output Format:
Temasek-style framework with transformation focus and wealth added analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 TEMASEK_SAA: theme, sector, target_pct, transformation_thesis
Sheet 2 WEALTH_ADDED: return, opportunity_cost, wealth_added by period
Sheet 3 RESILIENCE_CHECK: position, liquidity, balance_sheet_score
```

</details>

---

## 🔹 The Institutional Private Equity Fund Due Diligence Fra

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of alternatives at an institutional investor evaluating a PE fund commitment.

Task:
DD memo for [CUR][X] commitment to [FUND NAME] [FUND NUMBER].
Fund: Strategy [DESCRIBE] | AUM [CUR][X] | Prior fund: [X]x DPI, [X]x TVPI, [X]% net IRR
Fees: [X]% management / [X]% carry | GP commit: [X]%
Track record quality: is performance repeatable? Deal-level attribution needed?
Team stability: key person risk assessment
Fund size scaling: can strategy absorb more capital at same returns?
Fee terms: market standard or negotiating opportunity?
Co-investment: availability and estimated annual flow
Recommendation: INVEST / PASS / CONDITIONAL with specific conditions

Output Format:
PE DD memo with track record analysis and recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 DD_SCORECARD: dimension, assessment, score_1to10, concern, data_request
Sheet 2 RETURNS_BENCHMARK: vintage, fund_IRR, quartile_cutoffs, percentile
Sheet 3 FEE_ANALYSIS: fee_type, amount, market_standard, negotiation_point
```

</details>

---

## 🔹 The Multi-Generational Family Office Investment Policy

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief investment officer of a multi-generational family office.

Task:
Investment Policy Statement for [FAMILY OFFICE].
Family overview: generations, AUM [CUR][X], operating businesses, philanthropy goals
RRTTLLU for family context:
Return: preserving purchasing power across generations
Risk: family dynamics, concentration in operating business
Time: multi-generational (50+ years)
Tax: estate planning, jurisdiction optimisation
Liquidity: current generation needs vs long-term preservation
Legal: family governance structure, trusts, foundation
Unique: operating business concentration risk, family values
Portfolio separation: liquidity portfolio vs growth portfolio vs legacy
Governance: family investment committee, next generation education

Output Format:
Family office IPS with multi-generational framework and governance structure.
```

### 📊 Excel Model Structure
```text
Sheet 1 FO_SAA: portfolio_tranche, asset_class, target_pct, purpose
Sheet 2 GOVERNANCE: body, members, authority, meeting_frequency
Sheet 3 NEXT_GEN: education_programme, involvement_roadmap, succession
• NBIM's zero home-country exposure has a specific economic rationale: a commodity economy already
holds oil risk through its GDP.
• CPPIB's total portfolio approach evaluates all assets for their absolute AND relative contribution to portfolio
objectives.
• The DB pension duration gap (in currency terms) is the single most important risk metric for any trustee to
understand.
• Character notes: Vikram Nair (Head of Institutional Strategy, HSBC AM India). CFA Society India
conference. Gulf sovereign fund delegates.
```

</details>

---

