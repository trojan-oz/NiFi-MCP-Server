"""Regression tests for safety-critical NiFi MCP behaviour."""
import unittest

import requests

from nifi_mcp_server.client import NiFiClient, NiFiError
from nifi_mcp_server.server import _redact_sensitive


class FakeResponse:
    def __init__(self, status_code=200, body=None, text="response"):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self.reason = "test response"
        self.text = text
        self.content = text.encode()
        self._body = body if body is not None else {"ok": True}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, *, get_responses=None, post_responses=None, get_error=None, post_error=None):
        self.headers = {}
        self.get_responses = list(get_responses or [])
        self.post_responses = list(post_responses or [])
        self.get_error = get_error
        self.post_error = post_error
        self.get_calls = 0
        self.post_calls = 0

    def get(self, *args, **kwargs):
        self.get_calls += 1
        if self.get_error:
            raise self.get_error
        return self.get_responses.pop(0) if self.get_responses else FakeResponse()

    def post(self, *args, **kwargs):
        self.post_calls += 1
        if self.post_error:
            raise self.post_error
        return self.post_responses.pop(0) if self.post_responses else FakeResponse()


class HardeningTests(unittest.TestCase):
    def test_redaction_is_case_insensitive_and_normalizes_separators(self):
        payload = {
            "Authorization": "Bearer secret",
            "clientSecret": "secret-1",
            "apiKey": "secret-2",
            "access_token": "secret-3",
            "x-api-key": "secret-4",
            "kerberosKeytab": "secret-5",
            "sslKeystorePasswd": "secret-6",
            "nested": {"COOKIE": "session=secret", "refresh-token": "secret-7"},
            "tokenizerMode": "keep-me",
            "displayName": "keep-me-too",
        }
        result = _redact_sensitive(payload)
        for key in ("Authorization", "clientSecret", "apiKey", "access_token", "x-api-key", "kerberosKeytab", "sslKeystorePasswd"):
            self.assertEqual(result[key], "***REDACTED***", key)
        self.assertEqual(result["nested"]["COOKIE"], "***REDACTED***")
        self.assertEqual(result["nested"]["refresh-token"], "***REDACTED***")
        self.assertEqual(result["tokenizerMode"], "keep-me")
        self.assertEqual(result["displayName"], "keep-me-too")

    def test_version_detection_never_falls_back_to_nifi_1(self):
        client = NiFiClient("https://nifi.invalid/nifi-api", FakeSession())
        client.get_version_info = lambda: {"about": {"version": "2.11.0-SNAPSHOT"}}
        self.assertEqual(client.get_version_tuple(), (2, 11, 0))

        unknown = NiFiClient("https://nifi.invalid/nifi-api", FakeSession())
        unknown.get_version_info = lambda: {"about": {}}
        with self.assertRaisesRegex(NiFiError, "Unable to determine NiFi version"):
            unknown.get_version_tuple()

        unavailable = NiFiClient("https://nifi.invalid/nifi-api", FakeSession(get_error=requests.Timeout("offline")))
        with self.assertRaises(requests.Timeout):
            unavailable.get_version_tuple()

    def test_mutating_post_is_not_automatically_retried(self):
        session = FakeSession(post_error=requests.Timeout("response lost"))
        client = NiFiClient("https://nifi.invalid/nifi-api", session)
        with self.assertRaises(requests.Timeout):
            client._post("process-groups/root/process-groups", {"component": {"name": "example"}})
        self.assertEqual(session.post_calls, 1)

    def test_read_does_not_retry_non_retryable_client_errors(self):
        session = FakeSession(get_responses=[FakeResponse(400, text="bad request")])
        client = NiFiClient("https://nifi.invalid/nifi-api", session)
        with self.assertRaises(NiFiError):
            client._get("flow/about")
        self.assertEqual(session.get_calls, 1)

    def test_failed_optional_health_checks_are_not_reported_healthy(self):
        class PartialClient(NiFiClient):
            def list_processors(self, pg_id):
                return {"processors": [{"component": {"name": "p1"}, "status": {"runStatus": "Running"}}]}

            def get_controller_services(self, pg_id=None):
                raise requests.Timeout("service endpoint timed out")

            def list_connections(self, pg_id):
                return {"connections": []}

            def get_bulletins(self, after_ms=None):
                raise requests.Timeout("bulletin endpoint timed out")

        client = PartialClient("https://nifi.invalid/nifi-api", FakeSession())
        health = client.get_flow_health_status("root")
        self.assertEqual(health["overallHealth"], "UNKNOWN")
        self.assertEqual(health["checks"]["processors"], "OK")
        self.assertEqual(health["checks"]["connections"], "OK")
        self.assertEqual(health["checks"]["controllerServices"], "FAILED")
        self.assertEqual(health["checks"]["bulletins"], "FAILED")
        self.assertTrue(any("Controller-service check failed" in e for e in health["errors"]))
        self.assertTrue(any("Bulletin check failed" in e for e in health["errors"]))


if __name__ == "__main__":
    unittest.main()
