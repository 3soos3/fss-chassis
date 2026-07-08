# fss-mcp

[![PyPI](https://img.shields.io/pypi/v/fss-mcp)](https://pypi.org/project/fss-mcp/)
[![Python](https://img.shields.io/badge/python-3.11_%7C_3.12_%7C_3.13-blue)](https://pypi.org/project/fss-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/3soos3/fss-chassis/badge)](https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis)

FSS-compliant MCP server chassis. Build forensic-grade MCP servers that satisfy the [Forensic Software Standards (FSS)](https://fss.3soos3.online) conformance levels L1–L5.

## What it provides

- Security middleware pipeline: I/O limits → Auth → Rate limit → Sanitise → Validate
- `_provenance` block on every tool response (FSS-0004)
- Ed25519 signing of tool results (FSS-0005, L2+)
- FIT JWT verification (FSS-0006, L5)
- `/.well-known/fss-deployment.json` endpoint (FSS-0009, L4)
- HTTP and stdio transports
- OpenTelemetry integration

## Install

```bash
pip install fss-mcp

# with HTTP transport:
pip install "fss-mcp[http]"

# with auth middleware:
pip install "fss-mcp[auth]"

# with OpenTelemetry:
pip install "fss-mcp[otel]"

# everything:
pip install "fss-mcp[http,auth,otel]"
```

## Links

- Repository: <https://github.com/3soos3/fss-chassis>
- FSS standard: <https://fss.3soos3.online>
- OpenSSF Scorecard: <https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis>
- Security advisories: <https://github.com/3soos3/fss-chassis/security/advisories>
