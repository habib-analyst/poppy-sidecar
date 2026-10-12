"""poppy.json generator: from a small business profile to a draft-0.1 document.

Two ways in:
  * ``generate(profile)`` — profile is a dict (see PROFILE_FIELDS).
  * ``interactive_profile()`` — asks questions on stdin, returns a profile.

Then ``poppy-sidecar generate --profile profile.json`` writes poppy.json.
The output is validated with the kit's own validator before it is returned.
"""

from poppy_sidecar import schema as S
from poppy_sidecar.validator import validate

PROFILE_FIELDS = """Required: name, domain.
Recommended: auth_issuer, signin {direct/device/mediated scopes},
custom_scopes {name: description}, interfaces {web/apis/agent}.
Example:
{
  "name": "Example Guest House",
  "domain": "example.com",
  "auth_issuer": "https://auth.example.com",
  "signin": {
    "direct": ["poppy:read", "poppy:write"],
    "device": ["poppy:read"]
  },
  "custom_scopes": {
    "booking:manage": "Create, view and cancel room bookings"
  },
  "interfaces": {
    "web": {"browser_session_endpoint": "https://example.com/poppy/browser-session"},
    "apis": [
      {"type": "openapi", "url": "https://api.example.com/openapi.json",
       "description": "Room availability and bookings"}
    ]
  }
}"""


def generate(profile):
    """Build a poppy.json dict from a business profile dict."""
    name = profile.get("name", "").strip()
    domain = profile.get("domain", "").strip().lower()
    if not name or not domain:
        raise ValueError("profile needs 'name' and 'domain'")
    issuer = (profile.get("auth_issuer") or ("https://auth." + domain)).rstrip("/")

    doc = {
        "protocol_version": "0.1",
        "organization": {"name": name, "domain": domain},
    }

    signin = profile.get("signin") or {}
    custom_scopes = dict(profile.get("custom_scopes") or {})
    auth = {"issuer": issuer}
    for st in S.SIGNIN_TYPES:
        scopes = signin.get(st)
        if scopes:
            blk = {"scopes": list(scopes)}
            if st == "mediated":
                blk["endpoint"] = issuer + "/poppy/sign-in"
                blk["fields"] = [
                    {"name": "email", "label": "Email", "secret": False},
                    {"name": "password", "label": "Password", "secret": True},
                ]
            auth[st] = blk
    if custom_scopes:
        auth["custom_scopes"] = custom_scopes

    ifaces = profile.get("interfaces") or {}
    web = ifaces.get("web")
    apis = ifaces.get("apis")
    agent = ifaces.get("agent")
    if web or apis or agent:
        doc["auth"] = auth
    if web is not None:
        doc["web"] = {"browser_session_endpoint": web.get("browser_session_endpoint")} \
            if web.get("browser_session_endpoint") else {}
    if apis:
        doc["apis"] = [
            {"type": a.get("type", "openapi"), "url": a["url"],
             "description": a.get("description", "")}
            for a in apis if a.get("url")
        ]
    if agent:
        doc["agent"] = {"protocols": [
            {"type": p.get("type", "poppy"), "endpoint": p["endpoint"]}
            for p in agent.get("protocols", []) if p.get("endpoint")
        ]}

    # Self-check: never emit a document our own validator rejects.
    report = validate(doc, domain=domain)
    if not report.ok:
        raise ValueError("generated document failed self-validation:\n" + str(report))
    return doc


def interactive_profile():
    """Prompt for a business profile on stdin."""
    print("poppy-sidecar generator — answer a few questions, get a poppy.json.\n"
          "(Enter = skip / accept the default in [brackets])")
    def ask(prompt, default=""):
        hint = " [%s]" % default if default else ""
        v = input(prompt + hint + ": ").strip()
        return v or default

    profile = {
        "name": ask("Business name"),
        "domain": ask("Website domain (e.g. example.com)").lower(),
    }
    profile["auth_issuer"] = ask("OAuth issuer URL",
                                 "https://auth." + profile["domain"])
    print("\nSign-in types: which scopes can each grant? (comma-separated, blank = not offered)")
    signin = {}
    for st in S.SIGNIN_TYPES:
        raw = ask("  %s scopes" % st, "poppy:read, poppy:write" if st == "direct" else "")
        if raw.strip():
            signin[st] = [s.strip() for s in raw.split(",") if s.strip()]
    profile["signin"] = signin

    print("\nCustom scopes beyond poppy:read/poppy:write? (name=description, blank line to finish)")
    custom = {}
    while True:
        line = input("  scope: ").strip()
        if not line:
            break
        if "=" in line:
            k, v = line.split("=", 1)
            custom[k.strip()] = v.strip()
    profile["custom_scopes"] = custom

    print("\nInterfaces (at least one):")
    ifaces = {}
    bse = ask("  Web browser-session endpoint URL",
              "https://%s/poppy/browser-session" % profile["domain"])
    if bse:
        ifaces["web"] = {"browser_session_endpoint": bse}
    api_url = ask("  API spec URL (OpenAPI/MCP), blank to skip")
    if api_url:
        atype = ask("  API type", "openapi")
        ifaces["apis"] = [{"type": atype, "url": api_url,
                           "description": ask("  API description", "Bookings and availability")}]
    agent_ep = ask("  Company-agent conversation endpoint, blank to skip")
    if agent_ep:
        ifaces["agent"] = {"protocols": [{"type": "poppy", "endpoint": agent_ep}]}
    profile["interfaces"] = ifaces
    return profile
