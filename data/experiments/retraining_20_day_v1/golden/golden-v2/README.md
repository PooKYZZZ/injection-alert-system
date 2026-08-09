# Golden-v2: LRP records-search controls

This locked golden set evaluates the classifier using the only currently protected
Land Records Portal route:

```text
GET /records/search?query=...
```

The target-route cases use the route's real `query` parameter and cover benign
searches, SQL injection, code injection, other supported attacks, and encoded or
boundary representations. The expected labels and actions use the frozen
CyberTrace label and response-action contracts.

The historical `GET /api/users?page=1&limit=10` false-positive is retained as one
`legacy_regression` case. It is evaluated for regression safety but is excluded
from the `target_case_count` because `/api/users` is not an LRP route.

## Integrity

Do not edit these files after locking. Any correction or additional control must
create a new golden version and regenerate the manifest hashes. Training and
validation data must not contain exact or near-duplicate copies of these cases.

## Scope boundary

This offline set proves model classification and action decisions for prepared
request text. It does not by itself prove that Cloudflare, cloudflared,
ModSecurity, the LRP, the audit bridge, and CyberTrace processed a live request.
That requires a separate controlled local end-to-end smoke test.
