# PR7 Controlled CRITICAL WAF Enforcement — document index

The former monolithic plan has been split so the implementation contract, its
rationale, and experimental evidence cannot contradict each other.

1. [Normative implementation contract](PR7_IMPLEMENTATION_SPEC.md)
2. [Design rationale and deferred work](PR7_DESIGN_RATIONALE.md)
3. [T0 feasibility evidence template](PR7_T0_EVIDENCE.md)

Only the implementation contract defines required implementation behaviour.
The synthesis corrections are incorporated, but T0 continuation remains
**BLOCKED pending final process-topology proof**. T1 and
later work remain blocked until every foundational T0 gate passes, with only
the documented disabled-runtime-IPv6 exception. These documents do not
authorize local `ENFORCE` or hosted, staging, or production activation.
