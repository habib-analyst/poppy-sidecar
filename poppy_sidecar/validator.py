"""Spec-compliance validator for poppy.json (PAP draft 0.1).

Every finding cites the spec section it comes from. Exit codes are CI-ready:
0 = no errors, 1 = errors (2 = usage error). Warnings never fail the run
unless --strict is passed.
"""

import json
import urllib.request
import urllib.error

from poppy_sidecar import schema as S


class Finding:
    def __init__(self, level, code, message, section=""):
        assert level in ("error", "warning")
        self.level = level
        self.code = code
        self.message = message
        self.section = section

    def to_dict(self):
        return {"level": self.level, "code": self.code,
                "message": self.message, "section": self.section}

    def __str__(self):
        tag = "ERROR" if self.level == "error" else "WARN"
        sec = " [spec %s]" % self.section if self.section else ""
        return "%s %s: %s%s" % (tag, self.code, self.message, sec)


class ValidationReport:
    def __init__(self, findings=()):
        self.findings = list(findings)

    @property
    def errors(self):
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self):
        return [f for f in self.findings if f.level == "warning"]

    @property
    def ok(self):
        return not self.errors

    def to_dict(self):
        return {"ok": self.ok,
                "errors": [f.to_dict() for f in self.errors],
                "warnings": [f.to_dict() for f in self.warnings]}

    def __str__(self):
        lines = [str(f) for f in self.findings]
        lines.append("valid: %s (%d errors, %d warnings)"
                     % (self.ok, len(self.errors), len(self.warnings)))
        return "\n".join(lines)


def _is_https(url):
    return isinstance(url, str) and url.startswith("https://")


