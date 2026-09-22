# OPNsense Pilot

A self-hosted, read-only-first intelligence and operations platform for OPNsense firewalls: version-aware diagnosis and modernization advice backed by evidence.

## Language

**OPNsense Pilot**:
The project and its deliverable; the Python package is `opnsense_pilot` and the CLI is `opnsense-pilot`.
_Avoid_: OPNsense Operator, `opnsense_operator`, operator (reads as a Kubernetes operator)

**Production trial**:
The narrow, opt-in use of explicitly supported low-risk operations against a real firewall (milestone M5).
_Avoid_: Production pilot, pilot (reserved for the project name)

**Detector**:
A reviewed, deterministic rule that reads collected evidence about one firewall and yields findings, valid only for the releases it has been source-verified against.
_Avoid_: Check, scanner, lint, heuristic

**Finding**:
One detector's result about one firewall: a feature status, a health, the evidence behind them, and a recommended next step.
_Avoid_: Alert, issue, warning, violation

**Feature status**:
Where a configured feature stands in upstream's lifecycle for the installed release (current, legacy but supported, migration available, deprecated, unsupported, unknown). Says nothing about whether it works.
_Avoid_: Legacy status, deprecation level

**Health**:
Whether a configured feature is operating correctly right now. Independent of feature status: a legacy configuration can be healthy and a current one broken. A detector that does not assess health reports it as unknown, never as healthy.
_Avoid_: Status (ambiguous with feature status)

**Abstain**:
A detector returning unknown because the release is outside what it was verified against or required evidence was not collected, naming what is missing. Missing evidence never counts as absence.
_Avoid_: Skip, pass, not applicable
