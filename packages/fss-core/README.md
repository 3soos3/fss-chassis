# fss-core

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
