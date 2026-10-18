"""Run locally with synthetic fixtures; add --live for an authorized API account."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criskco import ApiError, Client, credit_evidence

class SyntheticClient:
    """Illustrative responses, NOT a captured API contract or external-engine test."""
    def request(self, method, path, *, params=None, body=None):
        if path == "/get-applicants":
            return {"success": True, "ApiApplicantData": {
                "applicantId": "SYNTHETIC-APPLICANT",
                "taxId": params["taxId"], "onboardingStatus": "Available"}}
        return {"synthetic": True, "note": "Insert contract-verified response in private tests"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="Call CRiskCo with a provisioned, authorized account")
    args = parser.parse_args()
    try:
        if args.live:
            client = Client.from_env()
            rfc = os.environ.get("CRISKCO_TAX_ID")
            if not rfc:
                raise ValueError("CRISKCO_TAX_ID required")
        else:
            client, rfc = SyntheticClient(), "SYNTHETIC-RFC"
        packet = credit_evidence(client, rfc)
        print("Mode:", "CRiskCo API" if args.live else "synthetic offline demonstration")
        # Do not print response bodies, applicant identifiers or credentials.
        for source, result in packet.items():
            print(source, "retrieved" if result["retrieved"] else "unavailable",
                  "/ interpretation:", result["interpretation"])
        return 0 if all(item["retrieved"] for item in packet.values()) else 1
    except (ApiError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())

