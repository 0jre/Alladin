# 🏦 The ESG & Climate Desk

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 The TCFD Four-Pillar Portfolio Climate Risk & Alignment

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
ESG analyst preparing an institutional TCFD-aligned portfolio climate disclosure.

Task:
TCFD four-pillar analysis for [PORTFOLIO]. Allocation: [LIST SECTORS AND WEIGHTS]
PILLAR 1 GOVERNANCE: board and management climate oversight structures
PILLAR 2 STRATEGY: physical and transition risk by scenario
1.5°C orderly: which sectors benefit, which face stranded asset risk?
3°C+ disorderly: physical risk (flood, heat, water) and demand disruption
PILLAR 3 RISK MANAGEMENT: climate integration in investment process
PILLAR 4 METRICS (all required):
Carbon footprint: tCO2e per [CUR]1M invested
WACI: Weighted Average Carbon Intensity (tCO2e per [CUR]1M revenue)
Portfolio temperature alignment estimate
Net-zero progress vs base year
Top 3 holdings requiring priority engagement with specific asks

Output Format:
TCFD four-pillar report suitable for annual report inclusion.
```

### 📊 Excel Model Structure
```text
Sheet 1 TCFD_SUMMARY: pillar, finding, RAG, action, deadline
Sheet 2 EMISSIONS_DATA: company, weight, Scope12, WACI, temp_alignment, flag
Sheet 3 ENGAGEMENT_TRACKER: company, issue, request, deadline, status
```

### 💡 Sample Output
```text
TCFD | [DATE]
PILLAR 2 STRATEGY
1.5°C: [Sector A] faces stranded asset risk. [Sector B] benefits.
3°C+: [Sector C] exposed to [flood/heat/water] in [geographies].
PILLAR 4 METRICS
Carbon Footprint: [X] tCO2e/[CUR]1M vs benchmark [Y]
WACI: [X] tCO2e/[CUR]1M rev | Temp Alignment: [X]°C (target: <[Y]°C)
TOP 3 ENGAGEMENTS
1. [COMPANY] ([X]%, [X]% portfolio emissions): [SPECIFIC REQUEST]
```

</details>

---

## 🔹 The SFDR Article 8 vs Article 9 Classification & Gap An

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
ESG compliance specialist reviewing fund classification under EU SFDR.

Task:
SFDR classification review for [FUND NAME].
Fund: objective [DESCRIBE], ESG screening [DESCRIBE],
SI proportion [X]%, PAI indicators [reported/not], DNSH [conducted/not]
Review against ESMA Article 9 requirements:
1. Investment objective language: does it state 'primary objective'? (not 'consideration')
2. SI proportion: is it above 50% (ESMA guidance minimum for credible Article 9)?
3. PAI indicators: all mandatory PAIs reported?
4. DNSH: conducted, documented, included in pre-contractual annex?
5. Taxonomy alignment: % disclosed where required?
Greenwashing risk if Article 9 claimed prematurely
Timeline to legitimate qualification

Output Format:
Classification review with specific gap analysis and remediation plan.
```

### 📊 Excel Model Structure
```text
Sheet 1 CLASSIFICATION_CHECKLIST: requirement, current_status, gap, fix, timeline
Sheet 2 DISCLOSURE_TRACKER: document, current_language, required_language, priority
```

### 💡 Sample Output
```text
SFDR REVIEW | [FUND] | [DATE]
CURRENT: ARTICLE [8/9]
GAPS TO ARTICLE 9 (if applicable)
1. LANGUAGE: Current '[EXACT]' vs Required '[PRIMARY OBJECTIVE]' — HIGH risk
2. SI PROPORTION: [X]% vs required [Y]% minimum
3. DNSH: [not documented]
GREENWASHING RISK: HIGH if Article 9 claimed before all gaps closed.
TIMELINE: [X] months with focused remediation
```

</details>

---

