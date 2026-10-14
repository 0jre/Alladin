# 🏦 The Earnings Intelligence Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Institutional Pre-Earnings Intelligence Brief

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior equity research analyst writing institutional earnings previews for buy-side funds.

Task:
Pre-earnings brief for [COMPANY], [TICKER], reporting in [N] days.
Last 4 quarters: beat/miss history, revenue, EPS, primary KPI (with % magnitude)
Consensus estimates for upcoming quarter
Three thesis-critical metrics for THIS company THIS quarter (not generic EPS)
— must be KPIs management has been building narrative around
Historical stock price reaction day+1 after each of last 4 reports
Bull case: specific upside scenario with magnitude estimate
Bear case: specific downside with mechanism and magnitude
Decision matrix: exact action at each outcome combination
Current positioning recommendation

Output Format:
Pre-earnings brief with decision summary at top. Base Case Estimates only.
```

### 📊 Excel Model Structure
```text
Sheet 1 EARNINGS_HISTORY: 8 quarters, actuals, consensus, magnitude, stock_D1
Sheet 2 DECISION_MATRIX: scenario, criteria, action, size_change, approval_required
```

### 💡 Sample Output
```text
PRE-EARNINGS BRIEF | [COMPANY] | Reports: [DATE]
DECISION SUMMARY: [HOLD/TRIM/ADD] into earnings.
3 THESIS-CRITICAL METRICS
1. [KPI 1]: need ≥[Y] — [thesis implication if miss]
2. [KPI 2]: need [CONDITION]
3. [GUIDANCE]: cut below [X] = thesis break
DECISION MATRIX
All 3 beat → Add to [X]% | 2 of 3 → Hold | 1 of 3 → Trim | All miss → IC escalation
```

</details>

---

## 🔹 The Management Communication & Language Shift Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst specialising in management communication and earnings call sentiment.

Task:
Tone evolution across last 4 earnings transcripts for [COMPANY]. Ask Claude: 'Find the
last 4 earnings call transcripts for [COMPANY] and analyse them.'
Per quarter: MORE CONSTRUCTIVE / NEUTRAL / MORE CAUTIOUS
Keyword frequency across all 4 transcripts:
Positive: 'accelerating', 'confident', 'exceeding', 'ahead of'
Negative: 'cautious', 'monitoring', 'headwinds', 'challenging'
Language shifts: words that appeared or disappeared with frequency counts
Topic deflection: questions management avoided or answered obliquely
Guidance language: moving more specific or more vague over 4 quarters?
Synthesis: what does the 4-quarter trajectory signal about business momentum?

Output Format:
Tone evolution table with evidence. One-paragraph synthesis. Quotes under 10 words.
```

### 📊 Excel Model Structure
```text
Sheet 1 TONE_TRACKER: quarter, rating, positive_count, negative_count, deflections
Sheet 2 KEYWORD_ANALYSIS: word, Q1_Q2_Q3_Q4 frequency, trend_direction
```

### 💡 Sample Output
```text
TONE TRAJECTORY
Q-3: [CONSTRUCTIVE] → Q-2: [NEUTRAL] → Q-1: [CAUTIOUS] → Q: [MORE CAUTIOUS]
KEY SHIFTS
DISAPPEARED: '[word]' ([N]x → 0x) | APPEARED: '[word]' (0x → [N]x)
SYNTHESIS: [What the 4-quarter trajectory signals about upcoming guidance]
```

</details>

---

## 🔹 The Management Guidance Reliability & Forecast Accuracy

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior equity analyst specialising in management guidance analysis and reliability
scoring.

Task:
Historical guidance accuracy and quality for [COMPANY], last 8 quarters.
For each quarter: initial guidance vs actual for revenue, EPS, key KPI
Pattern: does management guide conservative, accurate, or aggressive?
Guidance language: specific (numeric) or vague (qualitative)? Trending which way?
Which metrics does management refuse to guide on and why?
Revision frequency: how often does guidance change intra-quarter?
Credibility score: 1-10 per metric with rationale
Implication for upcoming quarter: what adjustment to consensus is warranted?

Output Format:
Guidance track record with credibility scores and pattern analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 GUIDANCE_TRACK: quarter, metric, initial_guide, actual, magnitude_miss
Sheet 2 CREDIBILITY_SCORES: metric, guidance_type, accuracy, score
Sheet 3 REVISION_PATTERN: date, metric, direction, trigger
```

</details>

---

## 🔹 The Institutional Segment-Level Revenue Intelligence Fr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior equity analyst specialising in segment revenue analysis and business mix
assessment.

Task:
Segment-level revenue analysis for [COMPANY], last 8 quarters.
Revenue by: geography, product line, channel, customer type
Growth rate per segment across 8 quarters
Gross margin per segment (if disclosed)
Mix shift: which segments growing as % of total? Higher or lower margin?
Margin implication: what does mix trajectory mean for blended margin in 3 years?
ARR/backlog/book-to-bill for relevant segment types
Key insight: what does segment analysis tell us that the headline misses?

Output Format:
Segment decomposition with mix shift and margin implications.
```

### 📊 Excel Model Structure
```text
Sheet 1 SEGMENT_REVENUE: segment, revenue by quarter, pct_of_total, growth
Sheet 2 MIX_SHIFT: segment, pct_2yrs_ago, pct_today, direction, margin_implication
```

</details>

---