def validate(doc, domain=None, live=False, timeout=10):
    """Validate a parsed poppy.json document.

    doc: dict (parsed JSON). domain: the host the document was fetched
    from, used for the §3.1 domain-match check (skipped if None).
    live: also check endpoint reachability + OAuth server metadata.
    """
    findings = []

    def err(code, msg, section=""):
        findings.append(Finding("error", code, msg, section))

    def warn(code, msg, section=""):
        findings.append(Finding("warning", code, msg, section))

    if not isinstance(doc, dict):
        err("NOT_AN_OBJECT", "poppy.json must be a JSON object")
        return ValidationReport(findings)

    # --- protocol_version (§3.1) ---
    ver = doc.get("protocol_version")
    if not ver:
        err("MISSING_VERSION", "missing required field 'protocol_version'", "§3.1")
    elif not isinstance(ver, str) or "." not in ver:
        err("BAD_VERSION", "protocol_version must look like 'major.minor', got %r" % ver, "§3.1")
    else:
        try:
            major = int(ver.split(".")[0])
        except ValueError:
            major = None
        if major != S.SUPPORTED_MAJOR:
            err("UNSUPPORTED_MAJOR",
                "major version %r is not supported by this kit (supports %d.x)"
                % (ver, S.SUPPORTED_MAJOR), "§3.1")

    # --- organization (§3.1) ---
    org = doc.get("organization")
    if not isinstance(org, dict):
        err("MISSING_ORGANIZATION", "missing required object 'organization'", "§3.1")
        org = {}
    if not org.get("name"):
        err("MISSING_ORG_NAME", "organization.name is required", "§3.1")
    if not org.get("domain"):
        err("MISSING_ORG_DOMAIN", "organization.domain is required", "§3.1")
    elif domain and not S.domains_match(org["domain"], domain):
        err("DOMAIN_MISMATCH",
            "organization.domain %r does not match the requested host %r (ignoring leading www.)"
            % (org["domain"], domain), "§3.1")

    # --- at least one route (§3.1) ---
    has_agent = bool((doc.get("agent") or {}).get("protocols"))
    has_apis = bool(doc.get("apis"))
    has_web = doc.get("web") is not None
    if not (has_agent or has_apis or has_web):
        err("NO_ROUTE", "at least one of 'agent', 'apis', 'web' is required", "§3.1")

    # --- auth (§3.1, §4.4) ---
    auth = doc.get("auth")
    needs_auth = has_agent or has_apis or bool((doc.get("web") or {}).get("browser_session_endpoint"))
    if needs_auth and not isinstance(auth, dict):
        err("MISSING_AUTH", "'auth' is required when agent, apis, or web.browser_session_endpoint is present", "§3.1")
        auth = {}
    elif isinstance(auth, dict):
        issuer = auth.get("issuer")
        if not _is_https(issuer):
            err("BAD_ISSUER", "auth.issuer must be an HTTPS URL, got %r" % issuer, "§3.1")
        for st in S.SIGNIN_TYPES:
            blk = auth.get(st)
            if blk is None:
                continue
            if not isinstance(blk, dict):
                err("BAD_SIGNIN_BLOCK", "auth.%s must be an object" % st, "§4.4")
                continue
            scopes = blk.get("scopes")
            if not isinstance(scopes, list) or not scopes or not all(isinstance(x, str) for x in scopes):
                err("BAD_SCOPES", "auth.%s.scopes must be a non-empty list of strings" % st, "§4.4")
            if st == "mediated":
                if not _is_https(blk.get("endpoint")):
                    err("BAD_MEDIATED_ENDPOINT",
                        "auth.mediated.endpoint must be an HTTPS URL, got %r" % blk.get("endpoint"), "§4.7")
                fields = blk.get("fields")
                if not isinstance(fields, list) or not fields:
                    err("BAD_MEDIATED_FIELDS", "auth.mediated.fields must be a non-empty list", "§4.7")
                else:
                    for f in fields:
                        if not isinstance(f, dict) or not f.get("name") or not f.get("label") \
                                or not isinstance(f.get("secret"), bool):
                            err("BAD_MEDIATED_FIELD",
                                "each mediated field needs name, label, and boolean secret; got %r" % f, "§4.7")
        # custom scopes: every non-protocol scope should be described (§4.4)
        custom = auth.get("custom_scopes") or {}
        if not isinstance(custom, dict):
            err("BAD_CUSTOM_SCOPES", "auth.custom_scopes must be an object", "§4.4")
        else:
            mentioned = set()
            for st in S.SIGNIN_TYPES:
                mentioned.update((auth.get(st) or {}).get("scopes") or [])
            for sc in mentioned:
                if sc in S.PROTOCOL_SCOPES:
                    continue
                if S.scope_is_reserved(sc):
                    err("RESERVED_SCOPE",
                        "scope %r uses the reserved 'poppy:' prefix but is not a protocol scope" % sc, "§4.4")
                elif sc not in custom:
                    warn("UNDESCRIBED_SCOPE",
                         "custom scope %r is granted but not described in auth.custom_scopes" % sc, "§4.4")

    # --- agent (§3.1, §7) ---
    agent = doc.get("agent") or {}
    if agent:
        for i, p in enumerate(agent.get("protocols") or []):
            if not isinstance(p, dict) or not p.get("type"):
                err("BAD_AGENT_PROTOCOL", "agent.protocols[%d] needs a 'type'" % i, "§3.1")
            if not _is_https(p.get("endpoint") if isinstance(p, dict) else None):
                err("BAD_AGENT_ENDPOINT",
                    "agent.protocols[%d].endpoint must be an HTTPS URL" % i, "§3.1")

    # --- apis (§3.1, §6) ---
    for i, api in enumerate(doc.get("apis") or []):
        if not isinstance(api, dict):
            err("BAD_API", "apis[%d] must be an object" % i, "§3.1")
            continue
        if not api.get("type"):
            err("BAD_API_TYPE", "apis[%d] needs a 'type'" % i, "§3.1")
        elif api["type"] not in S.KNOWN_API_TYPES:
            warn("UNKNOWN_API_TYPE",
                 "apis[%d].type %r is not named by the draft (known: %s); companies keep their own schema"
                 % (i, api["type"], sorted(S.KNOWN_API_TYPES)), "§6")
        if not _is_https(api.get("url")):
            err("BAD_API_URL", "apis[%d].url must be an HTTPS URL, got %r" % (i, api.get("url")), "§3.1")
        if not api.get("description"):
            warn("MISSING_API_DESCRIPTION",
                 "apis[%d] has no description; agents use it to pick the right API" % i, "§3.1")

    # --- web (§3.1, §5) ---
    web = doc.get("web")
    if web is not None:
        if not isinstance(web, dict):
            err("BAD_WEB", "'web' must be an object", "§3.1")
        elif web.get("browser_session_endpoint") is not None \
                and not _is_https(web.get("browser_session_endpoint")):
            err("BAD_BROWSER_SESSION_ENDPOINT",
                "web.browser_session_endpoint must be an HTTPS URL", "§5")

    # --- extensions (§3.3) ---
    exts = doc.get("extensions") or {}
    if not isinstance(exts, dict):
        err("BAD_EXTENSIONS", "'extensions' must be an object keyed by name", "§3.3")
    else:
        for name, cfg in exts.items():
            if not S.extension_name_ok(name):
                err("BAD_EXTENSION_NAME",
                    "extension %r must be a plain name or start with a domain you control" % name, "§3.3")
            if not isinstance(cfg, dict) or "version" not in cfg:
                err("BAD_EXTENSION_VERSION",
                    "extension %r needs a 'version' (its major version)" % name, "§3.3")

    # --- live checks (opt-in) ---
    if live:
        _live_checks(doc, domain, findings, timeout, err, warn)

    return ValidationReport(findings)


