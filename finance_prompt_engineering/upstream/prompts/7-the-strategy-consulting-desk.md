# 🏦 The Strategy Consulting Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The Institutional Competitive Landscape & Market Struct

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategy partner conducting competitive analysis for an institutional investment
fund.

Task:
Full competitive landscape for [SECTOR], [GEOGRAPHY].
Top 5-7 competitors: market cap, revenue, 3yr growth, EBITDA margin, market share
Moat per company: brand, cost advantage, network effect, switching cost
Rate each: WIDE / MODERATE / NARROW with one-line rationale
Moat trajectory: STRENGTHENING / STABLE / WEAKENING
Market share trends by primary channel, 3 years
Management quality: capital allocation track record rated 1-10
Biggest threats: regulatory, disruption, macro
Single best investment thesis with catalyst and 12-month timeline

Output Format:
Strategy consulting brief with moat trajectory and market share trends.
```

### 📊 Excel Model Structure
```text
Sheet 1 COMPETITIVE_TABLE: company, metrics, moat_score, trajectory
Sheet 2 MARKET_SHARE: company, channel, 2022, 2023, 2024, trend
Sheet 3 INVESTMENT_THESIS: best_idea, rationale, catalyst, timeline
```

### 💡 Sample Output
```text
COMPETITIVE LANDSCAPE | [SECTOR] | [DATE]
MARKET STRUCTURE
Company | Market Cap | Revenue | Moat | Trajectory
[CO A] | [CUR][X] | [CUR][X] | WIDE | STRENGTHENING
[CO B] | [CUR][X] | [CUR][X] | NARROW | WEAKENING
BEST THESIS: Overweight [COMPANY A] vs [COMPANY B]
Growing [X]% faster at [X]% cheaper valuation. Catalyst: [DESCRIBE]
```

</details>

---

## 🔹 The Porter Five Forces Industry Attractiveness Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategy analyst applying Michael Porter's documented Five Forces framework.

Task:
Porter Five Forces analysis for [INDUSTRY/SECTOR].
Force 1: Competitive Rivalry
Number of competitors, concentration (HHI), growth rate, exit barriers
Rating: LOW / MEDIUM / HIGH intensity
Force 2: Supplier Power
Concentration, switching costs, forward integration threat
Force 3: Buyer Power
Concentration, price sensitivity, backward integration threat
Force 4: Threat of New Entrants
Capital requirements, regulatory barriers, brand differentiation
Force 5: Threat of Substitutes
Availability, relative price/performance, switching costs
Overall industry attractiveness score: 1-10
Which force is changing most rapidly? Investment implication?

Output Format:
Five Forces assessment with industry attractiveness score and investment implication.
```

### 📊 Excel Model Structure
```text
Sheet 1 FIVE_FORCES: force, intensity, rating, evidence, trend
Sheet 2 ATTRACTIVENESS_SCORE: overall and by force, 3yr trend
Sheet 3 INVESTMENT_IMPLICATION: what the force analysis means for equity returns
```

</details>

---

## 🔹 The Competitive Advantage Period & Moat Width Assessmen

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior investment analyst specialising in economic moat assessment and duration analysis.

Task:
Deep moat analysis for [COMPANY].
Moat source identification and evidence:
Intangible assets (brand, patent, regulatory licence): strength, scope, duration
Cost advantage: source (scale, process, location), magnitude, sustainability
Switching costs: direct evidence (churn rate, contract terms, integration depth)
Network effect: type (direct/indirect), critical mass achieved, reinforcement
Efficient scale: limited market size that deters competition
Moat width: WIDE / NARROW / NONE with supporting metrics
Competitive Advantage Period: how many years can excess returns persist?
Moat trajectory: is it strengthening or narrowing?
Key moat threat: what is the most credible path to moat erosion?

Output Format:
Moat assessment with Competitive Advantage Period and erosion threat.
```

### 📊 Excel Model Structure
```text
Sheet 1 MOAT_SOURCES: source, evidence, strength_1to5, duration_estimate
Sheet 2 RETURNS_ANALYSIS: ROIC, WACC, economic_profit by year (10yr)
Sheet 3 THREAT_ANALYSIS: moat_threat, probability, timeline, impact
```

</details>

---

## 🔹 The Channel-Level Market Share & Competitive Dynamics F

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior industry analyst specialising in market share dynamics and competitive positioning.

Task:
Market share trend analysis for [COMPANY] in [SECTOR].
Total market share: quarterly for last 8 quarters
By distribution channel: [CHANNEL 1], [CHANNEL 2], [CHANNEL 3]
New customer acquisition: win rate vs specific competitors
Customer retention: churn rate trend, net revenue retention
Price realisation: is market share gained at normal pricing or discounted?
Geographic market share: by region if available
Trend inflection: when did market share momentum change and what caused it?
Leading indicator: what metric will signal further share gains/losses 2 quarters ahead?

Output Format:
Market share trend with channel decomposition and leading indicator.
```