## 🔹 The Forensic Earnings Quality & Cash Conversion Analysi

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior forensic accounting analyst specialising in earnings quality and red flag
detection.

Task:
Earnings quality assessment for [COMPANY], last 8 quarters.
Cash conversion: OCF vs net income ratio (quality earnings: >90%)
FCF vs reported EPS: FCF/share vs EPS trend
Working capital: receivables or inventory growing faster than revenue?
Accruals ratio: (NOA(t) - NOA(t-1)) / avg total assets (Sloan 1996 methodology)
High accruals = lower future earnings (documented in academic research)
Revenue quality: deferred revenue trend, revenue recognition changes
Expense management: capitalisation trends, R&D; spending trajectory
Overall earnings quality score: 1-10 with red flags listed

Output Format:
Earnings quality scorecard with accruals analysis and red flags.
```

### 📊 Excel Model Structure
```text
Sheet 1 CASH_CONVERSION: quarter, net_income, OCF, FCF, OCF/NI_ratio
Sheet 2 ACCRUALS: quarter, NOA, accruals_ratio, flag
Sheet 3 QUALITY_SCORECARD: dimension, score, red_flags, trend
```

</details>

---

## 🔹 The Buy-Side Consensus Map & Variant Perception Framewo

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager specialising in consensus analysis and differentiated
positioning.

Task:
Consensus positioning analysis and variant perception for [COMPANY].
Consensus map: rating distribution (% Buy/Hold/Sell), median target, implied upside
EPS estimate dispersion: coefficient of variation (high = high uncertainty)
Revision trend: upgrades vs downgrades last 30 days
Crowding: institutional ownership % and trend, short interest
My variant perception:
Where does my view differ from consensus? Be specific about the assumption.
Is the market wrong on growth, margin, or multiple?
What convergence catalyst would force consensus to my view?
My variant: [DESCRIBE WHERE YOU DIFFER FROM CONSENSUS]

Output Format:
Consensus map with variant perception and convergence catalyst.
```

### 📊 Excel Model Structure
```text
Sheet 1 CONSENSUS_MAP: analyst, rating, target (show distribution)
Sheet 2 POSITIONING: institutional_ownership, trend, crowding, short_interest
Sheet 3 VARIANT_PERCEPTION: my_assumption, consensus, delta, catalyst
```

</details>

---

## 🔹 The Institutional Post-Earnings Position Management Pro

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager specialising in systematic post-earnings position management.

Task:
Post-earnings repositioning for [COMPANY] following [QUARTER] results.
Matrix execution: did actual outcome match pre-committed matrix? Any deviation?
If deviation: document reasoning and flag for bias review
Thesis update: which assumptions confirmed, weakened, or broken?
Updated BCE following results and new guidance
Market reaction: proportionate, over, or under-reaction?
If under-reaction: is there a trading opportunity?
New monitoring KPIs for next quarter
Actual results: [DESCRIBE] | My pre-committed matrix: [IF APPLICABLE]

Output Format:
Post-earnings memo with thesis update and new monitoring plan.
```

### 📊 Excel Model Structure
```text
Sheet 1 MATRIX_EXECUTION: scenario_predicted, actual, action_required, deviation
Sheet 2 THESIS_UPDATE: assumption, pre, post, status
Sheet 3 NEW_MONITORING: KPI, current, trim_threshold, add_threshold
```

</details>

---

## 🔹 The Multi-Company Earnings Season Monitoring System

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior equity analyst managing earnings season across a large coverage universe.

Task:
Earnings season dashboard for [N]-company coverage universe.
Earnings calendar: company, date, BMO/AMC, consensus estimates, my position
Flash note template per company as results arrive:
Headline (1 sentence): beat/miss + primary driver
Key metrics table: actual vs consensus vs prior year
Guidance (2-3 sentences)
Thesis impact: POSITIVE/NEUTRAL/NEGATIVE + 2-sentence rationale
Decision matrix action triggered
Season summary: beat/miss rate, matrix accuracy, macro thesis confirmation
My coverage universe: [LIST COMPANIES AND EARNINGS DATES]

Output Format:
Earnings calendar with flash note template and season summary.
```

### 📊 Excel Model Structure
```text
Sheet 1 EARNINGS_CALENDAR: company, date, time, consensus, my_position, matrix
Sheet 2 FLASH_NOTE_LOG: company, date, beat/miss, thesis_impact, action
Sheet 3 SEASON_SUMMARY: beat_rate, matrix_accuracy, macro_confirmation
```

### 💡 Sample Output
```text
EARNINGS SEASON | [N] companies | Next 2 weeks
CALENDAR
[DATE] | [COMPANY] | AMC | Rev: [CUR][X] | EPS: [CUR][X] | [X]% OW
FLASH NOTE FORMAT
HEADLINE: [COMPANY] [QTR] [beats/misses] [METRIC] by [X]%
THESIS IMPACT: [POSITIVE/NEUTRAL/NEGATIVE]
DECISION: [ACTION per pre-committed matrix]
• Pre-commitment to decision matrix before earnings prevents rationalisation — the most common
institutional error.
• Thesis-critical metrics are company-specific and quarter-specific, never generic EPS.
• Tone trajectory precedes guidance changes by 1-2 quarters: 'acceleration' → 'sustained' → 'cautious'.
• Character notes: Priya Desai (Senior Analyst, Mirae Asset India). Enterprise software. 6% stock decline
avoided by pre-commitment.
```

</details>

---

