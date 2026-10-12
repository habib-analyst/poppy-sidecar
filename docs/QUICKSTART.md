# Quickstart

## Install

```bash
pip install poppy-sidecar
```

No dependencies beyond Python 3.10+ stdlib.

## 1. Generate a poppy.json for your business

Answer a few questions:

```bash
poppy-sidecar generate --interactive -o poppy.json
```

Or from a profile file (`poppy-sidecar generate --profile HELP` shows the format):

```bash
poppy-sidecar generate --profile my-business.json -o poppy.json
```

The generator self-validates: it refuses to emit a document its own
validator would reject.

## 2. Validate a poppy.json

```bash
poppy-sidecar validate poppy.json --domain example.com
```

```
valid: True (0 errors, 1 warning)
```

Every finding cites the spec section it comes from. Exit code 0 = no
errors (CI-ready); `--strict` makes warnings fail too; `--json` gives
machine-readable output. Add `--live` to also check endpoint
reachability and the issuer's OAuth metadata (`poppy_domains`).

## 3. Test whether your agent respects the declared scopes

Record what your test agent did as a trace:

```json
{
  "granted_scopes": ["poppy:read"],
  "actions": [
    {"interface": "api:Bookings", "action": "search_rooms",
     "scope_needed": "poppy:read", "signin_type": "direct"},
    {"interface": "api:Bookings", "action": "cancel_booking",
     "scope_needed": "poppy:write", "signin_type": "direct"}
  ]
}
```

```bash
poppy-sidecar testbed poppy.json trace.json
```

```
testbed: 2 actions, 1 violations
  VIOLATION SCOPE_OVERREACH: cancel_booking — action 'cancel_booking' needs scope 'poppy:write' but the session holds ['poppy:read'] (sign-in: direct)
RESULT: FAIL
```

Exit code 0 = clean, 1 = violations. `scope_needed` may be omitted and the
PAP verb heuristic decides (reads → `poppy:read`, everything else →
`poppy:write`, fail-closed); `""` marks an explicitly public action.

## Python API

```python
from poppy_sidecar import generate, validate, run_testbed

doc = generate({"name": "My Shop", "domain": "example.com",
                "interfaces": {"web": {}}})
report = validate(doc, domain="example.com")
print(report.ok)  # True

tb = run_testbed(doc, {"granted_scopes": ["poppy:read"], "actions": []})
print(tb.passed)  # True
```
