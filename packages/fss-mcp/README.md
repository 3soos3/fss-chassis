# fss-mcp

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
