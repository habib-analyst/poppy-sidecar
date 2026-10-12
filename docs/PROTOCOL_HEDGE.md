# Protocol hedge: why the core is protocol-agnostic

There is a protocol war on. PAP (Sierra + Meta, open spec, Apache 2.0) and
Visa's Trusted Agent Protocol (permissioned, payment-focused) both want to
be how agents transact with businesses. Betting the whole toolkit on one
winner is how you become abandonware.

## The shared pattern

Strip the branding and every agent-commerce protocol answers the same two
questions:

1. **DECLARE** — what does the business expose, and under which grants?
2. **TEST** — did the agent's trace stay inside the declaration?

`poppy_sidecar/core.py` models exactly this and nothing else:

- `DiscoveryDoc` — `declared_interfaces()`, `declared_scopes()`,
  `grants(signin_type)`, `scope_required_for(interface, action)`.
- `AgentTrace` / `AttemptedAction` — what the agent did + what it held.
- `conformance_report(doc, trace)` — violations + coverage. No PAP
  concepts leak into it.

## PAP plugs in as an adapter

`PAPAdapter` maps `poppy.json` onto `DiscoveryDoc`:

| DiscoveryDoc | PAP source |
|---|---|
| declared interfaces | `apis[]` (by description), `agent.protocols`, `web` |
| declared scopes | `poppy:read`/`poppy:write` + `auth.custom_scopes` |
| grants(sign-in type) | `auth.{direct,device,mediated}.scopes` |
| scope heuristic | read-verbs → `poppy:read`, else `poppy:write` (fail-closed) |

## What a Visa-TAP adapter would look like

TAP declares differently: no discovery document — a **key directory** at
`https://mcp.visa.com/.well-known/jwks`, RFC 9421 signatures with
`agent-browser-auth` / `agent-payer-auth` tags, and mandate-carrying
payment containers. A `TAPAdapter(DiscoveryDoc)` would:

- `declared_interfaces()` ← the merchant's TAP-accepting endpoints.
- `declared_scopes()` ← `{"tap:browse", "tap:pay"}` mapped from the two tags.
- `grants(...)` ← derived from the verified signature tag on each request.
- `scope_required_for()` ← pay-intent actions → `tap:pay`, else `tap:browse`.

The testbed, CLI, and CI patterns don't change — only the adapter does.
That's the hedge: if TAP wins the enterprise and PAP wins the long tail,
the same `testbed` command tests both.

## What we don't claim

We have not implemented the TAP adapter (no stable public merchant-side
spec to build against as of 2026-10-12). The seam exists, is tested via
`PAPAdapter`, and is documented here so the second adapter is a weekend,
not a rewrite.
