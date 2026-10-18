import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from criskco import Client, ApiError, NoRedirects, applicant_state, wait_for_applicant, credit_evidence

class Fake:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result

def ready(**extra):
    return {"success": True, "ApiApplicantData": {
        "applicantId": "test-1", "taxId": "TEST", "onboardingStatus": "Available", **extra}}

class Tests(unittest.TestCase):
    def test_both_documented_status_shapes(self):
        self.assertEqual(applicant_state(ready(), "TEST"), "test-1")
        self.assertEqual(applicant_state({"applicant": [{"applicantId": "test-2",
                                                       "status": "Available"}]}, "TEST"), "test-2")

    def test_ambiguity_mismatch_unknown_fail_closed(self):
        for payload in [
            ready(taxId="OTHER"), ready(onboardingStatus="SomethingNew"),
            {"applicant": [{"status": "Available"}, {"status": "Available"}]},
            {"new_envelope": []}, {"success": False}, ready(applicantId=None),
            {**ready(), "applicant": []}, ready(status="Processing"),
        ]:
            with self.subTest(payload=payload), self.assertRaises(ApiError):
                applicant_state(payload, "TEST")

    def test_polling_bounded_and_no_final_sleep(self):
        client = Fake([{"applicant": []}] * 3)
        sleeps = []
        with self.assertRaises(ApiError):
            wait_for_applicant(client, "TEST", attempts=3, interval=1, sleep=sleeps.append)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(sleeps, [1, 1])

    def test_not_connected_stops(self):
        with self.assertRaises(ApiError):
            wait_for_applicant(Fake([ready(onboardingStatus="Not Connected")]), "TEST")

    def test_missing_source_is_unknown_not_negative(self):
        client = Fake([ready(), {}, ApiError("Unavailable"), [], {}, {}])
        packet = credit_evidence(client, "TEST")
        self.assertFalse(packet["receivables"]["retrieved"])
        self.assertEqual(packet["receivables"]["interpretation"], "unknown")
        self.assertEqual(packet["payables"]["interpretation"], "not_evaluated")
        self.assertEqual(client.calls[1][2]["body"], {"applicantId": "test-1"})

    def test_no_onboarding_without_recorded_consent(self):
        client = Client("fake", "fake")
        with patch.object(client, "request") as send:
            with self.assertRaises(ValueError):
                client.onboard(rfc="TEST", ciec="secret", email="test@example.invalid",
                               ref_id="test-1", consent_date="2026-01-01",
                               terms_version="test", accepted=False)
            send.assert_not_called()

    def test_no_arbitrary_endpoints_or_redirects(self):
        client = Client("fake", "fake")
        with self.assertRaises(ValueError):
            client.request("GET", "https://other.example")
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "", {}, "https://other.example"))

    def test_api_headers_route_and_timeout(self):
        client = Client("fake-id", "fake-key")
        with patch.object(client._opener, "open") as transport:
            transport.return_value.__enter__.return_value.read.return_value = b'{"success":true}'
            client.validate_rfc("TEST")
            request = transport.call_args.args[0]
            self.assertEqual(request.full_url, "https://service.criskco.com/apiservice.svc/ValidateRFC?rfc=TEST")
            self.assertEqual(request.get_header("Apiid"), "fake-id")
            self.assertEqual(transport.call_args.kwargs["timeout"], 30)

    def test_transport_error_sanitized_and_not_retried(self):
        client = Client("fake-id", "fake-key")
        for error in [URLError("secret payload"), HTTPError("https://secret", 401, "secret", {}, None)]:
            with patch.object(client._opener, "open", side_effect=error) as transport:
                with self.assertRaises(ApiError) as caught:
                    client.validate_rfc("TEST")
                self.assertNotIn("secret", str(caught.exception))
                self.assertEqual(transport.call_count, 1)

    def test_invalid_and_failed_json(self):
        for raw in [b"not json", b'{"success":false,"responseDetails":"secret"}']:
            client = Client("fake", "fake")
            with patch.object(client._opener, "open") as transport:
                transport.return_value.__enter__.return_value.read.return_value = raw
                with self.assertRaises(ApiError) as caught:
                    client.validate_rfc("TEST")
                self.assertNotIn("secret", str(caught.exception))

if __name__ == "__main__":
    unittest.main()

