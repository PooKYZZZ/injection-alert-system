# Panel Attack Testing Rules of Engagement

Status: implemented for the MAIN PC local demonstration workflow.

## Authorized scope

This procedure is limited to the local Injection Alert System checkout and its
Docker services on the MAIN PC. The offline classifier endpoint is
`http://127.0.0.1:8000/api/predict`. Any WAF replay must use the local Compose
target and its approved route; public Cloudflare hostnames are not replay
targets for this procedure.

The checked-in panel catalogue starts from the approved fixtures in
`scripts/fixtures/attack_dataset_samples.json`. A generated variant is a test
candidate until an analyst confirms that its expected label is still valid.

## Allowed activity

- Use only the catalogue cases and one deterministic transformation per case.
- Use only `GET` and `POST` methods present in the approved fixtures.
- Score candidates locally before any WAF replay.
- Use finite batches with a maximum of 100 requests and a maximum runtime of
  120 seconds.
- Keep the request rate at or below 5 requests per second, with a configurable
  additional pause.
- Retry only transient failures, at most once by default, with exponential
  backoff.
- Stop after three consecutive transient failures, when the local stop file is
  present, or when the operator presses Ctrl+C.
- Record model, prediction, policy, WAF, bridge, and persistence evidence as
  separate fields.

## Prohibited activity

- Do not run an unbounded or unattended attack loop.
- Do not send catalogue traffic to `app.cybertracesystems.com`,
  `target.cybertracesystems.com`, or another external host.
- Do not use destructive database, filesystem, command-execution, or callback
  actions. The code-injection cases are classification fixtures only.
- Do not log cookies, API keys, tunnel tokens, or raw request bodies in the
  result report.
- Do not change confidence thresholds, action mapping, the active model, or the
  frozen holdout to improve a result.
- Do not add a candidate to training data until an analyst has verified it.

## Pass and review rules

An approved fixture can pass only when the response is successful, the predicted
label is correct, the returned confidence/tier/action fields are present, and
the action follows the existing policy. A proposed variant remains `REVIEW`
even when its prediction matches. A high or critical confidence mismatch is a
failure and must remain visible in the panel evidence.

Offline reports intentionally leave WAF, bridge, and backend correlation fields
as `NOT_COLLECTED` or blank. Those fields are populated only by a separate,
approved local WAF replay and must not be inferred from the ML response.

## Evidence and cleanup

Generated catalogue inputs and reports belong under the ignored `output/`
directory. The result report stores one-way input hashes and metadata, not raw
request bodies. The active model digest is checked before and after any
approved integration run; no promotion or model replacement is part of this
procedure.
