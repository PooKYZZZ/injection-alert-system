# PR7 Controlled CRITICAL WAF Enforcement — document index

The former monolithic plan has been split so the implementation contract, its
rationale, and experimental evidence cannot contradict each other.

1. [Normative implementation contract](PR7_IMPLEMENTATION_SPEC.md)
2. [Design rationale and deferred work](PR7_DESIGN_RATIONALE.md)
3. [T0 feasibility evidence template](PR7_T0_EVIDENCE.md)

Only the implementation contract defines required implementation behaviour.
The synthesis corrections are incorporated and T0 is **complete: GO**. E28
proves controlled source identity and E29 proves process topology and
persistence. T1 and later work require separate authorization, with only
the documented disabled-runtime-IPv6 exception. These documents do not
authorize local `ENFORCE` or hosted, staging, or production activation.
