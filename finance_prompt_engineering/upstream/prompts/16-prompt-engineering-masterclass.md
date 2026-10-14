# 🏦 Prompt Engineering Masterclass

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 Prompt 1 — The Five-Element Institutional Prompt Enginee

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst applying CRAFT Level 4 prompt engineering to institutional finance tasks.

Task:
Rewrite this Level 1 prompt as a CRAFT Level 4 professional prompt:
Level 1 prompt: [PASTE YOUR CURRENT PROMPT HERE]
CRAFT Level 4 requires ALL FIVE elements:
C — Context: fund mandate, benchmark, investment philosophy, regulatory context
R — Role: specific professional identity, seniority, specialisation
A — Action: numbered list of exact deliverables (not 'analyse this company')
F — Format: exact output structure, table headers, length limit, Excel specs
T — Tone: institutional language, BCE only, risk caveats, assumption log
Show the Level 1 → Level 4 transformation side by side
Explain what each CRAFT element adds to output quality

Output Format:
Level 1 vs Level 4 comparison with quality improvement explanation.
```

### 💡 Sample Output
```text
LEVEL 1 (original): '[PASTE ORIGINAL]'
LEVEL 4 (CRAFT):
CONTEXT: You are analysing for [FUND], a [TYPE] fund benchmarked to [INDEX]...
ROLE: You are a [SENIOR ROLE] with [N] years of [SPECIALISATION] experience...
ACTION:
1. [SPECIFIC DELIVERABLE 1]
2. [SPECIFIC DELIVERABLE 2]
...
FORMAT: [TABLE STRUCTURE, LENGTH, EXCEL SPECS]
TONE: Base Case Estimates only. Risk caveats on all forward-looking statements.
QUALITY IMPROVEMENT: Level 4 eliminates [X] minutes of editing per output
```

</details>

---

## 🔹 Prompt 2 — The Step-by-Step Macro Transmission Reasoning

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief investment strategist using chain-of-thought prompting for macro analysis.

Task:
Think through this step-by-step before providing your final answer.
Show ALL reasoning at each step. Conclusions only come after visible reasoning.
Macro scenario: [DESCRIBE PRECISELY: central bank policy, geopolitical event, macro shock]
STEP 1: IMMEDIATE CROSS-ASSET (0-72 hours)
Equities, bonds, currency, gold, commodities
Distinguish risk-on/off from underlying fear/confidence driver
STEP 2: SECTOR EQUITY IMPACT (weeks 1-4)
Which sectors benefit, which hurt? State specific transmission mechanism per sector
STEP 3: PORTFOLIO IMPLICATION
My allocation: [DESCRIBE BY SECTOR/CLASS]
Estimate directional impact and magnitude per sleeve
STEP 4: DURATION RECOMMENDATION
Extend or shorten? By how much? Why?
STEP 5: THREE TACTICAL CHANGES
Specific instruments. Not directional views — specific trades.

Output Format:
Step-by-step reasoning visible before conclusion. Assumption log appended.
```

### 💡 Sample Output
```text
CHAIN-OF-THOUGHT | [SCENARIO] | [DATE]
STEP 1: CROSS-ASSET
[Asset]: [direction] because [specific mechanism]
KEY ASSUMPTION: [critical interpretive assumption]
STEP 2: SECTORS
BENEFIT: [SECTOR] — [specific mechanism]
HURT: [SECTOR] — [specific mechanism]
STEP 3: MY PORTFOLIO
[SLEEVE] [X]%: [direction], est. [+/-X]% because [reason]
STEP 4: DURATION — [EXTEND/SHORTEN] [X]yr via [INSTRUMENT]
STEP 5:
1. [SPECIFIC TRADE]
2. [SPECIFIC TRADE]
3. [SPECIFIC TRADE]
```

</details>

---

## 🔹 Prompt 3 — The Institutional Investment Pre-Mortem Frame

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Lead analyst conducting structured pre-mortem before IC presentation.

