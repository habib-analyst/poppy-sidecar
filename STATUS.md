# poppy-sidecar STATUS (lifeline — updated after every unit)

## 2026-10-12 ~09:00 PKT — START
- Spec verified live at personalagentprotocol.org/spec (draft 0.1, 1966 lines): discovery §3 fields table captured; scopes §4.4 (poppy:read/poppy:write, poppy: reserved prefix, custom_scopes); OAuth metadata RFC 8414 + poppy_domains §3.2; API types openapi/mcp §6; extensions naming rule §3.3; mediated fields (name/label/secret) §4.7.
- Novelty gate PASS: no open-source PAP tooling exists (agentwebprotocol=AWP different; sierracatalina/PCP=Personal Context Protocol different; Decagon PACT=consent protocol; AVA Pay=TAP/AP2 only).
- Visa TAP hedge grounded: key directory at https://mcp.visa.com/.well-known/jwks, RFC 9421 signatures, agent-browser-auth/agent-payer-auth tags.
- Next: package skeleton (schema, generator, validator, testbed, core, cli) → tests → dogfood guest houses → docs → branding → paper → LinkedIn draft.

## 2026-10-12 ~09:35 PKT — core built, 40/40 tests green
- Package: schema.py (draft-0.1 model), core.py (protocol-agnostic declare-and-test + PAPAdapter), generator.py (profile->poppy.json + interactive), validator.py (25 checks w/ spec citations, exit codes, opt-in live checks), testbed.py (scope-respect + reachability), cli.py (generate/validate/testbed).
- Tests caught 3 real bugs pre-ship: empty web{} dropped by generator, signed-out reads wrongly flagged, extension names with spaces accepted. All fixed, 40/40 green.
- Dogfood: 3 guest-house poppy.json generated + validate clean (oriole-luxury, oriole-guest-house real domains; cozy placeholder .example marked illustrative).
- Testbed demo: good trace PASS (exit 0); sneaky trace 2/2 violations caught (SCOPE_OVERREACH + UNDECLARED_INTERFACE), exit 1.
- Next: docs (spec summary, quickstart, CI guide, protocol hedge) → branding (README, LICENSE, pyproject) → paper → LinkedIn draft → RESEARCH_LOG.

## 2026-10-12 ~09:55 PKT — DONE
- 40/40 tests green. CLI e2e verified (incl. DOMAIN_MISMATCH anti-impersonation check, exit 1).
- Payload: 26 files, 72KB (under the 138KB single-push limit). Excluded: STATUS.md, __pycache__.
- Paper: hidden_files/papers/poppy-sidecar/PAPER.md. LinkedIn draft: hidden_files/linkedin_drafts/poppy-sidecar.md (status=ready via notify_linkedin_work.py).
- README per brand kit (badges, pitch, quickstart w/ real output, measured table, how-it-works, BibTeX, footer).
- REPO NEEDED: poppy-sidecar — "First independent developer kit for the Personal Agent Protocol: poppy.json generator, spec validator, and agent scope-compliance testbed".
