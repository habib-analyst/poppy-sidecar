"""Compliance testbed: does your agent respect the declared scopes?

Give it a poppy.json and a trace of what your test agent did (or plans to
do). It answers two questions:

  1. RESPECT: did any action need a scope the sign-in didn't grant?
     (SCOPE_OVERREACH) or touch an interface the business never declared?
     (UNDECLARED_INTERFACE)
  2. REACHABILITY: which declared interfaces did the trace never exercise?
     (a gap in your test coverage, not a violation)

A trace is JSON: {"granted_scopes": [...], "actions": [{"interface",
"action", "scope_needed", "signin_type"}]}. scope_needed may be omitted
(None) and then the PAP verb heuristic decides (reads -> poppy:read,
everything else -> poppy:write, fail-closed); "" marks an explicitly
public action. Testbed policy: a signed_out (guest) session may read;
any action needing poppy:write (or a custom scope) without a sign-in
is SCOPE_OVERREACH. The trace's granted_scopes are authoritative — the
user may approve fewer scopes than the sign-in type allows (spec §4.4).
"""

import json

from poppy_sidecar.core import PAPAdapter, AgentTrace, conformance_report


class TestbedReport:
    def __init__(self, violations, coverage, unreachable, n_actions):
        self.violations = violations
        self.coverage = coverage
        self.unreachable = unreachable
        self.n_actions = n_actions

    @property
    def passed(self):
        return not self.violations

    def to_dict(self):
        return {
            "passed": self.passed,
            "n_actions": self.n_actions,
            "violations": [v.to_dict() for v in self.violations],
            "coverage": self.coverage,
            "unreachable": self.unreachable,
        }

    def summary(self):
        lines = ["testbed: %d actions, %d violations"
                 % (self.n_actions, len(self.violations))]
        for v in self.violations:
            lines.append("  VIOLATION %s: %s — %s"
                         % (v.code, v.action.action, v.detail))
        if self.unreachable:
            lines.append("  unreachable declared interfaces (no trace coverage): %s"
                         % ", ".join(self.unreachable))
        lines.append("  coverage: %s" % self.coverage)
        lines.append("RESULT: %s" % ("PASS" if self.passed else "FAIL"))
        return "\n".join(lines)


def run_testbed(poppy_doc, trace):
    """Run the compliance testbed.

    poppy_doc: parsed poppy.json dict. trace: AgentTrace or dict.
    """
    if isinstance(trace, dict):
        trace = AgentTrace.from_dict(trace)
    doc = PAPAdapter(poppy_doc)
    violations, cov = conformance_report(doc, trace)
    return TestbedReport(violations, cov["coverage"], cov["unreachable"],
                         len(trace.actions))


def load_trace_file(path):
    with open(path, encoding="utf-8") as f:
        return AgentTrace.from_dict(json.load(f))
