# 🏦 Claude Model Family

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 Prompt 1 — The Institutional Claude Model Selection & Co

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of AI implementation at an institutional asset manager.

Task:
Design a model routing framework for institutional finance tasks.
the fast AI model: bulk/volume tasks (N>20 items, structured extraction, daily monitoring)
the standard AI model: all standard analysis (DCF, earnings, risk, research notes, code)
the advanced reasoning model: complex multi-layer reasoning only (IC memos, sovereign
credit, SWF SAA)
For my task list: [DESCRIBE YOUR MOST COMMON TASKS]
Assign each task to the optimal model with cost and quality rationale.

Output Format:
Model routing table with task, recommended model, rationale, and cost implication.
```

### 📊 Excel Model Structure
```text
Sheet 1 ROUTING_TABLE: task, model, rationale, relative_cost, quality_impact
Sheet 2 COST_ANALYSIS: estimated_tasks_per_month, cost_per_model, total_saving
```

### 💡 Sample Output
```text
ROUTING FRAMEWORK | [DATE]
BULK TASKS → the fast AI model
[TASK 1]: extract metrics from [N] CSVs — speed critical, structured output
STANDARD ANALYSIS → the standard AI model
[TASK 2]: DCF valuation, earnings preview, risk report
COMPLEX REASONING → the advanced reasoning model
[TASK 3]: quarterly IC memo, sovereign credit assessment
COST SAVING vs Opus-for-everything: [X]x reduction at equivalent quality
```

</details>

---

## 🔹 Prompt 2 — The High-Speed Universe Screening & Data Extr

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst using Claude the fast AI model for high-speed bulk financial data
tasks.

Task:
Configure a the fast AI model bulk screening workflow for [UNIVERSE: N
stocks/bonds/funds].
Task: extract [METRICS LIST] from uploaded CSV/data file
Apply filter criteria: [DESCRIBE PASS/FAIL CRITERIA]
Output: structured JSON or CSV with passing names, scores, and flags
Speed requirement: process [N] items in under [X] minutes
Error handling: flag any missing data fields rather than failing silently
Post-processing: rank by composite score, top [N] to Sonnet for deeper analysis

Output Format:
Bulk screening output in structured format ready for Sonnet deep-dive.
```

### 📊 Excel Model Structure
```text
Sheet 1 BULK_RESULTS: ticker, all_extracted_metrics, pass_fail, composite_score
Sheet 2 FLAGGED_ITEMS: items_with_missing_data or_near_threshold
Sheet 3 TOP_N_FOR_DEEPDIVE: highest_scoring_names_for_Sonnet_analysis
```

### 💡 Sample Output
```text
BULK SCREEN | the fast AI model | [N] items | [DATE]
Processed: [N] items
Passing criteria: [X] of [N]
Flagged (missing data): [Y]
TOP 5 FOR SONNET DEEP-DIVE
[TICKER] | Score [X] | [KEY METRICS]
[TICKER] | Score [X] | [KEY METRICS]
```

</details>

---

## 🔹 Prompt 3 — The Institutional Analysis Configuration & Ou

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior analyst configuring Claude the standard AI model for professional-grade analytical
output.

Task:
Configure the standard AI model for [ANALYTICAL TASK] with professional output standards.
Task specification: [DESCRIBE EXACTLY WHAT YOU NEED]
Input: [DESCRIBE DOCUMENTS OR DATA PROVIDED]
Output standards:
Base Case Estimates only (never price targets)
Assumption log required on every analytical output
Risk caveats on all forward-looking statements
Source every key assumption with document reference
Flag any assumption not supported by uploaded documents
Format: [DESCRIBE TABLE STRUCTURE, LENGTH, EXCEL SPECS]
Compliance: [REGULATORY CONTEXT]

Output Format:
Sonnet-optimised analytical output with full compliance conventions applied.
```

### 📊 Excel Model Structure
```text
Sheet 1 ANALYSIS_OUTPUT: primary_findings, assumptions, sources
Sheet 2 ASSUMPTION_LOG: assumption, HIGH/MEDIUM/LOW sensitivity, evidence
Sheet 3 RISK_REGISTER: risk, forward_looking_caveat, monitoring_signal
```

</details>

---

## 🔹 Prompt 4 — The Extended Multi-Layer Reasoning Framework

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Chief investment officer using Claude the advanced reasoning model for complex
institutional reasoning tasks.

Task:
Apply the advanced reasoning model extended reasoning to [COMPLEX ANALYTICAL CHALLENGE].
Use Opus when the task requires:
Multi-step logical chains with interdependent conclusions
Weighing competing frameworks simultaneously (e.g. RRTTLLU across 6 investor types)
Synthesising conflicting evidence to a single recommendation
IC presentation quality reasoning that will face expert challenge
My complex task: [DESCRIBE]
Show reasoning steps explicitly before conclusion
Identify the 3 assumptions most critical to the conclusion

Output Format:
Extended reasoning output with explicit logic chain and critical assumption
identification.
```

### 📊 Excel Model Structure
```text
Sheet 1 REASONING_CHAIN: step, logic, evidence, confidence
Sheet 2 CRITICAL_ASSUMPTIONS: assumption, if_wrong_conclusion_changes_to
Sheet 3 CONCLUSION: recommendation, confidence_level, monitoring_KPIs
```

