#!/usr/bin/env python3
"""Runnable example: generate + validate + testbed for a guest house.

Run from the repo root:
    python examples/generate_guesthouse.py
"""

import json
import sys

sys.path.insert(0, ".")

from poppy_sidecar import generate, validate, run_testbed

PROFILE = {
    "name": "Oriole Guest House Islamabad",
    "domain": "orioleguesthouse.com",
    "auth_issuer": "https://auth.orioleguesthouse.com",
    "signin": {
        "direct": ["poppy:read", "poppy:write", "booking:manage"],
        "device": ["poppy:read"],
    },
    "custom_scopes": {"booking:manage": "View, create and cancel room bookings"},
    "interfaces": {
        "web": {"browser_session_endpoint": "https://orioleguesthouse.com/poppy/browser-session"},
        "apis": [{"type": "openapi",
                  "url": "https://api.orioleguesthouse.com/openapi.json",
                  "description": "Room availability, rates and bookings"}],
    },
}

# 1. generate
doc = generate(PROFILE)
print("generated poppy.json for", doc["organization"]["name"])

# 2. validate
report = validate(doc, domain="orioleguesthouse.com")
print(report)
assert report.ok

# 3. testbed: a well-behaved agent vs a sneaky one
good = {"granted_scopes": ["poppy:read", "poppy:write", "booking:manage"],
        "actions": [
            {"interface": "api:Room availability, rates and bookings",
             "action": "search_rooms", "scope_needed": "poppy:read",
             "signin_type": "direct"},
            {"interface": "api:Room availability, rates and bookings",
             "action": "book_room", "scope_needed": "poppy:write",
             "signin_type": "direct"},
        ]}
sneaky = {"granted_scopes": ["poppy:read"],
          "actions": [
              {"interface": "api:Room availability, rates and bookings",
               "action": "cancel_booking", "scope_needed": "poppy:write",
               "signin_type": "direct"},
          ]}

r_good = run_testbed(doc, good)
r_sneaky = run_testbed(doc, sneaky)
print("\ngood agent:  %s" % ("PASS" if r_good.passed else "FAIL"))
print("sneaky agent: %s (%d violations)" % (
    "PASS" if r_sneaky.passed else "FAIL", len(r_sneaky.violations)))
for v in r_sneaky.violations:
    print("  -", v.code, "::", v.detail)
assert r_good.passed and not r_sneaky.passed
print("\ndone.")
