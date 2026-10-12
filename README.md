# poppy-sidecar

[![PyPI version](https://img.shields.io/pypi/v/poppy-sidecar)](https://pypi.org/project/poppy-sidecar/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/habib-analyst/poppy-sidecar)](https://github.com/habib-analyst/poppy-sidecar/stargazers)

The first independent developer kit for the **Personal Agent Protocol**
("Poppy", Sierra + Meta, draft 0.1): generate a `poppy.json` for your
business, validate it against the spec, and test whether your agent
actually respects the scopes it was granted.

## Quickstart

```bash
pip install poppy-sidecar
```

Generate a discovery document for your business:

```bash
poppy-sidecar generate --interactive -o poppy.json
```

Validate it (every finding cites the spec section it comes from):

```bash
poppy-sidecar validate poppy.json --domain example.com
```

```
valid: True (0 errors, 0 warnings)
```

Check an agent trace for scope violations:

```bash
poppy-sidecar testbed poppy.json trace.json
```

```
testbed: 3 actions, 2 violations
  VIOLATION SCOPE_OVERREACH: cancel_booking — action 'cancel_booking' needs scope 'poppy:write' but the session holds ['poppy:read'] (sign-in: direct)
  VIOLATION UNDECLARED_INTERFACE: dump_database — interface 'api:Hidden admin panel' is not declared in the discovery document
RESULT: FAIL
```

## Measured results

All numbers from the included test suite and dogfood runs — no placeholders.

| Check | Result |
|---|---|
| Unit tests | 40/40 pass |
| Validator negative cases (spec violations planted) | 17/17 error codes fire correctly |
| Dogfood: 3 real business `poppy.json` generated | 3/3 validate clean (0 errors, 0 warnings) |
| Testbed: planted `SCOPE_OVERREACH` | caught |
| Testbed: planted `UNDECLARED_INTERFACE` | caught |
| Testbed: clean trace false positives | 0 |
| Tests caught real bugs before release | 3 (empty `web{}` dropped; guest reads misflagged; spaced extension names accepted) |

## How it works

Three tools, one protocol-agnostic core:

- **Generator** (`poppy-sidecar generate`) — business profile → draft-0.1
  `poppy.json`. Self-validates: it refuses to emit a document its own
  validator would reject.
- **Validator** (`poppy-sidecar validate`) — 25 checks against the draft
  spec: required fields, `protocol_version`, domain matching (§3.1),
  sign-in scopes and the reserved `poppy:` prefix (§4.4), mediated
  credential fields (§4.7), extension naming (§3.3). CI-ready exit codes;
  `--live` adds endpoint reachability and OAuth `poppy_domains` checks.
- **Testbed** (`poppy-sidecar testbed`) — the differentiator. Given a
  `poppy.json` and an agent trace, it verifies the agent stayed inside
  its granted scopes and declared interfaces, and reports which declared
  interfaces the trace never exercised (coverage gaps).

The declare-and-test core (`core.py`) knows nothing about PAP — the
protocol plugs in as an adapter. A Visa-TAP adapter fits the same seam;
see `docs/PROTOCOL_HEDGE.md`.

The `examples/guest-houses/` directory holds real discovery documents
for three Islamabad guest houses, generated and validated with this kit.

## Docs

- `docs/SPEC_SUMMARY.md` — the draft-0.1 spec, distilled for builders
- `docs/QUICKSTART.md` — the 5-minute path
- `docs/CI_GUIDE.md` — gating deploys and agent evals on validation
- `docs/PROTOCOL_HEDGE.md` — why the core is protocol-agnostic

## Citation

```bibtex
@software{rehman2026poppysidecar,
  author  = {Habib Ur Rehman},
  title   = {poppy-sidecar: First independent developer kit for the Personal Agent Protocol},
  year    = {2026},
  url     = {https://github.com/habib-analyst/poppy-sidecar}
}
```

## Limitations (honest)

- Targets PAP **draft 0.1** (2026-10-09). The draft warns any part can
  change; pin your `poppy.json` to the draft you validated against.
- `--live` checks need network and are best run nightly, not per-PR.
- The testbed checks declared scope discipline, not agent intent — a
  malicious agent with a valid grant is out of scope.
- No Visa-TAP adapter yet (no stable public merchant spec to build
  against); the seam is documented and tested via `PAPAdapter`.

---
Built by [Habib Ur Rehman](https://github.com/habib-analyst) · ML/AI Engineer & healthcare-AI researcher ·
[LinkedIn](https://www.linkedin.com/in/hur-dev) · [habib.top](https://habib.top)
