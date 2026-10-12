# CI integration guide

`poppy-sidecar validate` is built for pipelines: deterministic output,
spec-cited findings, and CI-ready exit codes.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | no errors (warnings allowed) |
| 1 | spec errors found — or warnings, with `--strict` |
| 2 | usage error (file not found, invalid JSON, bad arguments) |

## GitHub Actions

```yaml
- name: Validate poppy.json
  run: |
    pip install poppy-sidecar
    poppy-sidecar validate .well-known/poppy.json \
      --domain ${{ vars.SITE_DOMAIN }} --strict
```

Serve the file at `/.well-known/poppy.json` (or test the source file
before deploy — same thing, fewer surprises).

## Agent scope tests in CI

Keep a corpus of agent traces from your eval harness and gate on them:

```yaml
- name: Agent scope conformance
  run: |
    pip install poppy-sidecar
    for trace in tests/agent-traces/*.json; do
      poppy-sidecar testbed .well-known/poppy.json "$trace" || exit 1
    done
```

A trace that newly violates after a prompt or tool change fails the build —
scope regressions become test failures, not incidents.

## What to check in, what to gate on

- **Check in**: `poppy.json`, the business profile it was generated from,
  and the agent-trace corpus.
- **Gate on**: `validate --strict` (catches undescribed scopes, missing
  API descriptions) and `testbed` over every trace.
- **Nightly, not per-PR**: `validate --live` (endpoint reachability and
  OAuth `poppy_domains` checks need network and are slower).
