# 🏦 Claude Cowork, Plugins & MCP Connectors

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 Prompt 1 — The Cowork Earnings Flash Note Automation Sys

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Configure as a Cowork workflow. Trigger: new PDF in /Earnings_Releases/ folder.

Task:
STEP 1 (Haiku): Detect new PDF. Identify company ticker and report date.
STEP 2 (Haiku): Extract from PDF:
Revenue, EPS, EBITDA, gross margin, operating expenses (vs prior quarter, prior year)
Full-year or next-quarter guidance (if disclosed)
STEP 3: Open [TICKER] row in /Models/Estimates_Master.xlsx.
Calculate beat/miss % for each metric vs consensus estimate.
STEP 4 (Sonnet): Draft flash note using /Templates/Flash_Note.docx:
Headline (1 sentence): beat/miss + primary driver
Key metrics table: actual vs consensus vs prior year
Guidance summary (2-3 sentences)
Thesis impact: POSITIVE/NEUTRAL/NEGATIVE + 2-sentence rationale
STEP 5: Save as [TICKER]_[DATE]_Flash.docx in /Flash_Notes/
STEP 6: Draft approval email to PM. DO NOT SEND. Require human approval.
STEP 7: Update /Reports/Flash_Log.xlsx with ticker, filing time, draft time, beat/miss.

Output Format:
Draft flash note ready in /Flash_Notes/ within 12-15 minutes of PDF detection.
```

### 💡 Sample Output
```text
FLASH NOTE | [COMPANY] ([TICKER]) | [DATE] | Filed: [TIME]
HEADLINE: [COMPANY] [QUARTER] [beats/misses] [PRIMARY METRIC] by [X]%;
[PRIMARY DRIVER]
KEY METRICS
Metric | Actual | Consensus | Beat/Miss | Prior Year
Revenue | [CUR][X] | [CUR][Y] | [+/-Z]% | [CUR][A]
EPS | [X] | [Y] | [+/-Z]% | [A]
GUIDANCE: [FULL YEAR / NEXT QUARTER]: [CUR][X-Y] vs consensus [CUR][Z]
THESIS IMPACT: [POSITIVE/NEUTRAL/NEGATIVE]
[2 sentences why this result affects the thesis]
[DRAFT — PM approval required. Not SEBI registered.]
```

</details>

---

## 🔹 Prompt 2 — The Real-Time News Classification & Alert Sys

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Set as a Cowork workflow. Trigger: scheduled run every [N] hours.

Task:
Monitor news and regulatory filings for [N]-stock coverage universe.
STEP 1 (Haiku): Scan news headlines for each ticker in /Coverage/universe.csv
Classify each news item: MATERIAL / NOTEWORTHY / ROUTINE / IGNORE
MATERIAL criteria: earnings revision, M&A;, CEO change, regulatory action, guidance change
STEP 2 (Sonnet for MATERIAL items only): For each MATERIAL item:
One-sentence summary
Thesis impact: POSITIVE/NEUTRAL/NEGATIVE
Urgency: IMMEDIATE ACTION / MONITOR / NOTE FOR NEXT REVIEW
STEP 3: Update /Reports/News_Log.xlsx
STEP 4: If MATERIAL + IMMEDIATE ACTION: draft alert email to PM (DO NOT SEND)

Output Format:
News log updated and MATERIAL items flagged with thesis impact.
```

### 📊 Excel Model Structure
```text
Sheet 1 NEWS_LOG: ticker, date, headline, classification, thesis_impact, urgency
Sheet 2 MATERIAL_ALERTS: item, summary, thesis_impact, draft_email_prepared
Sheet 3 WEEKLY_SUMMARY: tickers_with_material_news, themes, portfolio_implications
```

</details>

---

## 🔹 Prompt 3 — The Automated Portfolio Risk Limit Breach Det

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Configure as a daily Cowork workflow for risk monitoring.

Task:
Daily risk limit monitoring for [PORTFOLIO].
STEP 1 (Haiku): Import current positions from /Portfolio/positions_today.csv
Compare to limits in /Risk/limits_master.xlsx:
Single position limit: flag if any holding >[X]% of NAV
Sector concentration: flag if any sector >[X]% of NAV
Cash level: flag if cash <[X]% (liquidity limit)
Active share: flag if active share <[X]% (benchmark-hugging risk)
STEP 2 (Sonnet for breaches): For each breach:
Calculate magnitude of breach
Recommend corrective trade
Urgency: SAME DAY / END OF WEEK / NEXT REBALANCE
STEP 3: Update /Reports/Risk_Dashboard.xlsx
STEP 4: If breach: draft risk alert to CIO (DO NOT SEND — require approval)

