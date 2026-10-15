"""Optional explicit mutation; prefer CRiskCo-hosted onboarding for a first integration."""
import getpass
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criskco import ApiError, Client

if __name__ == "__main__":
    try:
        client = Client.from_env()
        print("This sends a NEW onboarding request to CRiskCo. Check for an existing applicant first.")
        if input("Type SEND to proceed: ").strip() != "SEND":
            raise ValueError("No request sent")
        # These values must come from the actual applicant consent record.
        accepted = input("Was applicant acceptance actually recorded? Type YES: ").strip() == "YES"
        consent_date = input("Recorded acceptance date (YYYY-MM-DD): ").strip()
        version = input("Actual accepted terms version: ").strip()
        email = input("Applicant email: ").strip()
        ref_id = input("Unique internal applicant reference: ").strip()
        ciec = getpass.getpass("Applicant-authorized SAT password (hidden): ")
        try:
            result = client.onboard(rfc=os.environ.get("CRISKCO_TAX_ID"), ciec=ciec,
                                    email=email, ref_id=ref_id, consent_date=consent_date,
                                    terms_version=version, accepted=accepted)
        finally:
            ciec = None  # Releases this reference; Python cannot promise secure memory erasure.
        print("Onboarding response received. Poll separately; do not assume completion.")
    except (ApiError, ValueError, EOFError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)