## 🔹 The ISSB S1 General Sustainability & S2 Climate Risk Di

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior ESG analyst preparing ISSB S1/S2 compliant sustainability disclosure.

Task:
ISSB S1 and S2 disclosure framework for [COMPANY/PORTFOLIO].
ISSB S1 (General Sustainability):
Governance: sustainability oversight at board and management level
Strategy: material sustainability risks and opportunities affecting value
Risk management: how sustainability risks are identified and managed
Metrics: industry-specific sustainability metrics (SASB industry standards)
ISSB S2 (Climate):
Scope 1, 2, 3 GHG emissions (Scope 3 for significant categories)
Climate scenario analysis: 1.5°C and 3°C+ scenarios
Climate-related transition and physical risks
Climate-related targets: net zero commitment and interim milestones

Output Format:
ISSB S1/S2 disclosure framework with material risks and climate scenarios.
```

### 📊 Excel Model Structure
```text
Sheet 1 S1_DISCLOSURE: dimension, finding, materiality, current_practice, gap
Sheet 2 S2_EMISSIONS: Scope_1, Scope_2, Scope_3_categories, total, vs_target
Sheet 3 CLIMATE_SCENARIOS: scenario, physical_risk, transition_risk, financial_impact
```

</details>

---

## 🔹 The Portfolio Net Zero Pathway & Science-Based Targets

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior climate strategist assessing portfolio net zero alignment and pathway.

Task:
Net zero alignment assessment for [PORTFOLIO].
Current emissions baseline: total portfolio emissions [tCO2e], year [BASELINE YEAR]
Portfolio temperature alignment: what temperature does current portfolio imply?
Net zero pathway: required annual reduction rate to reach net zero by 2050
Current progress: % reduction vs baseline, vs required pathway
Science-Based Targets (SBTi): which portfolio companies have approved targets?
% of portfolio by weight with SBTi targets
% with net zero commitments (without SBTi verification)
Gap analysis: holdings that most undermine net zero alignment
Action plan: engagement priorities and divestment thresholds

Output Format:
Net zero pathway with gap analysis and action plan.
```

### 📊 Excel Model Structure
```text
Sheet 1 NET_ZERO_PATHWAY: year, required_emissions, actual, gap, on_track
Sheet 2 SBTI_COVERAGE: company, weight, SBTi_status, net_zero_target
Sheet 3 ENGAGEMENT_PRIORITIES: company, emissions_pct, gap_to_pathway, action
```

</details>

---

## 🔹 The Institutional ESG Engagement & Active Ownership Pro

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of stewardship designing systematic ESG engagement for institutional portfolio.

Task:
ESG engagement framework for [PORTFOLIO].
Engagement prioritisation: top 10 holdings by:
Emissions concentration (% of total portfolio emissions)
ESG score improvement potential (laggards in sector with poor practices)
Systemic issues (issues affecting entire portfolio, not just one company)
For each priority engagement:
Specific issue with evidence
Specific ask: what change is requested and by when?
Escalation ladder: dialogue → voting against board → co-filing → divestment
Voting policy: proxy voting guidelines for key ESG resolutions
Collaborative engagement: Climate Action 100+, IIGCC, other initiatives
Reporting: how engagement outcomes are disclosed to beneficiaries

Output Format:
Engagement framework with prioritised company list and escalation protocol.
```

### 📊 Excel Model Structure
```text
Sheet 1 ENGAGEMENT_LIST: company, issue, request, deadline, escalation_trigger
Sheet 2 VOTING_POLICY: resolution_type, guideline, rationale
Sheet 3 OUTCOME_TRACKER: company, engagement_start, progress, outcome
```

</details>

---

## 🔹 The EU Taxonomy Revenue Alignment & Green Revenue Frame

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior ESG analyst assessing EU Taxonomy alignment for equity portfolio.

Task:
EU Taxonomy alignment analysis for [PORTFOLIO].
Taxonomy-aligned revenue: % of each holding's revenue in taxonomy-aligned activities
DNSH assessment: do activities meet 'Do No Significant Harm' criteria?
Minimum social safeguards: labour rights, human rights compliance
Six environmental objectives:
Climate change mitigation | Climate change adaptation
Sustainable water | Circular economy | Pollution prevention | Biodiversity
Portfolio taxonomy alignment: weighted average % of taxonomy-aligned revenue
Disclosure: portfolio taxonomy alignment %, by objective
Gaps: which holdings have insufficient taxonomy disclosure?

Output Format:
Taxonomy alignment analysis with portfolio % and disclosure gaps.
```

