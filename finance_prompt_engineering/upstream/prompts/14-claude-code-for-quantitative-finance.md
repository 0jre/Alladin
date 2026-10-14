# 🏦 Claude Code for Quantitative Finance

Navigate back to [Awesome Claude Finance Prompts](../README.md).

---

## 🔹 Prompt 1 — The Institutional Monte Carlo Portfolio VaR I

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative risk engineer building professional-grade simulation tools.

Task:
Write a complete Monte Carlo portfolio VaR engine in Python.
Technical requirements:
10,000 simulations, 252-trading-day horizon
Cholesky decomposition for correlation (explain rationale in docstring)
Student-t distribution, [N] degrees of freedom (explain choice in docstring)
Asset classes: [LIST]
Outputs: VaR 95%, VaR 99%, CVaR/Expected Shortfall at both levels, max drawdown
Pre-built stress scenarios: 2008 GFC, 2020 COVID, 2022 Rate Shock
CSV export with columns: [LIST YOUR REQUIRED COLUMNS]
Code quality:
Comprehensive docstrings explaining WHY (methodology) not just WHAT
Unit tests covering convergence, boundary conditions, known analytical solutions
Modular structure: stress scenarios as separate importable functions

Output Format:
Complete, runnable Python. All docstrings must explain methodological decisions.
```

### 💡 Sample Output
```text
import numpy as np
import scipy.stats as stats
def monte_carlo_var(weights, cov_matrix, mu, n_sim=10000, horizon=252, dof=5):
'''
Institutional Monte Carlo VaR Engine
Cholesky: preserves empirical correlation (critical in 2022-style rate shocks
where equity-bond correlation turned positive)
Student-t dof=5: empirically calibrated to equity tail events
(normal distribution underestimates 99th percentile loss by ~3-5x)
Returns: dict(VaR_95, VaR_99, CVaR_95, CVaR_99, max_drawdown)
'''
L = np.linalg.cholesky(cov_matrix / 252)
terminal = np.zeros(n_sim)
for i in range(n_sim):
z = stats.t.rvs(df=dof, size=(horizon, len(weights)))
r = (L @ z.T).T + (mu / 252)
terminal[i] = np.prod(1 + r @ weights) - 1
return {'VaR_95': np.percentile(terminal, 5),
'VaR_99': np.percentile(terminal, 1),
'CVaR_95': terminal[terminal<=np.percentile(terminal,5)].mean()}
```

</details>

---

## 🔹 Prompt 2 — The Python DCF Model Build & Sensitivity Tabl

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst automating DCF model construction and sensitivity analysis.

Task:
Write a complete Python DCF model automation script.
Inputs (from CSV or direct parameters):
Revenue base, growth rates by year (5yr)
EBITDA margin by year
Capex as % revenue, NWC change as % revenue change
D&A; as % revenue
WACC (or components: RF, ERP, beta, Kd, tax rate, weights)
Terminal growth rate | Exit multiple (both methods)
Outputs:
FCF schedule by year with all line items
Enterprise value via GGM and exit multiple
3x3 sensitivity table: WACC (low/mid/high) x TGR (low/mid/high)
Export to Excel with formatted sensitivity table
Code must have docstrings explaining every key formula

Output Format:
Complete Python DCF automation with Excel export.
```

### 💡 Sample Output
```text
import pandas as pd
import numpy as np
def build_dcf(revenue_base, growth_rates, ebitda_margins,
capex_pct, nwc_pct, da_pct, wacc, tgr, exit_mult):
'''
Institutional DCF Model
FCF = NOPAT + D&A; - Capex - Delta_NWC
NOPAT = EBIT x (1 - tax_rate)
Terminal Value: average of GGM and exit multiple
'''
years = len(growth_rates)
revenue = [revenue_base]
for g in growth_rates:
revenue.append(revenue[-1] * (1 + g))
revenue = revenue[1:]
ebitda = [r * m for r, m in zip(revenue, ebitda_margins)]
# ... full implementation
return {'fcf_schedule': fcf, 'enterprise_value': ev, 'sensitivity': sens_table}
```

