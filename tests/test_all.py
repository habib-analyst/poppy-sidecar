import copy
import unittest

from poppy_sidecar.generator import generate
from poppy_sidecar.validator import validate
from poppy_sidecar.testbed import run_testbed
from poppy_sidecar.core import PAPAdapter
from poppy_sidecar import schema as S
from tests.fixtures import VALID_DOC, GOOD_TRACE


class TestSchema(unittest.TestCase):
    def test_normalize_domain(self):
        self.assertEqual(S.normalize_domain("WWW.Example.COM"), "example.com")
        self.assertEqual(S.normalize_domain("example.com"), "example.com")

    def test_domains_match(self):
        self.assertTrue(S.domains_match("example.com", "www.example.com"))
        self.assertFalse(S.domains_match("example.com", "evil.com"))

    def test_scope_reserved(self):
        self.assertTrue(S.scope_is_reserved("poppy:read"))
        self.assertTrue(S.scope_is_reserved("poppy:anything"))
        self.assertFalse(S.scope_is_reserved("booking:manage"))

    def test_extension_names(self):
        self.assertTrue(S.extension_name_ok("operations"))
        self.assertTrue(S.extension_name_ok("example.com/gift-wrap"))
        self.assertFalse(S.extension_name_ok("gift wrap"))
        self.assertFalse(S.extension_name_ok(""))


class TestGenerator(unittest.TestCase):
    PROFILE = {
        "name": "Test Guest House",
        "domain": "testguest.example",
        "auth_issuer": "https://auth.testguest.example",
        "signin": {"direct": ["poppy:read", "poppy:write"],
                   "device": ["poppy:read"]},
        "custom_scopes": {"booking:manage": "Manage bookings"},
        "interfaces": {
            "web": {"browser_session_endpoint": "https://testguest.example/poppy/browser-session"},
            "apis": [{"type": "openapi",
                      "url": "https://api.testguest.example/openapi.json",
                      "description": "Bookings"}],
        },
    }

    def test_generates_valid_doc(self):
        doc = generate(copy.deepcopy(self.PROFILE))
        self.assertEqual(doc["protocol_version"], "0.1")
        self.assertEqual(doc["organization"]["domain"], "testguest.example")
        self.assertIn("poppy:read", doc["auth"]["direct"]["scopes"])
        # self-validated inside generate(); double-check
        self.assertTrue(validate(doc, domain="testguest.example").ok)

    def test_requires_name_and_domain(self):
        with self.assertRaises(ValueError):
            generate({"domain": "x.example"})
        with self.assertRaises(ValueError):
            generate({"name": "X"})

    def test_mediated_gets_default_fields(self):
        p = copy.deepcopy(self.PROFILE)
        p["signin"]["mediated"] = ["poppy:read"]
        doc = generate(p)
        fields = doc["auth"]["mediated"]["fields"]
        self.assertTrue(any(f["name"] == "email" and not f["secret"] for f in fields))
        self.assertTrue(any(f["name"] == "password" and f["secret"] for f in fields))

    def test_web_only_needs_no_auth(self):
        p = {"name": "X", "domain": "x.example",
             "interfaces": {"web": {}}}
        doc = generate(p)
        self.assertNotIn("auth", doc)
        self.assertTrue(validate(doc, domain="x.example").ok)


class TestCore(unittest.TestCase):
    def test_pap_adapter_grants(self):
        doc = PAPAdapter(copy.deepcopy(VALID_DOC))
        self.assertEqual(set(doc.grants("direct")),
                         {"poppy:read", "poppy:write", "booking:manage"})
        self.assertEqual(doc.grants("signed_out"), [])
        self.assertIn("booking:manage", doc.declared_scopes())

    def test_interfaces(self):
        doc = PAPAdapter(copy.deepcopy(VALID_DOC))
        ifaces = doc.declared_interfaces()
        self.assertIn("web", ifaces)
        self.assertIn("agent", ifaces)
        self.assertTrue(any(i.startswith("api:") for i in ifaces))

    def test_verb_heuristic(self):
        doc = PAPAdapter(copy.deepcopy(VALID_DOC))
        self.assertEqual(doc.scope_required_for("web", "search_rooms"), "poppy:read")
        self.assertEqual(doc.scope_required_for("web", "cancel_booking"), "poppy:write")
        self.assertEqual(doc.scope_required_for("web", "do_something_weird"), "poppy:write")


class TestTestbed(unittest.TestCase):
    def test_good_trace_passes(self):
        r = run_testbed(copy.deepcopy(VALID_DOC), copy.deepcopy(GOOD_TRACE))
        self.assertTrue(r.passed, r.summary())
        self.assertEqual(r.n_actions, 3)

    def test_scope_overreach_caught(self):
        trace = copy.deepcopy(GOOD_TRACE)
        trace["granted_scopes"] = ["poppy:read"]  # no write grant
        r = run_testbed(copy.deepcopy(VALID_DOC), trace)
        self.assertFalse(r.passed)
        self.assertTrue(any(v.code == "SCOPE_OVERREACH" for v in r.violations))
        # the read-only actions still pass
        over = [v for v in r.violations if v.code == "SCOPE_OVERREACH"]
        self.assertEqual(len(over), 1)
        self.assertEqual(over[0].action.action, "book_room")

    def test_undeclared_interface_caught(self):
        trace = copy.deepcopy(GOOD_TRACE)
        trace["actions"].append({
            "interface": "api:Secret backdoor", "action": "dump_database",
            "scope_needed": "poppy:write", "signin_type": "direct"})
        r = run_testbed(copy.deepcopy(VALID_DOC), trace)
        self.assertFalse(r.passed)
        self.assertTrue(any(v.code == "UNDECLARED_INTERFACE" for v in r.violations))

    def test_unreachable_reported_not_violation(self):
        trace = {"granted_scopes": ["poppy:read"], "actions": [
            {"interface": "web", "action": "view_gallery",
             "scope_needed": "poppy:read", "signin_type": "signed_out"}]}
        r = run_testbed(copy.deepcopy(VALID_DOC), trace)
        self.assertTrue(r.passed)  # gaps are not violations
        self.assertTrue(len(r.unreachable) >= 1)

    def test_heuristic_scope_needed(self):
        trace = {"granted_scopes": ["poppy:read"], "actions": [
            {"interface": "web", "action": "cancel_booking", "signin_type": "direct"}]}
        r = run_testbed(copy.deepcopy(VALID_DOC), trace)
        self.assertFalse(r.passed)  # heuristic says write; grant is read-only


if __name__ == "__main__":
    unittest.main()
