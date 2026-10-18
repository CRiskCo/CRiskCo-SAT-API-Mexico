# CRiskCo-SAT-API-Mexico

Python integration examples for Mexican business credit workflows through **CRiskCo APIs**.

Ejemplos de integración en Python para flujos de crédito empresarial en México mediante las APIs de **CRiskCo**.

This is a small educational starter, not an official SDK or a credit decision engine. Every live data request goes to CRiskCo. Offline fixtures are clearly synthetic. No direct SAT connector or other data vendor is included.

## Start here / Inicio rápido

Python 3.11+; standard library only. From the repository directory:

```sh
python -m unittest discover -s tests -v
python examples/credit_workflow.py
```

The default workflow is offline. It demonstrates orchestration, not actual applicant data.

For live calls, provision a CRiskCo account and verify its environment, permissions, approved use and billing with CRiskCo. Set CRISKCO_API_ID, CRISKCO_API_KEY and CRISKCO_TAX_ID securely on your server. Set CRISKCO_ENABLE_LIVE=1 explicitly. An .env.example template is supplied; the examples do not auto-load .env files.

```sh
python examples/validate_rfc.py
python examples/credit_workflow.py --live
```

Do not put keys in browser JavaScript, Lovable public frontend variables, repository files, command-line arguments, screenshots or issue reports.

## Workflows / Flujos

| Example | Purpose |
|---|---|
| examples/validate_rfc.py | Request RFC validation; interpret the response using the verified account contract. |
| examples/credit_workflow.py | Wait for one authorized applicant, retrieve separate business, AR/AP and fiscal evidence, and preserve missingness. |
| examples/onboard_applicant.py | Optional explicit onboarding request with actual recorded consent. Prompts hide the SAT password. |

For the simplest initial integration, use CRiskCo-hosted onboarding and then run the read workflow. Follow the [integration guide](https://criskco.com/developers/api-guide) to obtain the correct registered reference and hosted flow. An onboarding reference code must not be assumed identical to a per-applicant reference.

The credit example covers assembling an evidence packet for analyst review. It does not treat invoicing as cash receipts, a fiscal document as credit approval, an empty response as a negative signal, or a successful HTTP call as complete coverage. It returns source responses unchanged in memory; it deliberately avoids financial calculations before schemas, cancellation treatment, currency and period coverage are verified.

## How to use the packet in a server application

```python
from criskco import Client, credit_evidence

client = Client.from_env()
packet = credit_evidence(client, authorized_applicant_rfc)
# Connect packet to your private analyst workflow.
# Check each source's retrieved flag, validate its raw schema,
# and preserve unknown states. Do not log raw taxpayer data.
```

## API contract and validation status

Reviewed against CRiskCo public documentation on 12 October 2026:

- [Integration guide](https://criskco.com/developers/api-guide)
- [Published examples](https://criskco.com/en/developers/code-samples)
- [Endpoint explorer](https://criskco.com/developers/api-explorer)
- [Full reference](https://api-docs.criskco.com/) — unavailable during this research session; verify before production use.

The public guide uses ApiApplicantData/onboardingStatus; the published example uses applicant/status. The adapter handles these two shapes, rejects multiple applicants, unknown states and conflicting fields, and verifies taxId when returned. This is compatibility with published examples, not confirmation of the live production contract.

No API credentials or actual taxpayer records were used to build or test this package. Tests mock transport and validate orchestration and failure handling. Live API contract testing remains outstanding. Financial/fiscal payloads stay unnormalized until that validation is complete. Check pagination, rate limits, retention, entitlements, data recency and error semantics for your provisioned account.

## Onboarding / Consentimiento

Do not run onboarding to test connectivity. Check for an existing applicant first. The interactive mutation requires the applicant's actual acceptance date and terms version, authorized credentials and a unique reference. The SEND prompt confirms the operator's intention; it is not the applicant's consent. Do not retry an ambiguous timeout automatically.

Para conectar una empresa, confirma la autorización del solicitante y registra los términos realmente aceptados. Nunca inventes una fecha o versión de consentimiento. Los datos ausentes permanecen como desconocidos; no equivalen a incumplimiento.

## Production handoff

- Keep secrets server-side and configure access controls, private audit records and a retention policy.
- Verify every endpoint and response on a provisioned test account before production.
- Configure bounded timeouts, account-specific quotas and reviewed retry rules; mutations need reconciliation.
- Validate document freshness and completeness before making any business decision.
- Add webhooks only after verifying authentication, replay handling and delivery semantics. This starter does not invent a webhook signature scheme.
- SIGER/RUG, shareholder coverage and licensing are outside this starter.
- Choose and approve a code license before public release. No third-party SDK dependencies are bundled.

## Resources / Recursos

[CRiskCo](https://criskco.com/) · [Developer resources](https://criskco.com/developers/api-guide) · [English samples](https://criskco.com/en/developers/code-samples)

Repository description suggestion: “CRiskCo API integration examples for Mexican SME credit workflows: RFC validation, authorized SAT onboarding and fiscal evidence.”

Suggested relevant topics: criskco, mexico, fintech, credit-risk, sat-mexico, cfdi, kyb, python.
Do not add astronomy or satellite tags merely because they contain “SAT”.

