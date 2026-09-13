# AGENTS.md — VN100 Quant Platform

## Required reading

Before changing code, read in this order:

1. docs/CURRENT_BASELINE.md
2. docs/BRD-VN100-Quant-Platform-SSI-FREE-MULTI-SOURCE.md
3. docs/SRD-VN100-Quant-Platform-SSI-FREE-MULTI-SOURCE.md
4. docs/CHANGELOG_SSI_FREE_MULTI_SOURCE.md

The BRD is the source of truth for business rules, trading rules,
thresholds, assumptions and validation requirements.

The SRD defines how the BRD must be implemented.

Do not invent a new threshold in code.

## Current architecture

Current baseline:
v3.3 SSI-Free Multi-Source.

SSI FastConnect is OUT OF SCOPE.

Do not:
- add SSI SDK
- add SSI credentials
- restore SSI bootstrap
- use vnstock
- implement auto trading
- implement order routing
- silently fall back to Yahoo or undocumented APIs
- scrape undocumented production endpoints
- fabricate real-data results

## Data provider state

No automated provider is currently ADMITTED.

Vietstock DataFeed is a provider candidate only.

CafeF is manual/reference/authorized-export validation by default.

Official field authorities include:
HOSE, HNX, VSDC, SSC and issuer disclosures.

If no admitted provider exists, the application must fail closed with:
NO_ADMITTED_PROVIDER.

## Assumptions

Any new:
- heuristic
- threshold
- inferred rule
- unsourced parameter

must be marked:

[GUESS]

Do not present [GUESS] values as validated alpha.

## Data integrity

Prevent:
- look-ahead bias
- survivorship bias
- future corporate-action leakage
- future fundamental publication leakage
- silent forward-fill of missing trading sessions
- current-universe substitution without warning

Historical proxy data must be labelled explicitly.

## Development workflow

For every task:

1. State what BRD/SRD requirements are being implemented.
2. Inspect existing implementation before editing.
3. Implement only the requested milestone.
4. Add regression/unit tests.
5. Run the full relevant test suite.
6. Report changed files.
7. Report assumptions.
8. Report unresolved issues.
9. Do not claim real-data validation unless real data was actually processed.

## Documentation governance

If research or implementation reveals a material change to:
- business rule
- architecture
- data-source policy
- market rule
- execution rule
- threshold
- validation policy
- known limitation

then BRD and SRD must be updated in the same PR.

Do not change only one of them.

## Pull requests

Prefer small PRs.

Each PR must include:

- Purpose
- BRD requirement
- SRD requirement
- Files changed
- Tests added
- Tests executed
- Results
- [GUESS] assumptions
- Known limitations
- Real-data status