### 💡 Sample Output
```text
OPUS REASONING | [TASK] | [DATE]
REASONING CHAIN
Step 1: [OBSERVATION] → [LOGICAL INFERENCE]
Step 2: [INFERENCE] + [EVIDENCE] → [INTERMEDIATE CONCLUSION]
Step 3: [INTERMEDIATE] x [CONSTRAINT] → [FINAL CONCLUSION]
CRITICAL ASSUMPTIONS
1. [ASSUMPTION] — if wrong: conclusion reverses
2. [ASSUMPTION] — if wrong: conclusion weakens
CONCLUSION: [RECOMMENDATION] with [X]% confidence
```

</details>

---

## 🔹 Prompt 5 — The Claude Finance Agent Capability Assessmen

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of AI strategy at an institutional firm evaluating Claude for finance workflows.

Task:
Assess Claude's capabilities for [SPECIFIC FINANCE WORKFLOW] using the Finance Agent v1.1
benchmark context.
Evaluate for this workflow:
Multi-step agentic task completion (can Claude chain 5+ steps autonomously?)
Financial calculation accuracy (DCF, WACC, LBO returns)
Document comprehension (can Claude read and extract from 10-K accurately?)
Compliance awareness (does Claude apply BCE language and risk caveats automatically?)
Code generation quality (does Python output run correctly first time?)
My workflow: [DESCRIBE IN DETAIL]
Test cases: [LIST 3 SPECIFIC TASKS YOU WANT EVALUATED]

Output Format:
Capability assessment with pass/fail per dimension and workflow recommendation.
```

### 📊 Excel Model Structure
```text
Sheet 1 CAPABILITY_MATRIX: dimension, test_case, result, confidence, recommendation
Sheet 2 WORKFLOW_FIT: task, suitable_model, confidence, caveat
```

</details>

---

## 🔹 Prompt 6 — The Institutional AI Cost Management & Budget

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of technology at an asset management firm managing Claude API costs.

Task:
Build a cost optimisation framework for [FIRM]'s Claude usage.
Current usage profile: [DESCRIBE TASKS AND VOLUMES]
Cost analysis:
Token consumption per task type (input + output tokens)
Monthly cost at current routing vs optimised routing
Cost per analytical output: current vs optimised
Break-even: at what task volume does Haiku routing pay for itself?
Optimisation recommendations:
Which tasks to move from Opus to Sonnet
Which tasks to move from Sonnet to Haiku
Prompt caching opportunities (repeated context)
Batch API for non-urgent bulk tasks

Output Format:
Cost optimisation plan with projected savings.
```

### 📊 Excel Model Structure
```text
Sheet 1 COST_ANALYSIS: task, volume, current_model, tokens, monthly_cost
Sheet 2 OPTIMISED_ROUTING: task, recommended_model, new_cost, saving_pct
Sheet 3 SAVINGS_SUMMARY: total_current, total_optimised, annual_saving
```

</details>

---

## 🔹 Prompt 7 — The Institutional Multi-Model Pipeline Archit

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
AI architect designing a multi-model workflow for an institutional finance team.

Task:
Design a multi-model pipeline for [WORKFLOW: e.g. earnings season, IC preparation, credit
screening].
Pipeline architecture:
Stage 1 (Haiku): data extraction and structuring from raw inputs
Stage 2 (Sonnet): analysis, scoring, and draft generation
Stage 3 (Opus): final synthesis, IC memo, or complex recommendation
For each stage:
Exact input format and source
Prompt template with [PLACEHOLDERS]
Expected output format feeding next stage
Quality check: what validates the output before passing to next stage?
Human touchpoints: where does the analyst review and approve?

Output Format:
Pipeline architecture with stage-by-stage prompt templates and quality gates.
```

### 📊 Excel Model Structure
```text
Sheet 1 PIPELINE_DESIGN: stage, model, input, output, quality_gate, human_touchpoint
Sheet 2 PROMPT_TEMPLATES: stage, prompt_template_with_placeholders
Sheet 3 TIMELINE: end_to_end_time_estimate per pipeline run
```

</details>

---

## 🔹 Prompt 8 — The Norway GPFG AI-at-Scale Institutional Dep

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Head of responsible investment applying AI at sovereign wealth fund scale.

Task:
Design an AI deployment framework inspired by NBIM Norway GPFG's documented approach.
NBIM documented application (per public statements and annual reports):
ESG screening across 9,000+ portfolio companies
the fast AI model: overnight batch extraction of TCFD metrics from sustainability reports
the standard AI model: escalation reports for responsible investment team
Scale: hundreds of analyst-hours per quarter → automated overnight batch
Design a similar framework for [YOUR ORGANISATION] with [N] portfolio companies.
Automation targets: which monitoring tasks can run overnight?
Human oversight: what decisions must remain with the analyst?
Governance: how are AI outputs reviewed before action?

Output Format:
AI deployment framework with automation targets and governance structure.
```

### 📊 Excel Model Structure
```text
Sheet 1 AUTOMATION_TARGETS: task, current_hours, automated_hours, saving, governance
Sheet 2 OVERNIGHT_BATCH: task, trigger, model, output, review_required
Sheet 3 GOVERNANCE_FRAMEWORK: decision_type, human_required, escalation_path
```

</details>

---

