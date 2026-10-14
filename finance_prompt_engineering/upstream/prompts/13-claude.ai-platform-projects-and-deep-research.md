# 🏦 Claude.ai Platform: Projects & Deep Research

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 Prompt 1 — The Institutional Claude Project Configuratio

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of research at a buy-side fund managing coverage across 12 sectors.

Task:
Design a Claude Project configuration for institutional equity research:
Project name and scope: [SECTOR/COVERAGE UNIVERSE]
Always-loaded documents: IPS, sector primers, valuation benchmarks
Session documents: latest earnings, recent filings, current pitch books
Custom instructions: output format, citation requirements, model preferences
Workflow: how to open each session, what to load first, how to close.

Output Format:
Complete Project configuration guide with document priority matrix.
```

### 📊 Excel Model Structure
```text
Sheet PROJECT_CONFIG: document, priority, always_load, session_load
Tab SESSION_TEMPLATE: open_with, standard_queries, close_with
```

### 💡 Sample Output
```text
Configuration covering all document types with explicit load priority.
```

</details>

---

## 🔹 Prompt 2 — The Claude Deep Research Sector Initiation Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Equity analyst initiating coverage on a new sector with zero prior research.

Task:
Use Claude Deep Research to build a sector initiation from scratch:
Step 1: Industry structure — Porter's Five Forces, value chain, key players
Step 2: Competitive dynamics — market share, pricing power, switching costs
Step 3: Financial benchmarks — typical margins, returns, valuation multiples
Step 4: Key risks — regulatory, cyclical, technological disruption
Step 5: Stock selection criteria — what makes a winner in this sector.

Output Format:
Sector initiation framework: 5 sections, each with analysis and data tables.
```

### 📊 Excel Model Structure
```text
Sheet SECTOR_MAP: company, market_share, margin, multiple, rating
Tab COMP_TABLE: metric, sector_avg, top_quartile, bottom_quartile
```

### 💡 Sample Output
```text
Full five-section initiation with comparative data tables.
```

</details>

---

## 🔹 Prompt 3 — The Multi-Quarter Transcript Intelligence Fra

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Portfolio manager tracking management credibility across earnings calls.

Task:
Load last 8 quarters of earnings call transcripts for [COMPANY].
Analyse management language for: guidance accuracy vs actuals, confidence changes, topic
avoidance patterns, tone shifts on key metrics.
Flag: promises made vs kept, topics that disappear from calls, language hedging patterns,
analyst question deflection.

Output Format:
Management credibility scorecard: guidance accuracy, language trends, red flags.
```

### 📊 Excel Model Structure
```text
Sheet GUIDANCE_TRACKER: quarter, metric, guided, actual, miss_pct
Tab LANGUAGE_FLAGS: quarter, topic, sentiment_score, flag
```

### 💡 Sample Output
```text
Scorecard with 8-quarter trend and specific language examples cited.
```

</details>

---

## 🔹 Prompt 4 — The Automated Prior Period vs Current Period

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Credit analyst comparing two consecutive annual reports for covenant drift.

Task:
Compare [CURRENT PERIOD] vs [PRIOR PERIOD] for [COMPANY]:
Financial changes: revenue, margins, leverage ratios, cash conversion
Language changes: risk factor additions/removals, MD&A; tone shifts
Covenant changes: new restrictions, waiver history, headroom changes
Management changes: new executives, board changes, comp structure
Flag every material change with page reference and significance rating.

Output Format:
Change log: financial deltas, language changes, covenant changes flagged by severity.
```

### 📊 Excel Model Structure
```text
Sheet CHANGE_LOG: section, prior_text, current_text, change_type, significance
Tab FINANCIAL_DELTA: metric, prior, current, change_pct, flag
```

### 💡 Sample Output
```text
Complete comparison with severity flags and specific references.
```

</details>

---

## 🔹 Prompt 5 — The Full Sector Initiation & Coverage Launch

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst launching coverage of 8 companies in a new sector simultaneously.

Task:
For each of 8 companies in [SECTOR], produce a coverage launch pack:
1. One-page company overview: business model, revenue streams, key metrics
2. Relative positioning: where each sits on growth vs value spectrum
3. Initial valuation: fair value range using two methods
4. Investment thesis: bull case, base case, bear case
5. Top 3 risks to monitor
Output: structured comparison table plus individual company pages.

Output Format:
Coverage launch pack: comparison table + 8 company pages + sector ranking.
```

### 📊 Excel Model Structure
```text
Sheet COVERAGE_UNIVERSE: company, thesis, price_target, upside, conviction
Tab COMP_VALUATION: company, method1, method2, blended, current_price
```

### 💡 Sample Output
```text
Complete 8-company pack with individual pages and comparison table.
```

</details>

---

## 🔹 Prompt 6 — The Long-Running Project Context Optimisation

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Research director managing ongoing coverage of 15 companies across 6 months.

Task:
Design a context optimisation strategy for sustained research coverage:
Document hierarchy: what must always be in context vs what loads per session
Compression techniques: running summaries, bullet-point thesis trackers
Version control: how to track when thesis assumptions change
Session templates: open with X, always query Y before closing
Project: [DESCRIBE COVERAGE SCOPE AND DOCUMENT VOLUME]

Output Format:
Context optimisation guide with document prioritisation and session templates.
```

### 📊 Excel Model Structure
```text
Sheet DOCUMENT_PRIORITY: document, priority, always_load, compression_rule
Tab SESSION_TEMPLATE: open_sequence, standard_queries, close_checklist
```

### 💡 Sample Output
```text
Complete strategy with document hierarchy and compression rules.
```

</details>

---

## 🔹 Prompt 7 — The Real-Time Portfolio Event & Signal Monito

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager at a long-only institutional fund.

Task:
Set up a Claude-based monitoring framework for a 20-stock portfolio:
Daily: price moves >3%, volume spikes, material news alerts
Weekly: earnings dates, analyst rating changes, insider transactions
Monthly: position drift vs IPS limits, factor exposure shifts
Output: priority-ranked alert list with action recommendation per item.

Output Format:
Priority-ranked alert dashboard: trigger, magnitude, context, recommended action.
```

### 📊 Excel Model Structure
```text
Sheet ALERT_LOG: date, ticker, alert_type, magnitude, action_taken
Tab MONITORING_RULES: trigger, threshold, frequency, escalation_level
```

### 💡 Sample Output
```text
Alert list covering all four monitoring frequencies with specific thresholds.
```

</details>

---

## 🔹 Prompt 8 — The Multi-Source Intelligence Aggregation & S

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior research analyst at a long-only fund managing a 25-stock portfolio.

Task:
Using Claude extended context, synthesise across four sources:
Source 1: Latest quarterly earnings transcript
Source 2: Key sections from the most recent annual report
Source 3: Three most recent sell-side research summaries
Source 4: Last 3 months of material news
Output: thesis changes, consensus vs your view gaps, three management questions, updated
conviction 1-10 with reasoning.

Output Format:
One-page synthesis: thesis changes, consensus gaps, management questions, conviction
update.
```

### 📊 Excel Model Structure
```text
Sheet RESEARCH_SYNTHESIS: source, key_finding, thesis_impact, action
Tab CONVICTION_TRACKER: date, event, old_conviction, new_conviction, reason
```

### 💡 Sample Output
```text
Full synthesis referencing all four sources with specific findings.
```

</details>

---

