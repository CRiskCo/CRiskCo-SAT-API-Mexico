"""CRiskCo RFC validation, server-side. Response is kept out of logs."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criskco import ApiError, Client

if __name__ == "__main__":
    try:
        result = Client.from_env().validate_rfc(os.environ.get("CRISKCO_TAX_ID"))
        print("RFC validation response received; inspect its verified schema in your application.")
        # A successful request is not an assertion that the RFC is valid.
    except (ApiError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)