</details>

---

## 🔹 Prompt 3 — The Options Pricing & Greeks Calculator Frame

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst building options analytics for institutional derivatives desk.

Task:
Write a complete Black-Scholes options pricing and Greeks calculator in Python.
Implement:
Black-Scholes call and put pricing (explain formula assumptions in docstring)
All five Greeks: Delta, Gamma, Theta, Vega, Rho
Implied volatility solver (Newton-Raphson, with convergence docstring)
Put-Call parity verification
Greeks surface: plot Delta and Gamma across strike range
Portfolio Greeks aggregation: sum Greeks across multiple positions
Sensitivity: how do Greeks change as spot moves +/-[X]%?
Institutional context: for FX options overlay on equity portfolio
Docstrings must explain: why Black-Scholes assumptions matter for real trading

Output Format:
Complete Python options library with Greeks and IV solver.
```

### 💡 Sample Output
```text
from scipy.stats import norm
import numpy as np
def black_scholes(S, K, T, r, sigma, option_type='call'):
'''
Black-Scholes Formula
Assumptions: log-normal returns, constant vol, no dividends, frictionless markets
Real-world caveat: vol smile violates constant vol assumption
For institutional use: always verify with market IV, not historical
d1 = (ln(S/K) + (r + 0.5*sigma^2)*T) / (sigma*sqrt(T))
'''
d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
d2 = d1 - sigma*np.sqrt(T)
if option_type == 'call':
return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)
```

</details>

---

## 🔹 Prompt 4 — The Fama-French Multi-Factor Model Python Imp

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst implementing the Fama-French factor model for portfolio analysis.

Task:
Implement the Fama-French 3-factor (and optionally 5-factor) model in Python.
Fama-French 3-factor (documented academic model):
Market factor: Rm - Rf (excess market return)
SMB: Small Minus Big (size factor)
HML: High Minus Low (value factor)
Model: R_portfolio - Rf = alpha + beta_mkt*(Rm-Rf) + beta_SMB*SMB + beta_HML*HML
5-factor additions:
RMW: Robust Minus Weak (profitability)
CMA: Conservative Minus Aggressive (investment)
Outputs:
Factor loadings (betas) with t-statistics
Alpha: risk-adjusted excess return
R-squared: % of variance explained by factors
Factor exposure plot across time

Output Format:
Complete Fama-French factor model with statistical output.
```

### 📊 Excel Model Structure
```text
Sheet 1 FACTOR_LOADINGS: factor, beta, t_stat, p_value, significance
Sheet 2 PERFORMANCE: alpha, R_squared, information_ratio, tracking_error
Sheet 3 ROLLING_BETAS: factor loadings rolling 12-month window
```

</details>

---

## 🔹 Prompt 5 — The Institutional Investment Strategy Backtes

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative analyst building a systematic strategy backtesting framework.

Task:
Build a backtesting framework for [STRATEGY DESCRIPTION] in Python.
Framework requirements:
Data ingestion: price and fundamental data from CSV
Signal generation: [DESCRIBE YOUR SIGNAL LOGIC]
Position sizing: [EQUAL WEIGHT / RISK PARITY / SIGNAL STRENGTH WEIGHTED]
Transaction costs: [X]bps per trade
Rebalancing: [MONTHLY / QUARTERLY / ON SIGNAL]
Performance metrics:
Annualised return, Sharpe ratio, Sortino ratio, Calmar ratio
Maximum drawdown with drawdown duration
Rolling 12-month return distribution
Turnover and transaction cost drag
Bias checks: survivorship bias, look-ahead bias documentation