### 📊 Excel Model Structure
```text
Sheet 1 MARKET_SHARE_TREND: quarter, total, by_channel, vs_peer
Sheet 2 ACQUISITION_RETENTION: win_rate, churn_rate, NRR, trend
Sheet 3 LEADING_INDICATOR: metric, current, signal, timeline
```

</details>

---

## 🔹 The Institutional SWOT & Strategic Position Assessment

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior strategy analyst conducting comprehensive SWOT for institutional investment
decision.

Task:
Full SWOT analysis for [COMPANY] vs [PRIMARY COMPETITOR].
Strengths: not generic (avoid 'strong brand' — require specific metric or evidence)
Each strength must have: specific evidence, magnitude, and duration estimate
Weaknesses: not generic — specific operational or financial gaps with numbers
Rank by materiality: which weakness could become existential?
Opportunities: size the opportunity (TAM, penetration rate, timeline)
Which opportunity has the highest probability of materialisation in 2 years?
Threats: most credible, not laundry list
Probability and impact matrix: rank threats by joint probability x impact
Investment implication: how does SWOT change the BCE?

Output Format:
SWOT with evidence, quantification, and investment implication.
```

### 📊 Excel Model Structure
```text
Sheet 1 SWOT_MATRIX: category, item, evidence, magnitude, duration, materiality
Sheet 2 THREAT_MATRIX: threat, probability, impact, joint_score, monitor_signal
Sheet 3 BCE_IMPACT: how SWOT findings adjust BCE from base case
```

</details>

---

## 🔹 The Technology Disruption & Business Model Innovation R

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior technology strategist assessing disruption risk for incumbent industry players.

Task:
Disruption risk assessment for [INDUSTRY] over the next 5 years.
Disruption framework (Clayton Christensen's documented principles):
Is there a low-end foothold? Where is disruption entering the market?
Is there a new-market foothold? Serving non-consumers?
Performance overshoot: are incumbents delivering more than customers need?
Disruption candidates: identify specific companies or technologies threatening incumbents
Timeline: when could disruption reach mainstream customers?
Incumbent response options: which incumbents are best positioned to respond?
Investment implication: which incumbents are most/least exposed?

Output Format:
Disruption risk assessment with timeline and incumbent exposure ranking.
```

### 📊 Excel Model Structure
```text
Sheet 1 DISRUPTION_ASSESSMENT: disruptor, entry_point, timeline, threat_level
Sheet 2 INCUMBENT_EXPOSURE: company, exposure_score, response_capability, net_risk
Sheet 3 SCENARIO_ANALYSIS: scenario, probability, winner, loser, timeline
```

</details>

---

## 🔹 The Institutional Pricing Power & Revenue Quality Analy

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst specialising in pricing power assessment and revenue quality.

Task:
Pricing power assessment for [COMPANY].
Price history: has the company raised prices above inflation consistently?
Volume response: what happened to volume when prices were raised?
Price/mix analysis: is revenue growth driven by price, volume, or mix?
Gross margin trend: is pricing covering cost inflation (expanding margin = pricing power)?
Customer survey data (if available): price sensitivity and willingness to pay
Competitor pricing: is [COMPANY] the price leader or price taker in its market?
Contract structure: long-term contracts with price escalation clauses?
Pricing power score: 1-10 with evidence

Output Format:
Pricing power scorecard with gross margin analysis and competitor comparison.
```

### 📊 Excel Model Structure
```text
Sheet 1 PRICE_HISTORY: year, price_change, volume_change, gross_margin, inflation
Sheet 2 PRICE_MIX: revenue_growth_decomposition: price, volume, mix by year
Sheet 3 PRICING_POWER_SCORE: dimension, score, evidence, trend
```

</details>

---

## 🔹 The Single Best Investment Thesis Construction Framewor

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior portfolio manager constructing a competitive advantage-based investment thesis.

Task:
Build the single most compelling investment thesis for [SECTOR].
Competitive analysis synthesis: who has the strongest and most improving competitive
position?
Thesis structure:
1. What: which company and current position vs intrinsic value
2. Why: the specific competitive advantage driving the thesis
3. Why now: what is changing that makes this the right time?
4. Catalyst: specific event or metric that will force market recognition
5. Why wrong: most credible bear case with probability
6. Exit: what would cause me to sell?
Pre-mortem: what does the market know that I don't?

Output Format:
Single best thesis in IC memo format with catalyst and pre-mortem.
```

### 📊 Excel Model Structure
```text
Sheet 1 THESIS_SUMMARY: company, thesis, catalyst, timeline, BCE
Sheet 2 BEAR_CASE: mechanism, probability, magnitude, trigger_to_sell
Sheet 3 PREMORTEM: what_market_knows, my_edge, edge_decay_risk
• Moat trajectory (strengthening vs weakening) matters more than current moat width for investment returns.
• Market share trends in key channels predict competitive outcomes 2-3 years ahead of earnings data.
• Porter's Five Forces provides the industry structure context that moat analysis alone misses.
• Character notes: Meera Krishnan (Senior Analyst, Axis Mutual Fund). SBI Life vs HDFC Life. 18%
outperformance. The bancassurance market share chart.
```

</details>

---