Task:
Pre-mortem for [POSITION / INVESTMENT IDEA] from four distinct perspectives.
PERSPECTIVE 1 — BULL ANALYST
Build the strongest version of the thesis.
What are we most right about? What is the specific path to bull BCE?
PERSPECTIVE 2 — BEAR ANALYST
Most credible specific path to 25-35% loss.
Must be mechanistically plausible with specific event sequence and probability.
Non-specific bear case not acceptable.
PERSPECTIVE 3 — RISK MANAGER
Ignoring return potential: 3 most material PORTFOLIO risks from owning this.
Focus: factor concentration, liquidity, correlation with existing holdings.
PERSPECTIVE 4 — INDEPENDENT FIDUCIARY
Questions a prudent CIO would ask before approving. Probe assumptions and sizing.

Output Format:
Four perspectives presented separately. Perspective 2 must be specific and uncomfortable.
```

### 💡 Sample Output
```text
PRE-MORTEM | [COMPANY] [X]% POSITION | [DATE]
PERSPECTIVE 1 — BULL
Most right: [SPECIFIC THESIS ELEMENT]
Bull BCE: [CUR][X] via [SPECIFIC PATH]
PERSPECTIVE 2 — BEAR
Path to -[X]%: [EVENT 1] → [EVENT 2] → loss
Probability: [X]%
IC should define: exit if [SPECIFIC TRIGGER]
PERSPECTIVE 3 — RISK MANAGER
1. [PORTFOLIO RISK 1]: [QUANTIFICATION]
2. [PORTFOLIO RISK 2]
3. [PORTFOLIO RISK 3]
PERSPECTIVE 4 — FIDUCIARY
Q1: [PROBING QUESTION]
Q2: [SIZING QUESTION]
Q3: [MONITORING QUESTION]
```

</details>

---

## 🔹 Prompt 4 — The Institutional Compliance Convention Appli

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst applying compliance conventions to all AI-generated outputs.

Task:
Apply these compliance conventions to ALL analytical output:
1. Opening header: 'DRAFT — AI-Assisted Analysis | Analyst Review Required Before Use'
2. Valuations: 'Base Case Estimate' only (never 'price target' or 'fair value')
3. Forward-looking statements: append 'This is an estimate based on [assumptions]. Actual
outcomes may differ materially.'
4. Assumption log: every key assumption, rated HIGH/MEDIUM/LOW sensitivity
5. Closing footer: 'For institutional internal use. Not investment advice. Not SEBI
registered. Claude® is Anthropic PBC. Based on information as of [DATE].'
My analytical request: [PASTE YOUR ANALYSIS REQUEST HERE]

Output Format:
Compliant analytical output with all required headers, caveats, and assumption log.
```

### 💡 Sample Output
```text
DRAFT — AI-Assisted Analysis | Analyst Review Required Before Use
[ANALYTICAL CONTENT WITH BCE LANGUAGE THROUGHOUT]
ASSUMPTION LOG
1. [ASSUMPTION] — HIGH sensitivity: [impact per unit change]
2. [ASSUMPTION] — MEDIUM
3. [ASSUMPTION] — LOW
Forward-looking estimates carry material uncertainty. Based on publicly available
information.
For institutional internal use. Not investment advice. Not SEBI registered.
Claude® is Anthropic PBC. As of [DATE].
```

</details>

---

## 🔹 Prompt 5 — The Institutional Few-Shot Learning & Output

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst using few-shot examples to calibrate Claude output quality.

Task:
Use these examples to calibrate your output for [TASK TYPE].
EXAMPLE 1 (HIGH QUALITY OUTPUT):
Input: [DESCRIBE EXAMPLE INPUT]
Output: [PASTE EXAMPLE OF GOOD OUTPUT YOU HAVE PREVIOUSLY ACCEPTED]
EXAMPLE 2 (ANOTHER GOOD EXAMPLE):
Input: [DESCRIBE EXAMPLE INPUT]
Output: [PASTE SECOND EXAMPLE]
NEGATIVE EXAMPLE (WHAT NOT TO DO):
Input: [DESCRIBE INPUT]
Output: [PASTE EXAMPLE OF OUTPUT THAT WAS TOO GENERIC OR INCORRECT]
Why it failed: [EXPLAIN WHAT WAS WRONG]
Now apply this standard to my actual request: [YOUR ACTUAL REQUEST]
Match the quality and format of the good examples above.

