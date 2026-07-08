# fss-core

[![PyPI](https://img.shields.io/pypi/v/fss-core)](https://pypi.org/project/fss-core/)
[![Python](https://img.shields.io/badge/python-3.11_%7C_3.12_%7C_3.13-blue)](https://pypi.org/project/fss-core/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/3soos3/fss-chassis/badge)](https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis)

Protocol primitives for the [Forensic Software Standards (FSS)](https://fss.3soos3.online) series. Used by FSS-compliant forensic tool providers to produce auditable, signed provenance records on every tool invocation.

## What it provides

- **`provenance`** — construct and sign `_provenance` blocks (FSS-0004)
- **`integrity`** — JCS (RFC 8785) canonical form and SHA-256 CAI hashes (FSS-0005)
- **`errors`** — standard FSS error codes (`FSS_AUTH_DENIED`, `FSS_RATE_LIMITED`, …)
- **`fss_context`** — context variables for investigation ID, FIT token, analyst identity

## Install

```bash
pip install fss-core

# with JWT/Ed25519 auth support (L2+):
pip install "fss-core[auth]"
```

## Links

- Repository: <https://github.com/3soos3/fss-chassis>
- FSS standard: <https://fss.3soos3.online>
- OpenSSF Scorecard: <https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis>
- Security advisories: <https://github.com/3soos3/fss-chassis/security/advisories>
