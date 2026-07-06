# Testing Guide — MCP Chassis Server

## How to Run the Application

### Prerequisites

- Python 3.11+
- `pip` or `uv` package manager

### Install

```bash
pip install -e ".[dev]"
```

Or with uv:
```bash
uv pip install -e ".[dev]"
```

### Run the Server

```bash
# With default config (config/default.toml)
python -m fss_mcp

# With custom config
python -m fss_mcp --config /path/to/config.toml

# With debug logging
python -m fss_mcp --log-level DEBUG

# Check version
python -m fss_mcp --version
```

The server communicates over **stdio** (stdin/stdout). It expects MCP JSON-RPC messages on stdin and writes responses to stdout. All logging goes to stderr.

### Run Tests

```bash
# All tests
python -m pytest

# Unit tests only
python -m pytest tests/unit/ -q

# Integration tests only (starts server subprocess)
python -m pytest tests/integration/ -q

# With verbose output
python -m pytest -v

# Specific test file
python -m pytest tests/unit/test_validation.py -v
```

### Lint and Type Check

```bash
# Lint
ruff check src/ tests/

# Type check
mypy src/

# Auto-format
ruff format src/ tests/
```

---

## What to Test Manually

### 1. Basic MCP Protocol

The server should respond correctly to the MCP protocol over stdio. You can test with a simple script or pipe JSON-RPC messages:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m fss_mcp --config config/default.toml 2>/dev/null
```

Expected: A JSON-RPC response with server capabilities.

### 2. Tool Listing

After initialization, send:
```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

Expected: Response listing `__health_check` and `example_echo` tools.

### 3. Tool Invocation — Echo

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"example_echo","arguments":{"message":"hello world"}}}
```

Expected: Response with `"hello world"` in content.

### 4. Health Check

```json
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"__health_check","arguments":{}}}
```

Expected: JSON with server_name, server_version, chassis_version, python_version, uptime_seconds, tools/resources/prompts loaded, and security_profile.

### 5. Resource Listing and Reading

```json
{"jsonrpc":"2.0","id":5,"method":"resources/list","params":{}}
{"jsonrpc":"2.0","id":6,"method":"resources/read","params":{"uri":"template://example/info"}}
```

Expected: Resource list includes `template://example/info`. Read returns JSON with server info.

### 6. Prompt Listing and Getting

```json
{"jsonrpc":"2.0","id":7,"method":"prompts/list","params":{}}
{"jsonrpc":"2.0","id":8,"method":"prompts/get","params":{"name":"example_greeting","arguments":{"name":"Alice"}}}
```

Expected: Prompt list includes `example_greeting`. Get returns a message greeting Alice.

### 7. Security — Input Validation

```json
{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"example_echo","arguments":{"message":123}}}
```

Expected: Error response — `message` should be a string, not integer.

### 8. Security — Unknown Tool

```json
{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"nonexistent","arguments":{}}}
```

Expected: Error response with `TOOL_NOT_FOUND`.

### 9. Security Profiles

Test with different profiles by modifying `config/default.toml`:
- `profile = "strict"` — default, all security features active
- `profile = "moderate"` — relaxed limits
- `profile = "permissive"` — minimal restrictions

Or override via environment:
```bash
MCP_SECURITY_PROFILE=permissive python -m fss_mcp
```

### 10. Debug Logging

```bash
MCP_LOG_LEVEL=DEBUG python -m fss_mcp 2>debug.log
```

Check `debug.log` for structured JSON log entries including correlation IDs.

---

## Expected Behaviors

| Feature | Expected |
|---------|----------|
| Server starts | Logs to stderr, waits for input on stdin |
| Initialize handshake | Returns capabilities (tools, resources, prompts) |
| Tool call | Runs middleware pipeline, returns result or error |
| Invalid input | Returns structured error with correlation ID |
| Rate limit exceeded | Returns error with retry-after timing |
| SIGTERM/SIGINT | Graceful shutdown with log message |
| Bad config file | Exits with CRITICAL log and non-zero code |
| Missing extension | Logs warning, continues without the extension |
| Oversized request | Rejected before reaching handler |

---

## Known Limitations

1. **Stdio only** — No HTTP transport in V1. SSE and StreamableHTTP transports are stubbed but raise `NotImplementedError`.

2. **No persistent rate limiting** — Rate limits are in-memory and reset on server restart. Suitable for single-instance stdio deployment.

3. **No async rate limiter lock** — The token bucket is synchronous. Under CPython's single-threaded async model this is safe, but under alternative runtimes (e.g., concurrent threads) it could have race conditions.

4. **JSON Schema validation is basic** — Validates types, required fields, enum constraints, `additionalProperties` rejection, and structural limits (string length, array length, depth). Does NOT validate `pattern`, `format`, or complex schema features like `oneOf`/`anyOf`.

5. **Auth framework is stubbed** — `NoAuthProvider` (default) allows everything. `TokenAuthProvider` is implemented but auth is disabled by default for stdio. Enable for HTTP transport.

6. **Extension auto-discovery scans at startup only** — Adding new extensions requires a server restart.

7. **No hot-reload** — Configuration changes require a server restart.

8. **MCP SDK version** — Built against `mcp>=1.2.0,<2.0`. When MCP SDK v2.0 stabilizes, the template internals will need migration (see MIGRATION_NOTES.md). Fork extension code should NOT need changes.
