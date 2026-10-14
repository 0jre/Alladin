# 🏦 The M&A; Valuation Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Institutional Buy-Side DCF Valuation Model

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
VP-level investment banker building valuation models for institutional M&A; transactions.

Task:
Build a complete DCF for [COMPANY], [TICKER]. Ask Claude: 'Using the latest publicly
available financials for [COMPANY]:'
Five-year revenue projections by segment with growth driver commentary (cite sources).
Operating margin build: gross margin trend, SG&A; leverage, EBITDA bridge.
FCF schedule: NOPAT, D&A;, capex, NWC change by year with formulas.
WACC: RF rate (source and date), ERP, beta derivation, cost of debt, weights.
Terminal value: Gordon Growth Model AND EV/EBITDA exit multiple — average both.
3x3 sensitivity: WACC (low/mid/high) x TGR (low/mid/high). BCE per cell.
Equity bridge: enterprise value to equity value to per-share BCE.
Base / bull / bear scenarios with specific assumption differences.

Output Format:
Investment banking valuation memo. Source every key assumption. BCE only.
```

### 📊 Excel Model Structure
```text
Sheet 1 DCF_MODEL: revenue, EBIT, NOPAT, D&A;, Capex, NWC, FCF (all formulas)
Sheet 2 WACC_BUILD: RF, ERP, beta, Ke, Kd, weights, WACC
Sheet 3 SENSITIVITY: 3x3 WACC x TGR grid (auto-calculating)
Sheet 4 SCENARIOS: base/bull/bear assumptions with BCE
```

### 💡 Sample Output
```text
DCF MEMO | [COMPANY] | [DATE]
WACC: RF [X]% ([source, date]) | ERP [X]% | Beta [X] | WACC [X]%
SENSITIVITY (BCE [CURRENCY]/share)
WACC \ TGR | [low] | [mid] | [high]
[low] | [X] | [X] | [X]
[mid] | [X] | →[X]← | [X] BASE
[high] | [X] | [X] | [X]
BCE: [CUR][X] | Bull: [CUR][Y] | Bear: [CUR][Z]
```

</details>

---

## 🔹 The Institutional Cost of Capital Construction Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior financial analyst specialising in defensible WACC estimation for M&A.;

Task:
Build a fully sourced WACC for [COMPANY] in [COUNTRY/MARKET].
Risk-free rate: current government bond yield — exact source and date
ERP: Damodaran's current country ERP (state date accessed)
Beta: regression vs [INDEX] over [N] years, state R-squared
Cost of debt: current market yield or credit spread + RF
Capital structure: market-value weights (not book value)
Tax rate: effective rate, trailing 3yr average
Sensitivity: WACC at +/- 100bps RF and +/- 0.2 beta

Output Format:
WACC table with every component sourced. Sensitivity analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 WACC_BUILD: component, value, source, date, methodology_note
Sheet 2 BETA_REGRESSION: returns, index, regression output, R-squared
Sheet 3 WACC_SENSITIVITY: WACC at RF +/-100bps and beta +/-0.2
```

### 💡 Sample Output
```text
WACC BUILD | [COMPANY] | [DATE]
RF: [X]% ([source] [date]) | ERP: [X]% (Damodaran) | Beta: [X] (R2=[X])
Ke: [X]% | Kd after-tax: [X]% | WACC: [X]%
```

</details>

---

## 🔹 The Institutional Peer Group Valuation Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior equity analyst building a fully sourced peer group valuation cross-check.

Task:
Comparable company analysis for [TARGET] vs [N]-company peer group.
Peer selection criteria: state inclusion/exclusion rationale
Trading multiples: EV/Revenue NTM, EV/EBITDA NTM, P/E NTM, P/FCF
Growth metrics: NTM revenue growth, EBITDA margin, FCF yield, ROIC
Statistics: median, mean, 25th and 75th percentile
Target vs peers: premium/discount on every metric with assessment
Implied valuation range at peer median, mean, and percentiles

Output Format:
Comps table with implied valuation range and premium/discount analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 COMPS_TABLE: peers, EV/Rev, EV/EBITDA, P/E, P/FCF, growth, margins
Sheet 2 IMPLIED_VALUATION: target BCE at peer min/25th/median/75th/max
Sheet 3 PREMIUM_DISCOUNT: target vs each peer with delta
```

</details>

---

## 🔹 The Private Equity Leveraged Buyout Returns Analysis

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
PE analyst building returns analysis for a sponsor acquisition with co-investor.

Task:
Complete LBO analysis for [COMPANY].
Entry EV/EBITDA: [X]-[X]x in [N] levels | Hold: [N] years
Exit EV/EBITDA: [X]-[X]x in [N] levels
Financing: [X]% senior, [X]% mezz, [X]% equity
EBITDA growth: [X]%/yr base | [X]% bull | [X]% bear
Returns matrix: IRR and MOIC at each entry/exit combination
Maximum leverage for [X]% IRR hurdle
DSCR by year (flag any year below [X]x)
Equity bridge at exit with GP carry calculation

Output Format:
Returns matrix as primary output with DSCR table.
```

### 📊 Excel Model Structure
```text
Sheet 1 LBO_MODEL: sources/uses, P&L;, debt schedule, equity bridge
Sheet 2 RETURNS_MATRIX: IRR/MOIC grid (auto-calculating)
Sheet 3 DEBT_SCHEDULE: amortisation, cash sweep, DSCR by year
```