### 📊 Excel Model Structure
```text
Sheet 1 TAXONOMY_ALIGNMENT: company, weight, aligned_pct, objective, evidence
Sheet 2 PORTFOLIO_SUMMARY: weighted_alignment_pct, by_objective
Sheet 3 DISCLOSURE_GAPS: companies_lacking_adequate_taxonomy_disclosure
```

</details>

---

## 🔹 The Physical Climate Risk & Asset Vulnerability Analysi

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior climate risk analyst assessing physical climate risk for investment portfolios.

Task:
Physical climate risk assessment for [PORTFOLIO].
Risk categories:
Acute: floods, hurricanes, wildfires (event-driven)
Chronic: sea level rise, temperature rise, rainfall changes (trend-driven)
For each major holding: identify primary physical risk by geography
IPCC scenarios: 1.5°C, 2.0°C, 4.0°C physical risk comparison
Asset exposure: % of portfolio exposed to high physical risk geographies
Time horizon: risks materialising in 5yr, 10yr, 20yr timeframes
Financial impact: estimated insurance costs, asset impairment, revenue disruption
Mitigation: which holdings have disclosed adaptation plans?

Output Format:
Physical risk map with holding exposure and financial impact estimates.
```

### 📊 Excel Model Structure
```text
Sheet 1 PHYSICAL_RISK_MAP: company, geography, risk_type, severity, financial_impact
Sheet 2 PORTFOLIO_EXPOSURE: pct_high_risk, pct_medium_risk, pct_low_risk by risk_type
Sheet 3 ADAPTATION_PLANS: company, plan_disclosed, adequacy, engagement_needed
```

</details>

---

## 🔹 The ESG-Integrated Investment Universe Screen & Scoring

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior ESG analyst integrating ESG factors into fundamental investment screening.

Task:
ESG-integrated screen for [UNIVERSE].
ESG score sources: MSCI ESG, Sustainalytics, or company disclosure
ESG integration approach:
Exclusion: remove companies below ESG score threshold or in excluded sectors
Integration: ESG adjustment to valuation (discount rate, terminal growth rate)
Tilting: overweight high ESG, underweight low ESG within benchmark
Material ESG factors by sector (SASB materiality map):
Banks: data privacy, financial inclusion, governance
Energy: GHG emissions, water, safety
Technology: data privacy, labour practices, product governance
ESG score vs returns: any correlation in this universe historically?
PAI indicators: primary adverse impact indicators as required by SFDR

Output Format:
ESG-integrated ranking with exclusions and material factor analysis.
```

### 📊 Excel Model Structure
```text
Sheet 1 ESG_SCREEN: ticker, ESG_score, ESG_momentum, exclusion_flag, tilt
Sheet 2 MATERIAL_FACTORS: sector, material_ESG_factors, evidence, scores
Sheet 3 PAI_INDICATORS: indicator, portfolio_value, benchmark, gap
• SFDR Article 9 precision: 'primary objective' in the investment objective, not 'consideration'. Three words,
EUR 80 million.
• TCFD Pillar 4 metrics reveal hidden concentration: one small position can account for 31% of total portfolio
emissions.
• ISSB S1/S2 is becoming mandatory for public company reporting globally — align to both TCFD and ISSB.
• Character notes: Anjali Singh (Fund Manager, Mirabilis Capital Europe). EUR 2.8 billion fund. EUR 80
million redemptions.
```

</details>

---