Output Format:
Output calibrated to the quality standard of the few-shot examples provided.
```

### 💡 Sample Output
```text
[OUTPUT MATCHING THE QUALITY STANDARD OF FEW-SHOT EXAMPLES]
SELF-CHECK: Does this output match the format of Example 1? [YES]
Does it avoid the failure mode of the Negative Example? [YES]
Would it pass the PM review standard? [YES/NO with specific gap if NO]
```

</details>

---

## 🔹 Prompt 6 — The Institutional Team Prompt Library Design

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of research building a systematic prompt library for institutional research team.

Task:
Design a prompt library for [TEAM OF N ANALYSTS] covering [COVERAGE UNIVERSE].
Library structure:
Category 1: Screening prompts (by methodology: Graham, Lynch, Multi-Factor, etc.)
Category 2: Valuation prompts (DCF, LBO, SOTP, comps)
Category 3: Risk prompts (stress test, tail risk, factor analysis)
Category 4: Earnings prompts (preview, tone, post-earnings)
Category 5: ESG prompts (TCFD, SFDR, engagement)
Governance framework:
Version control: how to track prompt improvements
Testing: how to validate a new prompt before adding to library
Compliance: review process before any new prompt goes live
Onboarding: how to train new analysts on the library
Quality standard: what makes a prompt library-worthy vs a one-off?

Output Format:
Prompt library structure with governance framework and quality standards.
```

### 📊 Excel Model Structure
```text
Sheet 1 LIBRARY_STRUCTURE: category, prompt_name, model, last_updated, version
Sheet 2 GOVERNANCE: step, owner, timeline, quality_gate
Sheet 3 ONBOARDING_GUIDE: analyst_level, required_prompts, training_sequence
```

</details>

---

## 🔹 Prompt 7 — The AI Output Quality Control & Review Protoc

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst building a systematic output validation process for institutional AI use.

Task:
Design an output validation protocol for [OUTPUT TYPE: research note / risk report / IC
memo].
Pre-distribution checklist:
[ ] Base Case Estimate language used throughout (no price targets)
[ ] Risk caveats on all forward-looking statements
[ ] Assumption log present and complete
[ ] All key assumptions sourced to specific documents
[ ] No MNPI used as input (compliance check)
[ ] SEBI non-registration noted where required
[ ] Factual verification: spot-check 3 specific data points against source
[ ] Logical consistency: does the conclusion follow from the analysis?
[ ] Peer review: has a second analyst reviewed?
Failure protocol: if any check fails, what happens?

Output Format:
Validation checklist with failure protocol and quality tracking.
```

### 📊 Excel Model Structure
```text
Sheet 1 VALIDATION_CHECKLIST: check, pass_fail, reviewer, timestamp
Sheet 2 FAILURE_LOG: check_failed, description, action_taken, resolution
Sheet 3 QUALITY_METRICS: pass_rate_by_check, most_common_failures, trend
```

</details>

---

## 🔹 Prompt 8 — The Investment Committee Memo CRAFT Applicati

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Lead analyst constructing a full IC memo using CRAFT Level 4 prompt engineering.

Task:
Build a complete IC memo for [COMPANY/POSITION CHANGE] using CRAFT Level 4.
CRAFT APPLICATION:
Context: [FUND], benchmarked to [INDEX], [PHILOSOPHY] orientation
Role: Senior analyst with [N]yr coverage of [SECTOR], CFA/FRM qualified
Action (numbered deliverables):
1. Three-sentence thesis: what, why, why now
2. Key metrics: BCE range, upside/downside, primary multiples
3. Base/bull/bear scenarios with probability estimates
4. Three thesis-critical KPIs to monitor
5. Two bear cases with specific mechanistic paths
6. Position size with explicit sizing rationale
7. Exit criteria: specific conditions that trigger full exit
Format: max 500 words, decision table at top
Tone: IC language, BCE only, assumption log appended

Output Format:
Full IC memo in 500 words. Decision table at top. Assumption log at end.
```

### 📊 Excel Model Structure
```text
Sheet 1 IC_SUMMARY: thesis, BCE, scenarios, KPIs, position_size
Sheet 2 ASSUMPTION_LOG: assumption, sensitivity, source
Sheet 3 MONITORING_PLAN: KPI, current, confirm_threshold, exit_threshold
```

### 💡 Sample Output
```text
AI advanced reasoning model
```

</details>

---

