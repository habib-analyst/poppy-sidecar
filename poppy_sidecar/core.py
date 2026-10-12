"""Protocol-agnostic declare-and-test core.

The hedge against the protocol war (PAP vs Visa TAP vs whatever comes next):
every agent-commerce protocol answers the same two questions —

  1. DECLARE: what does the business expose, and under which grants?
  2. TEST: did the agent's trace stay inside the declaration?

``DiscoveryDoc`` models (1), ``AgentTrace`` models (2), and
``conformance_report`` runs the check. PAP plugs in via ``PAPAdapter``;
a Visa-TAP adapter would plug in the same way (see docs/PROTOCOL_HEDGE.md).
"""

from poppy_sidecar import schema as S


class AttemptedAction:
    """One thing a test agent did (or plans to do).

    interface: which declared interface it used, e.g. "api:orders",
        "web", "agent".
    action: human-readable name, e.g. "cancel_booking".
    scope_needed: the account scope this action requires, e.g. "poppy:write".
        "" means explicitly public (no account scope). None (default) means
        "let the protocol heuristic decide".
    signin_type: which sign-in the session used: "direct", "device",
        "mediated", or "signed_out".
    """

    def __init__(self, interface, action, scope_needed=None, signin_type="signed_out"):
        self.interface = interface
        self.action = action
        self.scope_needed = scope_needed
        self.signin_type = signin_type

    def to_dict(self):
        return {
            "interface": self.interface,
            "action": self.action,
            "scope_needed": self.scope_needed,
            "signin_type": self.signin_type,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            interface=d.get("interface", ""),
            action=d.get("action", ""),
            scope_needed=d.get("scope_needed"),  # None -> heuristic; "" -> public
            signin_type=d.get("signin_type", "signed_out"),
        )


class AgentTrace:
    """An ordered list of attempted actions plus the scopes actually granted."""

    def __init__(self, actions=(), granted_scopes=()):
        self.actions = list(actions)
        self.granted_scopes = list(granted_scopes)

    def to_dict(self):
        return {
            "actions": [a.to_dict() for a in self.actions],
            "granted_scopes": self.granted_scopes,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            actions=[AttemptedAction.from_dict(a) for a in d.get("actions", [])],
            granted_scopes=d.get("granted_scopes", []),
        )


class DiscoveryDoc:
    """Abstract declaration side. Subclass per protocol."""

    #: machine name of the protocol, e.g. "pap/0.1"
    protocol = "abstract"

    def declared_interfaces(self):
        """List of interface ids the business exposes, e.g. ["api:orders", "web"]."""
        raise NotImplementedError

    def declared_scopes(self):
        """Map scope name -> description for every scope the doc mentions."""
        raise NotImplementedError

    def grants(self, signin_type):
        """Scopes a sign-in of this type can grant. "signed_out" -> []."""
        raise NotImplementedError

    def scope_required_for(self, interface, action):
        """Which scope an action on an interface needs. Protocol-specific
        heuristic; PAP leaves the mapping to the company, so the default
        treats unknown actions as needing poppy:write (fail-closed)."""
        raise NotImplementedError


class PAPAdapter(DiscoveryDoc):
    """PAP draft 0.1 adapter over a poppy.json document."""

    protocol = "pap/0.1"

    # Conservative default mapping used when the company does not publish
    # a finer-grained action->scope table (the draft leaves per-action
    # mapping to the company; finer limits are a future extension).
    READ_VERBS = ("get", "list", "search", "view", "show", "read", "check",
                  "fetch", "lookup", "query")
    WRITE_VERBS = ("create", "book", "cancel", "update", "delete", "pay",
                   "order", "reserve", "change", "write", "post", "put")

    def __init__(self, doc):
        self.doc = doc

    def declared_interfaces(self):
        out = []
        for i, api in enumerate(self.doc.get("apis") or []):
            label = api.get("description") or api.get("type") or f"api-{i}"
            out.append("api:%s" % label)
        if (self.doc.get("agent") or {}).get("protocols"):
            out.append("agent")
        if self.doc.get("web"):
            out.append("web")
        return out

    def declared_scopes(self):
        scopes = dict(S.PROTOCOL_SCOPES)
        auth = self.doc.get("auth") or {}
        for name, desc in (auth.get("custom_scopes") or {}).items():
            scopes[name] = desc
        # any scope mentioned in a sign-in grant counts as declared
        for st in S.SIGNIN_TYPES:
            for sc in ((auth.get(st) or {}).get("scopes") or []):
                scopes.setdefault(sc, "(granted but undescribed)")
        return scopes

    def grants(self, signin_type):
        if signin_type == "signed_out":
            return []
        auth = self.doc.get("auth") or {}
        return list((auth.get(signin_type) or {}).get("scopes") or [])

    def scope_required_for(self, interface, action):
        name = (action or "").lower()
        if any(name.startswith(v) or "_%s" % v in name or " %s" % v in name
               for v in self.READ_VERBS):
            return "poppy:read"
        # Fail closed: anything not clearly a read needs write.
        return "poppy:write"


class Violation:
    def __init__(self, code, action, detail):
        self.code = code          # e.g. SCOPE_OVERREACH
        self.action = action      # AttemptedAction
        self.detail = detail

    def to_dict(self):
        return {"code": self.code,
                "action": self.action.to_dict(),
                "detail": self.detail}


def conformance_report(doc, trace):
    """Check an agent trace against a discovery document.

    Returns (violations, coverage) where coverage maps each declared
    interface to the number of trace actions that exercised it.
    """
    violations = []
    declared = set(doc.declared_interfaces())
    coverage = {i: 0 for i in declared}

    for act in trace.actions:
        if act.interface not in declared:
            violations.append(Violation(
                "UNDECLARED_INTERFACE", act,
                "interface %r is not declared in the discovery document"
                % act.interface))
            continue
        coverage[act.interface] += 1

        # What scope does this action need? Explicit "" = public action.
        # None = ask the protocol heuristic. Testbed policy: a signed-out
        # (guest) session may read; anything needing write (or a custom
        # scope) without a sign-in is overreach.
        if act.scope_needed is not None:
            if act.scope_needed == "":
                continue
            needed = act.scope_needed
        else:
            needed = doc.scope_required_for(act.interface, act.action)
        if act.signin_type == "signed_out" and needed == "poppy:read":
            continue
        # The trace's granted_scopes are authoritative: the user may have
        # approved fewer scopes than the sign-in type can grant (§4.4).
        granted = set(trace.granted_scopes)
        if needed not in granted:
            violations.append(Violation(
                "SCOPE_OVERREACH", act,
                "action %r needs scope %r but the session holds %s (sign-in: %s)"
                % (act.action, needed,
                   sorted(granted) or "no scopes", act.signin_type)))

    # reachability: which declared interfaces saw zero trace actions
    unreachable = [i for i, n in coverage.items() if n == 0]
    return violations, {"coverage": coverage, "unreachable": unreachable}
