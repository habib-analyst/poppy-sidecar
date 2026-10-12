import copy
import unittest

from poppy_sidecar.validator import validate
from tests.fixtures import VALID_DOC


class TestValidatorHappyPath(unittest.TestCase):
    def test_valid_doc_passes(self):
        r = validate(copy.deepcopy(VALID_DOC), domain="testguest.example")
        self.assertTrue(r.ok, str(r))
        self.assertEqual(r.errors, [])

    def test_valid_doc_without_domain_check(self):
        r = validate(copy.deepcopy(VALID_DOC))
        self.assertTrue(r.ok, str(r))

    def test_www_prefix_ignored(self):
        r = validate(copy.deepcopy(VALID_DOC), domain="www.testguest.example")
        self.assertTrue(r.ok, str(r))

    def test_minimal_doc_web_only_no_auth(self):
        doc = {"protocol_version": "0.1",
               "organization": {"name": "X", "domain": "x.example"},
               "web": {}}
        r = validate(doc, domain="x.example")
        self.assertTrue(r.ok, str(r))


class TestValidatorNegative(unittest.TestCase):
    def v(self, mutate):
        doc = copy.deepcopy(VALID_DOC)
        mutate(doc)
        return validate(doc, domain="testguest.example")

    def codes(self, report):
        return {f.code for f in report.findings}

    def test_missing_version(self):
        r = self.v(lambda d: d.pop("protocol_version"))
        self.assertIn("MISSING_VERSION", self.codes(r))
        self.assertFalse(r.ok)

    def test_bad_version_format(self):
        r = self.v(lambda d: d.update(protocol_version="v1"))
        self.assertIn("BAD_VERSION", self.codes(r))

    def test_unsupported_major(self):
        r = self.v(lambda d: d.update(protocol_version="1.0"))
        self.assertIn("UNSUPPORTED_MAJOR", self.codes(r))

    def test_missing_organization(self):
        r = self.v(lambda d: d.pop("organization"))
        self.assertIn("MISSING_ORGANIZATION", self.codes(r))

    def test_domain_mismatch(self):
        r = validate(copy.deepcopy(VALID_DOC), domain="evil.example")
        self.assertIn("DOMAIN_MISMATCH", self.codes(r))

    def test_no_route(self):
        r = self.v(lambda d: [d.pop(k) for k in ("agent", "apis", "web")])
        self.assertIn("NO_ROUTE", self.codes(r))

    def test_missing_auth_with_apis(self):
        r = self.v(lambda d: d.pop("auth"))
        self.assertIn("MISSING_AUTH", self.codes(r))

    def test_bad_issuer_not_https(self):
        r = self.v(lambda d: d["auth"].update(issuer="http://auth.testguest.example"))
        self.assertIn("BAD_ISSUER", self.codes(r))

    def test_empty_scopes(self):
        r = self.v(lambda d: d["auth"]["direct"].update(scopes=[]))
        self.assertIn("BAD_SCOPES", self.codes(r))

    def test_reserved_scope(self):
        def m(d):
            d["auth"]["direct"]["scopes"].append("poppy:superuser")
        r = self.v(m)
        self.assertIn("RESERVED_SCOPE", self.codes(r))

    def test_undescribed_custom_scope_warns(self):
        def m(d):
            d["auth"]["direct"]["scopes"].append("loyalty:points")
        r = self.v(m)
        self.assertIn("UNDESCRIBED_SCOPE", self.codes(r))
        self.assertTrue(r.ok)  # warning only

    def test_bad_mediated_endpoint(self):
        r = self.v(lambda d: d["auth"]["mediated"].update(endpoint="http://x"))
        self.assertIn("BAD_MEDIATED_ENDPOINT", self.codes(r))

    def test_bad_mediated_field(self):
        def m(d):
            d["auth"]["mediated"]["fields"] = [{"name": "email"}]
        r = self.v(m)
        self.assertIn("BAD_MEDIATED_FIELD", self.codes(r))

    def test_bad_agent_endpoint(self):
        def m(d):
            d["agent"]["protocols"][0]["endpoint"] = "http://api.testguest.example/x"
        r = self.v(m)
        self.assertIn("BAD_AGENT_ENDPOINT", self.codes(r))

    def test_bad_api_url(self):
        def m(d):
            d["apis"][0]["url"] = "ftp://x/y.json"
        r = self.v(m)
        self.assertIn("BAD_API_URL", self.codes(r))

    def test_unknown_api_type_warns(self):
        def m(d):
            d["apis"][0]["type"] = "graphql"
        r = self.v(m)
        self.assertIn("UNKNOWN_API_TYPE", self.codes(r))
        self.assertTrue(r.ok)

    def test_missing_api_description_warns(self):
        def m(d):
            d["apis"][0].pop("description")
        r = self.v(m)
        self.assertIn("MISSING_API_DESCRIPTION", self.codes(r))
        self.assertTrue(r.ok)

    def test_bad_extension_name(self):
        def m(d):
            d["extensions"] = {"gift wrap": {"version": "1"}}
        r = self.v(m)
        self.assertIn("BAD_EXTENSION_NAME", self.codes(r))

    def test_good_extension_names(self):
        def m(d):
            d["extensions"] = {
                "operations": {"version": "1", "endpoint": "https://x/y"},
                "testguest.example/gift-wrap": {"version": "2"},
            }
        r = self.v(m)
        self.assertTrue(r.ok, str(r))

    def test_not_an_object(self):
        r = validate([1, 2, 3])
        self.assertIn("NOT_AN_OBJECT", self.codes(r))


if __name__ == "__main__":
    unittest.main()
