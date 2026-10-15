# Consumer examples

- [portfolio_session.py](portfolio_session.py): default multi-token account,
  internal reconciliation and advisory scan. It never invents a trading decision.

The examples below use the explicit legacy task protocol:

- [http_session.py](http_session.py): inspect status, prepare a task, or submit a
  session-authored payload through the existing HTTP client. It supplies no model,
  strategy, signal, agent reports, or automatic retry/trading loop.
- [decision-template.json](decision-template.json): complete top-level submission
  shape with a deliberately unreviewed HOLD. Placeholder task/hash values make it
  non-executable unchanged. It is not evidence of four independent assessments.

Set the existing service's `LAB_API_TOKEN` in the client environment. From an
installed package or the repository root:

```bash
python3 .agents/examples/http_session.py status
python3 .agents/examples/http_session.py prepare --key session-01-prepare-01
python3 .agents/examples/http_session.py submit --file reviewed-submission.json --key session-01-submit-01
```

Review returned schemas/evidence before writing the submission file. Use a stable
key only for identical retries. Do not submit a template as if real research ran.