Output Format:
Risk dashboard updated and breach alerts drafted for approval.
```

### 📊 Excel Model Structure
```text
Sheet 1 RISK_DASHBOARD: dimension, current, limit, breach_flag, magnitude
Sheet 2 BREACH_LOG: date, dimension, magnitude, corrective_trade, urgency
Sheet 3 CORRECTIVE_TRADES: trade, size, rationale, expected_impact_on_limit
```

</details>

---

## 🔹 Prompt 4 — Claude's Five Finance Plugins — Selection & C

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst configuring Claude's built-in finance plugins for institutional research.

Task:
Select and configure the appropriate Claude finance plugin for your task:
PLUGIN 1 — FINANCIAL ANALYSIS
Capabilities: DuPont decomposition, Altman Z-score, Gordon Growth, ratio analysis
Best for: financial statement analysis, credit screening, valuation cross-checks
PLUGIN 2 — INVESTMENT BANKING
Capabilities: LBO conventions, accretion/dilution, fairness opinion structure
Best for: M&A; analysis, deal structuring, IB deliverables
PLUGIN 3 — EQUITY RESEARCH
Capabilities: research note format, sector KPIs, target price, required disclosures
Best for: initiating coverage, earnings notes, sector deep dives
PLUGIN 4 — PRIVATE EQUITY
Capabilities: PE formatting, IC memo, 100-day plan, IRR analysis
Best for: deal evaluation, portfolio monitoring, LP reporting
PLUGIN 5 — WEALTH MANAGEMENT (Claude built-in plugin, 2025)
Capabilities: IPS construction, RRTTLLU framework, client letter compliance,
goal-based planning, suitability assessment, rebalancing triggers
Best for: HNI/UHNI advisory, regulated client communication, portfolio suitability
My task: [DESCRIBE YOUR SPECIFIC TASK]
Plugin selected: [PLUGIN NAME]
Apply all domain-specific conventions and compliance requirements.

Output Format:
Plugin-enhanced output with domain-specific conventions and compliance language.
```

### 📊 Excel Model Structure
```text
Sheet 1 PLUGIN_OUTPUT: analysis with plugin conventions applied
Sheet 2 DOMAIN_METRICS: sector KPIs and benchmarks
Sheet 3 COMPLIANCE_CHECK: disclosures and regulatory language verified
```

</details>

---

## 🔹 Prompt 5 — HNI Client Advisory Using Claude Wealth Manag

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Wealth manager using Claude's built-in Wealth Management plugin for HNI client advisory.

Task:
Use the Claude Wealth Management plugin to prepare a complete HNI client advisory package.
CLIENT PROFILE:
Name: [CLIENT] | Age: [AGE] | Risk Profile: [CONSERVATIVE/MODERATE/AGGRESSIVE]
AUM: [AMOUNT] | Time Horizon: [YEARS] | Tax: [INDIA/OTHER]
Income: [AMOUNT] | Dependants: [N] | Existing Investments: [DESCRIBE]
STEP 1 — RRTTLLU ASSESSMENT
Return Required: minimum return to meet goals
Risk Tolerance: stated and revealed
Time Horizon: short/medium/long per goal
Tax: treatment on each asset class
Liquidity: emergency fund + near-term needs
Legal: nominee, will, trust requirements
Unique: specific constraints or ESG preferences
STEP 2 — INVESTMENT POLICY STATEMENT
Strategic Asset Allocation with rebalancing ranges
Permitted and prohibited instruments
Benchmark and review frequency
STEP 3 — CLIENT LETTER (compliance-ready)
Portfolio review vs IPS targets
Recommended changes with rationale
Compliance footer: SEBI status, educational purpose disclaimer

