"""Shared fixtures for the poppy-sidecar test suite."""

VALID_DOC = {
    "protocol_version": "0.1",
    "organization": {"name": "Test Guest House", "domain": "testguest.example"},
    "auth": {
        "issuer": "https://auth.testguest.example",
        "direct": {"scopes": ["poppy:read", "poppy:write", "booking:manage"]},
        "device": {"scopes": ["poppy:read"]},
        "mediated": {
            "endpoint": "https://auth.testguest.example/poppy/sign-in",
            "fields": [
                {"name": "email", "label": "Email", "secret": False},
                {"name": "password", "label": "Password", "secret": True},
            ],
            "scopes": ["poppy:read"],
        },
        "custom_scopes": {"booking:manage": "Create, view and cancel room bookings"},
    },
    "agent": {"protocols": [{"type": "poppy", "endpoint": "https://api.testguest.example/poppy/conversations"}]},
    "web": {"browser_session_endpoint": "https://testguest.example/poppy/browser-session"},
    "apis": [
        {"type": "openapi", "url": "https://api.testguest.example/openapi.json",
         "description": "Room availability and bookings"},
        {"type": "mcp", "url": "https://mcp.testguest.example/mcp",
         "description": "Concierge search"},
    ],
}

GOOD_TRACE = {
    "granted_scopes": ["poppy:read", "poppy:write", "booking:manage"],
    "actions": [
        {"interface": "api:Room availability and bookings", "action": "search_rooms",
         "scope_needed": "poppy:read", "signin_type": "direct"},
        {"interface": "api:Room availability and bookings", "action": "book_room",
         "scope_needed": "poppy:write", "signin_type": "direct"},
        {"interface": "web", "action": "view_gallery",
         "scope_needed": "poppy:read", "signin_type": "signed_out"},
    ],
}