Output Format:
Complete backtesting engine with performance attribution.
```

### 📊 Excel Model Structure
```text
Sheet 1 PERFORMANCE: annual_return, Sharpe, Sortino, max_drawdown, Calmar
Sheet 2 RETURNS_SERIES: date, strategy_return, benchmark_return, active_return
Sheet 3 DRAWDOWN_ANALYSIS: drawdown_periods, duration, magnitude, recovery
```

</details>

---

## 🔹 Prompt 6 — The Python Portfolio Risk Attribution & Decom

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative risk analyst building risk attribution tools for institutional portfolio.

Task:
Build a risk attribution engine in Python for [PORTFOLIO].
Risk decomposition:
Total portfolio volatility decomposed by position
Marginal contribution to risk (MCTR) per holding
Factor risk: systematic vs idiosyncratic risk split
Correlation contribution: how much does each pair correlation add to total risk?
Attribution metrics:
% risk contribution per position (should sum to 100%)
Risk concentration: is the top 5 positions contributing >50% of risk?
Risk-adjusted position sizing: optimal weights if targeting equal risk contribution
Output: risk attribution dashboard suitable for IC review

Output Format:
Risk attribution engine with MCTR and factor decomposition.
```

### 📊 Excel Model Structure
```text
Sheet 1 RISK_ATTRIBUTION: ticker, weight, vol, MCTR, pct_risk_contribution
Sheet 2 FACTOR_DECOMPOSITION: systematic_risk, idiosyncratic_risk, R_squared
Sheet 3 CONCENTRATION: top5_risk_contribution, HHI_of_risk, equal_risk_weights
```

</details>

---

## 🔹 Prompt 7 — The Institutional Performance Analytics & Att

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Senior performance analyst building a comprehensive performance analytics tool.

Task:
Build a complete performance analytics suite in Python for [PORTFOLIO].
Return calculations:
Time-weighted return (TWR) and money-weighted return (MWR)
Gross and net of fees
Annualised returns: 1yr, 3yr, 5yr, since inception
Risk-adjusted metrics:
Sharpe, Sortino, Calmar, Omega, Treynor ratios
Information ratio vs benchmark
Jensen's alpha
Attribution (BHB):
Allocation, selection, interaction effects by sector
Which sector drove outperformance/underperformance?
GIPS-ready output format

Output Format:
Complete performance analytics with GIPS-ready output.
```

### 📊 Excel Model Structure
```text
Sheet 1 RETURNS: TWR, MWR, gross, net by period
Sheet 2 RISK_METRICS: all ratios with peer comparison
Sheet 3 BHB_ATTRIBUTION: sector, allocation, selection, interaction, total
```

</details>

---

## 🔹 Prompt 8 — The Financial Data Extraction & Processing Pi

<details>
<summary><b>Click to expand prompt template</b></summary>

**📋 Copy & Paste this Prompt into Claude:**

```text
Role:
Quantitative developer building a financial data pipeline for institutional research.

Task:
Build a data pipeline in Python for [DATA SOURCE: Bloomberg CSV / SEC EDGAR / manual
input].
Pipeline stages:
Ingestion: read raw data from [SOURCE FORMAT]
Validation: check for missing values, outliers, data type errors
Transformation: standardise column names, currency conversion, date normalisation
Enrichment: calculate derived metrics (EV = mkt cap + net debt, FCF = OCF - capex)
Output: clean CSV or Excel ready for analysis
Error handling: log all data quality issues with severity (CRITICAL/WARNING/INFO)
Scheduling: can this run as a daily batch job?
Documentation: docstrings explaining every transformation decision

Output Format:
Complete data pipeline with validation, transformation, and scheduling.
```

### 📊 Excel Model Structure
```text
Sheet 1 PIPELINE_OUTPUT: all_derived_metrics, data_quality_flags
Sheet 2 DATA_QUALITY_LOG: field, issue, severity, records_affected
Sheet 3 DERIVED_METRICS: formula, source_fields, validation_test
```

</details>

---

