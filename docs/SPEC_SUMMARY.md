# Personal Agent Protocol (Poppy) — draft 0.1 spec summary

Source: https://personalagentprotocol.org/spec (read 2026-10-12; draft 0.1,
1966 lines). This is a summary for tool builders, not a substitute for the spec.
Anything here that conflicts with the live spec is wrong — the spec wins.

## What it is

An open protocol (Apache 2.0) by Sierra + Meta for how a **personal agent**,
acting for one user, works with a **company**. Published 2026-10-06, draft 0.1
spec 2026-10-09. Nickname: "Poppy". 35 design partners (OpenAI, Visa,
Mastercard, PayPal, Cloudflare, Target…). Reference implementation promised
"next month" (as of the draft).

## The core idea

Today it's all-or-nothing: the company blocks the agent, or the agent signs
in as the user and can do anything. PAP adds the middle: the company declares
what agents may do, the user grants read/write/both, one session spans the
company's APIs + website + own agent.

## Discovery: `/.well-known/poppy.json` (§3)

Published over HTTPS at `https://{domain}/.well-known/poppy.json`. May
redirect (all redirects HTTPS). Key fields:

| Field | Required | Notes |
|---|---|---|
| `protocol_version` | yes | `"0.1"`; agents MUST NOT use an unsupported major |
| `organization` | yes | `name` + `domain`; domain MUST match the requested host (ignoring `www.`) |
| `auth` | if agent/apis/web endpoint present | `issuer` (HTTPS OAuth issuer), sign-in types |
| `auth.direct` / `.device` / `.mediated` | if supported | each lists grantable `scopes` |
| `auth.mediated` | if supported | `endpoint` + `fields` (name/label/secret) |
| `auth.custom_scopes` | no | descriptions for non-`poppy:` scopes |
| `agent` | ≥1 of agent/apis/web | `protocols[]`: `type` + HTTPS `endpoint` |
| `apis` | ≥1 of agent/apis/web | `type` (openapi, mcp…), `url`, `description` |
| `web` | ≥1 of agent/apis/web | optional `browser_session_endpoint` |
| `extensions` | no | keyed by name; third-party names MUST start with a domain they control |

## Scopes (§4.4)

- `poppy:read` — view account info (orders, bookings).
- `poppy:write` — make changes (exchanges, booking updates).
- Independent: request both when needed. Companies MAY define their own
  (described in `custom_scopes`) and MAY skip the broad ones entirely.
- `poppy:` prefix is reserved. Each sign-in type lists the scopes it can
  grant; the company MUST NOT grant beyond what was requested and allowed.
- The user may approve fewer scopes than requested — agents check `scope`.

## Sign-in (§4.5–4.7)

- **Direct**: OAuth 2.0 authorization code + PKCE on the company's own page.
- **Device**: OAuth 2.0 device grant (link + code, any device).
- **Mediated**: the agent sends user credentials to `auth.mediated.endpoint`
  (rate-limited, never returned in responses, one-time codes for step-up).
- Result: an **Account Token** (OAuth refresh token, long-lived) + a signed-in
  **Session Token** (short-lived JWT, DPoP-bound).

## OAuth metadata (§3.2)

The issuer MUST publish RFC 8414 metadata at
`{issuer}/.well-known/oauth-authorization-server` with `poppy_domains`
listing every domain allowed to use that issuer — this stops domain A from
claiming company B's sign-in server. `token_endpoint` and
`revocation_endpoint` required.

## What the draft does NOT cover (open topics)

Per-action permission limits, payments, push notifications — listed as
future extensions. Finer-grained limits than read/write are explicitly
future work.

## Rivals / adjacent

- **Visa Trusted Agent Protocol**: identity layer for agents on card rails
  (RFC 9421 signatures, key directory at `mcp.visa.com/.well-known/jwks`,
  `agent-browser-auth` / `agent-payer-auth` tags). Permissioned (Visa-approved
  agents), payment-focused. See `PROTOCOL_HEDGE.md`.
- **Decagon PACT** (Apache 2.0): a separate consent protocol, not part of PAP.
- **Agent Web Protocol (agent.json)**: a different, earlier discovery format.
