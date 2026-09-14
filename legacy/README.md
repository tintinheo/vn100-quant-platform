# Historical artifacts — disabled

Nothing in this directory is active application source. The directory is
excluded from Python package discovery, source/wheel distributions, dependency
resolution, and pytest discovery. `legacy/__init__.py` additionally fails closed
if a checkout-root import is attempted. Do not extract an archive over `src/`,
add this directory/archive to `PYTHONPATH`, or install dependencies from within
an archive.

## v3.1 GPTCode implementation archive

`vnquant_realdata_v3_1_gptcode_impl.zip` (SHA-256
`4eff7a9c2b85610305c5aa0744798ab0803c03342187d03855bdbe57016de0a1`) is the
unaltered, historical v3.1 implementation bundle. It is retained solely for
provenance and regression archaeology. Its embedded `vnquant/` package is not
the maintained package despite sharing that name.

The archive contains the retired paths below:

- `vnquant/data/ssi.py`: `SSIFastConnectV3Provider`, which read
  `SSI_CLIENT_ID`, `SSI_API_KEY`, and `SSI_API_SECRET` and imported `ssi_sdk`.
- `vnquant/jobs/doctor.py`: an SSI-specific credential/network/schema preflight.
- `vnquant/jobs/bootstrap.py`: an SSI-specific VN100/security-master and OHLCV
  bootstrap.
- `.env.example`, `README.md`, and `requirements-local.txt`: historical SSI
  credential/setup and `ssi-sdk` installation material.
- `IMPLEMENTATION_REPORT_GPTCODE_STYLE.md`: the historical implementation
  report; the repository copy is preserved beside this README with an explicit
  disabled banner.

These files predate the 3.5 SSI-Free DNSE-First Auto-Sync baseline. They must
not be imported, executed, deployed, installed, collected as tests, or used as
a provider fallback. The active generic doctor/bootstrap commands live under
`src/vnquant/jobs/` and remain governed by provider admission. Negative SSI
retirement tests are intentionally retained to prevent reintroduction.

Historical claims in the archive (including its 18-test result) are legacy
evidence only, not current test evidence and not live/real-data validation.