def _fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "poppy-sidecar/validator"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(65536)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # network down, DNS, TLS, ...
        return None, str(e).encode()


def _live_checks(doc, domain, findings, timeout, err, warn):
    urls = []

    def collect(u, label):
        if isinstance(u, str) and u.startswith("https://"):
            urls.append((label, u))

    for i, api in enumerate(doc.get("apis") or []):
        if isinstance(api, dict):
            collect(api.get("url"), "apis[%d].url" % i)
    for i, p in enumerate((doc.get("agent") or {}).get("protocols") or []):
        if isinstance(p, dict):
            collect(p.get("endpoint"), "agent.protocols[%d].endpoint" % i)
    web = doc.get("web") or {}
    collect(web.get("browser_session_endpoint"), "web.browser_session_endpoint")
    auth = doc.get("auth") or {}
    issuer = auth.get("issuer")
    if _is_https(issuer):
        meta_url = issuer.rstrip("/") + "/.well-known/oauth-authorization-server"
        status, body = _fetch(meta_url, timeout)
        if status != 200:
            warn("OAUTH_METADATA_UNREACHABLE",
                 "issuer metadata %s returned %s; cannot verify poppy_domains (§3.2)"
                 % (meta_url, status), "§3.2")
        else:
            try:
                meta = json.loads(body.decode("utf-8", "replace"))
            except Exception:
                meta = {}
            if meta.get("issuer") != issuer:
                err("ISSUER_MISMATCH",
                    "OAuth metadata issuer %r does not exactly match auth.issuer %r"
                    % (meta.get("issuer"), issuer), "§3.2")
            domains = meta.get("poppy_domains") or []
            if domain and S.normalize_domain(domain) not in [S.normalize_domain(d) for d in domains]:
                err("POPPY_DOMAINS_MISSING",
                    "poppy_domains %r does not list %r; any domain could claim this issuer"
                    % (domains, domain), "§3.2")
            if not meta.get("token_endpoint"):
                err("NO_TOKEN_ENDPOINT", "OAuth metadata has no token_endpoint (required, §3.2)", "§3.2")
            if not meta.get("revocation_endpoint"):
                warn("NO_REVOCATION_ENDPOINT", "OAuth metadata has no revocation_endpoint (required, §3.2)", "§3.2")

    for label, url in urls:
        status, _ = _fetch(url, timeout)
        if status is None:
            warn("ENDPOINT_UNREACHABLE", "%s %s unreachable (network/TLS error)" % (label, url))
        elif status >= 400:
            warn("ENDPOINT_HTTP_%d" % status, "%s %s returned HTTP %d" % (label, url, status))
