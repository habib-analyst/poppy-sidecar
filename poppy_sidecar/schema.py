"""PAP draft 0.1 discovery-document model.

Hand-rolled from the live spec at https://personalagentprotocol.org/spec
(sections 3, 3.1, 3.2, 3.3, 4.4, 4.7, 6). No third-party dependencies:
validation is explicit code, not a JSON-Schema blob, so error messages can
cite the exact spec section that failed.
"""

SUPPORTED_MAJOR = 0
SUPPORTED_MINOR = 1

WELL_KNOWN_PATH = "/.well-known/poppy.json"

# Scopes defined by the protocol itself (§4.4). Companies MAY also define
# their own, which MUST be described in auth.custom_scopes. Names starting
# with "poppy:" are reserved for the protocol.
PROTOCOL_SCOPES = {
    "poppy:read": "View account information, such as orders and bookings.",
    "poppy:write": "Make changes, such as exchanging an item or updating a booking.",
}
RESERVED_SCOPE_PREFIX = "poppy:"

# API interface types named in §6 ("Companies choose what to offer:
# OpenAPI, MCP, or web pages"). The spec keeps each API's own schema, so
# the type list is open; these are the ones the draft names.
KNOWN_API_TYPES = {"openapi", "mcp"}

# Sign-in types from §4.4-4.7.
SIGNIN_TYPES = ("direct", "device", "mediated")

# Mediated sign-in credential field keys (§4.7).
MEDIATED_FIELD_KEYS = {"name", "label", "secret"}


def scope_is_reserved(scope):
    """True if the scope name uses the protocol-reserved ``poppy:`` prefix."""
    return scope.startswith(RESERVED_SCOPE_PREFIX)


def normalize_domain(domain):
    """Lowercase and strip a leading ``www.`` per §3.1 domain matching."""
    d = (domain or "").strip().lower()
    if d.startswith("www."):
        d = d[4:]
    return d


def domains_match(declared, requested):
    """§3.1: organization.domain MUST match the requested well-known host."""
    return normalize_domain(declared) == normalize_domain(requested)


def extension_name_ok(name):
    """§3.3: plain names are protocol-defined tokens; anything else MUST
    start with a domain the company controls (contains a dot)."""
    if not name or not isinstance(name, str):
        return False
    if " " in name or "\t" in name:
        return False
    if "." not in name:
        return True  # plain protocol-defined token, e.g. "operations"
    # domain-prefixed: must look like a domain prefix, e.g. "example.com/gift-wrap"
    head = name.split("/")[0]
    return "." in head
