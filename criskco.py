"""Small server-side CRiskCo client. No direct SAT calls; no third-party connector."""
import json
import os
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE_URL = "https://service.criskco.com/apiservice.svc"
ROUTES = {
    ("GET", "/ValidateRFC"),
    ("GET", "/get-applicants"),
    ("GET", "/GetCompanyTaxStatus"),
    ("GET", "/GetCompanyFiscalDetails"),
    ("POST", "/applicantinfo"),
    ("POST", "/ar-transactions/invoices"),
    ("POST", "/ap-transactions/invoices"),
    ("POST", "/OnboardingSatIntegration"),
}

class ApiError(Exception):
    """Sanitized failure: deliberately excludes credentials, identifiers and payloads."""

class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Client:
    def __init__(self, api_id, api_key):
        if not api_id or not api_key:
            raise ValueError("Both CRiskCo credentials are required")
        self._headers = {"apiId": api_id, "apiKey": api_key,
                         "Content-Type": "application/json", "Accept": "application/json"}
        self._opener = build_opener(NoRedirects())

    @classmethod
    def from_env(cls):
        if os.environ.get("CRISKCO_ENABLE_LIVE") != "1":
            raise ValueError("Set CRISKCO_ENABLE_LIVE=1 only after checking account and access scope")
        return cls(os.environ.get("CRISKCO_API_ID"), os.environ.get("CRISKCO_API_KEY"))

    def request(self, method, path, *, params=None, body=None):
        if (method, path) not in ROUTES:
            raise ValueError("Route is outside this example's CRiskCo allowlist")
        url = BASE_URL + path
        if params:
            url += "?" + urlencode(params)
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers=self._headers, method=method)
        # No automatic retries: replaying an onboarding request may duplicate work.
        try:
            with self._opener.open(req, timeout=30) as response:
                raw = response.read(10_000_001)
        except HTTPError as error:
            code = error.code
            error.close()
            raise ApiError(f"CRiskCo HTTP {code}; inspect securely before retrying") from None
        except (URLError, TimeoutError, OSError):
            raise ApiError("CRiskCo transport failure; outcome may be unknown") from None
        if len(raw) > 10_000_000:
            raise ApiError("Response exceeds example size limit; consult documented paging/export options")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ApiError("CRiskCo returned non-JSON data") from None
        if isinstance(result, dict) and result.get("success") is False:
            raise ApiError("CRiskCo reported an application failure")
        return result

    def validate_rfc(self, rfc):
        if not rfc:
            raise ValueError("RFC required")
        return self.request("GET", "/ValidateRFC", params={"rfc": rfc})

    def onboard(self, *, rfc, ciec, email, ref_id, consent_date, terms_version, accepted):
        if accepted is not True:
            raise ValueError("Actual applicant acceptance is required")
        try:
            accepted_on = date.fromisoformat(consent_date)
        except (ValueError, TypeError):
            raise ValueError("Use actual acceptance date as YYYY-MM-DD") from None
        if accepted_on > date.today():
            raise ValueError("Acceptance date cannot be in the future")
        if not all((rfc, ciec, email, ref_id, terms_version)):
            raise ValueError("Applicant, credential, reference and terms fields are required")
        return self.request("POST", "/OnboardingSatIntegration", body={
            "IsAgreeTerms": True, "DateAgreeTerms": consent_date,
            "VersionAgreeTerms": terms_version, "Email": email, "User": rfc,
            "Password": ciec, "RefApplicantId": ref_id,
        })

def applicant_state(payload, expected_tax_id):
    """Accept two published shapes; reject ambiguity instead of selecting row zero."""
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise ApiError("Invalid applicant response")
    if "ApiApplicantData" in payload and "applicant" in payload:
        raise ApiError("Ambiguous applicant response envelopes")
    if "ApiApplicantData" in payload:
        records = payload["ApiApplicantData"]
        records = [records] if isinstance(records, dict) else records
    elif "applicant" in payload:
        records = payload["applicant"]
    else:
        raise ApiError("Unknown applicant envelope; reconcile API contract")
    if records == []:
        return None
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ApiError("Expected exactly one applicant for the RFC query")
    record = records[0]
    # Some published samples omit taxId. Validate it whenever it is returned.
    if "taxId" in record and record["taxId"] != expected_tax_id:
        raise ApiError("Returned applicant does not match requested RFC")
    status = record.get("onboardingStatus", record.get("status"))
    if ("onboardingStatus" in record and "status" in record
            and record["onboardingStatus"] != record["status"]):
        raise ApiError("Conflicting applicant statuses")
    if status not in {"Available", "Processing", "Not Connected"}:
        raise ApiError("Unknown applicant status; reconcile API contract")
    if status == "Not Connected":
        raise ApiError("Applicant is not connected; review authorized onboarding")
    if status != "Available":
        return None
    applicant_id = record.get("applicantId")
    if not applicant_id:
        raise ApiError("Available response is missing applicantId")
    return str(applicant_id)

def wait_for_applicant(client, rfc, *, attempts=6, interval=5, sleep=time.sleep):
    if not 1 <= attempts <= 12 or not 0 <= interval <= 30:
        raise ValueError("Polling must be bounded")
    for attempt in range(attempts):
        result = client.request("GET", "/get-applicants",
                                params={"taxId": rfc, "onboardingStatus": "true"})
        applicant_id = applicant_state(result, rfc)
        if applicant_id:
            return applicant_id
        if attempt + 1 < attempts:
            sleep(interval)
    raise ApiError("Applicant was not ready within the polling window")

def credit_evidence(client, rfc):
    """Collect separate evidence sources; never calculate an approval decision."""
    applicant_id = wait_for_applicant(client, rfc)
    packet = {}
    for label, method, path, params, body in [
        ("applicant", "POST", "/applicantinfo", None, {"applicantId": applicant_id}),
        ("receivables", "POST", "/ar-transactions/invoices", None, {"applicantId": applicant_id}),
        ("payables", "POST", "/ap-transactions/invoices", None, {"applicantId": applicant_id}),
        ("compliance_opinion", "GET", "/GetCompanyTaxStatus", {"taxId": rfc}, None),
        ("fiscal_details", "GET", "/GetCompanyFiscalDetails", {"taxId": rfc}, None),
    ]:
        try:
            raw = client.request(method, path, params=params, body=body)
            # Transport success is not evidence completeness, validity or creditworthiness.
            packet[label] = {"retrieved": True, "interpretation": "not_evaluated", "raw": raw}
        except ApiError as error:
            packet[label] = {"retrieved": False, "interpretation": "unknown",
                             "error": str(error)}
    return packet

