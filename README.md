# MCP Chassis Server

An extensible [Model Context Protocol](https://modelcontextprotocol.io/) server chassis in Python. Fork it, add your extensions, and you have a production-ready MCP server with built-in security middleware, extension auto-discovery, and configuration management.

## Features

- **Security middleware pipeline** — I/O limits, authentication, rate limiting, input sanitization, and input validation applied automatically before handlers run
- **Extension auto-discovery** — drop `.py` files into `extensions/tools/`, `extensions/resources/`, or `extensions/prompts/` and they're registered at startup
- **Three security profiles** — `strict` (production), `moderate` (development), `permissive` (testing) with per-feature overrides
- **Configuration via TOML** — with environment variable overrides and named profile defaults

## Quick Start

```bash
pip install -e ".[dev]"
python -m mcp_chassis
```

See [docs/FORK_GUIDE.md](docs/FORK_GUIDE.md) for full setup, extension authoring, and configuration docs.

## Security Middleware

The middleware pipeline processes every tool request in this order:

```
I/O limits → Auth → Rate limit → Sanitize → Validate
```

Sanitization runs before validation so that validators operate on cleaned data.

### Input Sanitization

Three levels control what sanitization is applied:

| Level | Behavior |
|---|---|
| `strict` | Unicode NFC normalization, control char removal, path traversal removal (with URL-decoding and stacked-payload protection), shell metacharacter removal (including quotes, tilde, newline) |
| `moderate` | Control char removal, null byte removal, path traversal removal (with URL-decoding and stacked-payload protection) |
| `permissive` | Null byte removal only |

Path traversal sanitization decodes percent-encoded traversal characters (`%2e`, `%2f`, `%5c`) and applies removal in a loop until no traversal patterns remain, preventing evasion via stacked payloads like `....//`.

### Input Validation

Validates tool arguments against JSON schemas: required fields, types, string length, array length, and nesting depth. Schemas that set `"additionalProperties": false` will reject unexpected keys.

### Error Verbosity

Error responses can include detailed internal information (validation limits, schema paths) or generic messages with only an error code and correlation ID. Controlled by the `detailed_errors` setting:

```toml
[security]
detailed_errors = true   # Show detailed error messages (default: false for strict, true for moderate/permissive)
```

When `false`, error responses contain only the error code and a correlation ID for server-side log lookup. When `true`, the full error message is included, which helps LLM clients self-correct.

### Extension Security

Extension files are checked for safe permissions before import. World-writable files are rejected with a warning. All extension imports are logged at WARNING level to create an audit trail.

Extension directories should be writable only by trusted users or build processes. See the security note in `src/mcp_chassis/extensions/__init__.py` for details.

## Security Profiles

| Profile | Rate Limit | I/O Limits | Sanitization | Error Detail |
|---|---|---|---|---|
| `strict` | 60 rpm global, 30 rpm/tool | 1 MB req, 5 MB resp | Full (path traversal, shell metachars, control chars) | Generic |
| `moderate` | 120 rpm global, 60 rpm/tool | 5 MB req, 20 MB resp | Path traversal + control chars | Detailed |
| `permissive` | Disabled | 50 MB req/resp | Null bytes only | Detailed |

## Configuration

Edit `config/default.toml` or use environment variables:

```bash
MCP_LOG_LEVEL=DEBUG
MCP_SECURITY_PROFILE=moderate
MCP_RATE_LIMIT_ENABLED=false
MCP_CHASSIS_CONFIG=/path/to/config.toml
MCP_AUTH_TOKEN=secret123        # For future HTTP transport only
```

> **Note:** Token auth (`provider = "token"`) is not supported on the stdio transport.
> Over stdio, the OS provides process-level isolation. Token auth will be enforced
> when HTTP transport is implemented.

See [docs/FORK_GUIDE.md](docs/FORK_GUIDE.md) for the full TOML configuration reference.

## Testing

```bash
python -m pytest tests/              # All tests
python -m pytest tests/unit/         # Unit tests only
python -m pytest tests/integration/  # Integration tests only
```

## Project Documentation

| Document | Purpose |
|---|---|
| [docs/FORK_GUIDE.md](docs/FORK_GUIDE.md) | How to add tools, resources, prompts, and configure the server. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Component design and data flow. |
| [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Manual testing instructions. |
| [docs/NARRATIVE.md](docs/NARRATIVE.md) | Description of server for non-developer tech staff. |
| [docs/MIGRATION_NOTES.md](docs/MIGRATION_NOTES.md) | Notes for the migration of this server to MCP SDK version 2.0 when it is released in 2026. |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | General troubleshooting guide. |