### 💡 Sample Output
```text
LBO | [COMPANY] | [DATE]
RETURNS MATRIX (IRR)
Entry \ Exit | [X]x | [Y]x | [Z]x
[A]x | [I]% | [J]% | [K]%
[B]x | [I]% |[J]%I| [K]% BASE
BASE: IRR [X]% | MOIC [X]x | DSCR min Yr[X]: [X]x
```

</details>

---

## 🔹 The M&A; Control Premium & Transaction Multiple Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior M&A; banker building precedent transaction analysis for fairness opinions.

Task:
Precedent transactions for [SECTOR], last [N] years, deal >[CUR][X].
For each: acquirer, target, date, EV, EV/EBITDA, EV/Revenue, control premium
Control premium: premium to unaffected price (1-day, 30-day)
Strategic vs financial buyer: premium difference quantified
Trend: has transaction multiple been rising or falling over the period?
Implied range for [TARGET] at median and 75th percentile multiples

Output Format:
Transaction table with control premium analysis and implied target range.
```

### 📊 Excel Model Structure
```text
Sheet 1 TRANSACTIONS: acquirer, target, date, EV, EV/EBITDA, EV/Rev, premiums
Sheet 2 STATISTICS: median, mean, 25th, 75th by buyer type
Sheet 3 IMPLIED_RANGE: target value at each percentile
```

</details>

---

## 🔹 The Conglomerate SOTP & Break-Up Value Analysis

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst specialising in complex corporate structure and conglomerate valuation.

Task:
SOTP valuation for [COMPANY] with [N] business segments.
Per segment: appropriate methodology (EV/EBITDA for operating, NAV for real estate)
Pure-play comparables for each segment multiple
Corporate costs: capitalise at appropriate multiple
Net debt: deduct from total segment value
Conglomerate discount: apply [X]% with historical precedent justification
Break-up value: what would each segment fetch in a standalone sale?
Value gap: SOTP vs current market cap — catalyst to close?

Output Format:
SOTP table with conglomerate discount and break-up value per segment.
```

### 📊 Excel Model Structure
```text
Sheet 1 SOTP_TABLE: segment, EBITDA, multiple, EV, comparable_used
Sheet 2 COMPS_PER_SEGMENT: pure-play peers per segment
Sheet 3 BREAK_UP_VALUE: standalone value vs conglomerate contribution
```

</details>

---

## 🔹 The M&A; Deal Economics & EPS Impact Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior M&A; banker assessing deal economics for a proposed acquisition.

Task:
Accretion/dilution analysis for [ACQUIRER] acquiring [TARGET].
Deal: [X]% cash / [X]% stock at [X] exchange ratio
Financing: [CUR][X] new debt at [X]% coupon
Synergies: [CUR][X] cost, [CUR][X] revenue, phased over [N] years
One-time costs: restructuring [CUR][X], integration [CUR][X]
Pro forma EPS: Year 1, Year 2, Year 3 with and without synergies
Breakeven synergies: minimum for EPS neutrality
ROIC vs WACC: does the deal create value at each synergy case?

Output Format:
Accretion/dilution table by year with synergy sensitivity.
```

### 📊 Excel Model Structure
```text
Sheet 1 ACC_DIL: standalone EPS, pro_forma_EPS, accretion_pct by year
Sheet 2 SYNERGY_SENSITIVITY: accretion at 0/50/75/100% synergy realisation
Sheet 3 ROIC_ANALYSIS: incremental ROIC vs WACC per scenario
```

</details>

---

## 🔹 The Investment Banking Fairness Opinion Analytical Stru

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior investment banker preparing the analytical framework for a board fairness opinion.

Task:
Fairness opinion framework for [TARGET] at [CONSIDERATION].
Standard methods (document all used):
1. DCF Analysis: range
2. Comparable Company: 25th-75th percentile range
3. Precedent Transactions: 25th-75th percentile range
4. LBO Analysis: minimum financial buyer floor
5. 52-week trading range
Football field: display all ranges, mark where consideration falls
Is consideration within fairness range on majority of methods?
Document any excluded method with specific reason

Output Format:
Football field with methodology ranges and fairness assessment.
```

### 📊 Excel Model Structure
```text
Sheet 1 FOOTBALL_FIELD: methodology, low, high, consideration, in_range
Sheet 2 METHODOLOGY_DETAIL: assumptions, source, date per method
Sheet 3 FAIRNESS_SUMMARY: consideration vs each range, majority test
```

### 💡 Sample Output
```text
FAIRNESS OPINION | [TARGET] | Consideration: [CUR][X]
FOOTBALL FIELD
DCF: [CUR][X] — [CUR][Y] | In range: [Y/N]
Comparable Cos: [CUR][X] — [CUR][Y] | In range: [Y/N]
Precedent Trans: [CUR][X] — [CUR][Y] | In range: [Y/N]
LBO Floor: [CUR][X] — [CUR][Y] | In range: [Y/N]
FAIRNESS: Consideration within range in [X] of [N] methods
• The DCF sensitivity table is the most valuable output — it communicates the full range of reasonable
outcomes.
• WACC must be precisely sourced: RF rate with date, ERP with source. Unsourced WACC fails IC
challenge.
• LBO analysis provides the valuation floor: the minimum a financial buyer would pay. Strategic buyers
typically pay 30-40% more.
• Character notes: Nadia Merchant (2nd-year analyst, Apex Capital Advisors). 34 hours. 8 valuation
methods. One IC deck.
```

</details>

---