Output Format:
Complete HNI advisory package: RRTTLLU, IPS draft, and compliant client letter.
```

### 📊 Excel Model Structure
```text
Sheet 1 RRTTLLU_MATRIX: seven-factor assessment with scores and recommendations
Sheet 2 IPS_DRAFT: SAA, ranges, rebalancing triggers, permitted instruments
Sheet 3 CLIENT_LETTER: compliant, client-ready communication with disclosures
Sheet 4 PORTFOLIO_MONITOR: current vs IPS targets with drift alerts
```

</details>

---

## 🔹 Prompt 6 — The FactSet / LSEG / PitchBook Live Data Inte

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst integrating live data sources via MCP connectors.

Task:
Design a workflow using MCP connectors for [USE CASE: e.g. earnings preview, credit
analysis].
Available MCP connectors:
FactSet: financial data, estimates consensus, company filings
LSEG (Refinitiv): pricing, fixed income data, news feeds
PitchBook: private markets data, deal flow, fund performance
Moody's Analytics: credit risk data, ratings, default studies
Workflow design:
Which connector provides which data element?
Data refresh frequency: real-time vs daily vs on-demand
Integration: how does live data flow into Claude's analytical output?
Fallback: if connector unavailable, what manual data entry is required?
My use case: [DESCRIBE THE SPECIFIC ANALYTICAL TASK AND DATA NEEDED]

Output Format:
MCP workflow design with data source mapping and fallback plan.
```

### 📊 Excel Model Structure
```text
Sheet 1 DATA_MAP: data_element, mcp_connector, field_name, refresh_frequency
Sheet 2 WORKFLOW_STEPS: step, data_source, claude_action, output
Sheet 3 FALLBACK_PLAN: if_connector_down, manual_alternative, time_impact
```

</details>

---

## 🔹 Prompt 7 — The Investment Committee Presentation Prepara

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Set as a weekly Cowork workflow for IC preparation.

Task:
Automated IC deck preparation for [FUND]'s weekly IC meeting.
STEP 1 (Haiku): Pull current portfolio weights from /Portfolio/positions.csv
Compare to last IC: calculate all position changes since prior meeting
STEP 2 (Sonnet): For each changed position:
One-line rationale for change
Updated BCE vs prior BCE
Flag if thesis-critical KPI has changed
STEP 3 (Sonnet): Macro overlay update:
Key macro developments since last IC (3 bullet points max)
Portfolio positioning vs macro view: aligned or divergent?
STEP 4 (Sonnet): New ideas pipeline:
Any names from screening that merit IC attention this week?
STEP 5: Compile into /IC_Decks/IC_[DATE].docx using /Templates/IC_Template.docx

Output Format:
Draft IC deck prepared in /IC_Decks/ ready for PM review.
```

### 📊 Excel Model Structure
```text
Sheet 1 POSITION_CHANGES: ticker, prior_weight, current_weight, delta, rationale
Sheet 2 BCE_UPDATES: ticker, prior_BCE, current_BCE, delta, driver
Sheet 3 NEW_IDEAS_PIPELINE: ticker, screen_score, preliminary_thesis, next_step
```

### 💡 Sample Output
```text
the standard AI model (Cowork)
```

</details>

---

## 🔹 Prompt 8 — The Automated Client Communication & Quarterl

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Configure as a quarterly Cowork workflow for client communications.

Task:
Automated quarterly client letter for [FUND / STRATEGY].
STEP 1 (Haiku): Pull quarterly performance data from /Reports/Performance_Q[N].csv
Calculate: total return, benchmark return, active return, key contributors
STEP 2 (Sonnet): Draft quarterly letter using /Templates/Client_Letter.docx:
Performance summary: total return and benchmark comparison
Top 3 contributors and detractors with one-sentence each
Market commentary: 2 paragraphs on macro and sector context
Positioning: how is the portfolio positioned for next quarter?
Outlook: 2-3 sentences (use cautious, non-committal language)
STEP 3: Compliance check: verify Base Case Estimates language, no price targets
STEP 4: Save as /Client_Letters/[FUND]_Q[N]_[YEAR].docx
STEP 5: Draft distribution email (DO NOT SEND — require compliance approval)

Output Format:
Draft client letter ready for compliance review before distribution.
```

### 📊 Excel Model Structure
```text
Sheet CLIENT_LETTERS: quarter, fund, sent_date, return_pct, key_message
Tab COMMENTARY_TRACKER: quarter, market_theme, positioning_msg, outlook
```

### 💡 Sample Output
```text
Complete client letter draft with all five steps executed in sequence.
```

</details>

---

