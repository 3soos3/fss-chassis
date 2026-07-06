# Fork Guide — MCP Chassis Server

This guide explains how to fork this MCP server chassis and extend it with your own tools, resources, and prompts. It is written for both AI agents and human developers.

---

## Quick Start

1. Fork or copy this repository.
2. Install dependencies: `pip install -e ".[dev]"`
3. Run tests to confirm the baseline works: `make test`
4. Add your extensions (see sections below).
5. Run the server: `python -m fss_mcp`

---

## Project Structure

```
packages/fss-mcp/src/fss_mcp/
├── extensions/
│   ├── __init__.py          # Auto-discovery logic (do not modify)
│   ├── batch.py             # Batch registration helper
│   ├── my_init.py           # ← Your init hook goes here
│   ├── tools/
│   │   ├── __init__.py
│   │   └── example_tool.py  # Example — copy to add tools
│   ├── resources/
│   │   ├── __init__.py
│   │   └── example_resource.py  # Example — copy to add resources
│   └── prompts/
│       ├── __init__.py
│       └── example_prompt.py    # Example — copy to add prompts
├── server.py                # ChassisServer (do not modify)
├── context.py               # HandlerContext (read-only)
├── config.py                # Configuration (read-only)
└── ...

config/
└── default.toml             # Server configuration
```

---

## Adding a Tool

Create a new `.py` file in `packages/fss-mcp/src/fss_mcp/extensions/tools/`.

**Template:**

```python
"""My custom tool."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fss_mcp.context import HandlerContext
    from fss_mcp.server import ChassisServer


def register(server: "ChassisServer") -> None:
    """Register this tool with the server."""
    server.register_tool(
        name="my_tool_name",
        description="A short description shown to the AI client.",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
                "param2": {"type": "integer", "description": "Second parameter"},
            },
            "required": ["param1"],
        },
        handler=_handle_my_tool,
    )


async def _handle_my_tool(
    arguments: dict[str, Any], context: "HandlerContext"
) -> str:
    """Handle calls to my_tool_name.

    Args:
        arguments: Validated and sanitized tool arguments.
        context: Handler context with logging and config access.

    Returns:
        Result string (or JSON-serializable dict/list).
    """
    param1 = arguments["param1"]
    param2 = arguments.get("param2", 0)
    await context.log_info("my_tool called with param1=%r", param1)
    return f"Result: {param1} + {param2}"
```

**Rules:**
- The file must define a `register(server)` function.
- The handler must be `async`.
- Return a `str` for plain text, or any JSON-serializable value (dict/list).
- Use `context.log_*()` for logging — never use `print()`.
- Never import from `mcp.*` directly in extension code.

**Batch registration (for many similar tools):**

If you have many tools that follow the same pattern — call a method on a shared object, return JSON — use the batch registration helper instead of one file per tool:

```python
"""My tools — batch registered."""

from fss_mcp.extensions.batch import register_simple_tools

TOOLS = [
    {
        "name": "my_get_item",
        "description": "Get an item by ID.",
        "method": "get_item",           # method name on the source object
        "param": "item_id",             # required parameter name
        "param_description": "The ID.",
        "not_found_check": True,        # return {"error": "not_found"} when None
    },
    {
        "name": "my_list_items",
        "description": "List all items.",
        "method": "list_items",          # no param = no-argument tool
    },
]

def register(server):
    source = server._my_shared_object
    if source is None:
        return
    register_simple_tools(server, source, TOOLS)
```

Complex tools with custom parameter mapping or multiple parameters should still use the standard one-file-per-tool pattern above.

**With auth scopes:**

```python
server.register_tool(
    name="admin_tool",
    description="Admin-only operation.",
    input_schema={...},
    handler=_handle_admin,
    auth_scopes=["admin"],
)
```

---

## Adding a Resource

Create a new `.py` file in `packages/fss-mcp/src/fss_mcp/extensions/resources/`.

**Template:**

```python
"""My custom resource."""

from __future__ import annotations
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fss_mcp.context import HandlerContext
    from fss_mcp.server import ChassisServer


def register(server: "ChassisServer") -> None:
    """Register this resource with the server."""
    server.register_resource(
        uri="myapp://data/report",
        name="My Report",
        description="Returns the current report data as JSON.",
        mime_type="application/json",
        handler=_handle_report,
    )


async def _handle_report(uri: str, context: "HandlerContext") -> str:
    """Handle reads of myapp://data/report.

    Args:
        uri: The resource URI being requested.
        context: Handler context.

    Returns:
        Resource content as a string.
    """
    data = {"status": "ok", "count": 42}
    return json.dumps(data)
```

**URI conventions:**
- Use a custom scheme: `myapp://`, `template://`, etc.
- Keep URIs stable — clients may cache them.
- Return content as a string (JSON, plain text, etc.).

**With auth scopes:**

```python
server.register_resource(
    uri="myapp://data/admin-report",
    handler=_handle_admin_report,
    name="Admin Report",
    auth_scopes=["admin"],
)
```

---

## Adding a Prompt

Create a new `.py` file in `packages/fss-mcp/src/fss_mcp/extensions/prompts/`.

**Template:**

```python
"""My custom prompt."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fss_mcp.context import HandlerContext
    from fss_mcp.server import ChassisServer

_ARGUMENTS = [
    {"name": "topic", "description": "The topic to discuss.", "required": True},
    {"name": "style", "description": "Communication style.", "required": False},
]


def register(server: "ChassisServer") -> None:
    """Register this prompt with the server."""
    server.register_prompt(
        name="my_prompt",
        description="Generates a prompt for discussing a topic.",
        arguments=_ARGUMENTS,
        handler=_handle_my_prompt,
    )


async def _handle_my_prompt(
    arguments: dict[str, Any], context: "HandlerContext"
) -> list[dict[str, str]]:
    """Handle prompt generation.

    Args:
        arguments: Prompt arguments.
        context: Handler context.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    topic = arguments["topic"]
    style = arguments.get("style", "professional")
    return [
        {
            "role": "user",
            "content": f"Please discuss {topic} in a {style} tone.",
        }
    ]
```

**Rules:**
- Return a list of `{"role": "user"|"assistant", "content": "..."}` dicts.
- Arguments are sanitized and checked by the middleware before the handler is called (I/O limits, auth, rate limiting, sanitization).

**With auth scopes:**

```python
server.register_prompt(
    name="admin_prompt",
    handler=_handle_admin_prompt,
    description="Admin-only prompt.",
    auth_scopes=["admin"],
)
```

---

## Shared State (Init Hook)

If your extensions need shared state — a database connection, an API client, a knowledge base — use the init hook. This runs after middleware setup but before extension discovery, so all extensions can access the state you set up.

**Step 1:** Create an init module (e.g., `packages/fss-mcp/src/fss_mcp/extensions/my_init.py`):

```python
"""Init hook — sets up shared state for extensions."""

import logging

logger = logging.getLogger(__name__)


def on_init(server):
    """Called before extension discovery. Attach shared state to server."""
    from my_library import MyClient

    server._my_client = MyClient(server._config.app.get("api_url", ""))
    logger.info("MyClient initialized")
```

**Step 2:** Set `init_module` in config:

```toml
[extensions]
auto_discover = true
init_module = "fss_mcp.extensions.my_init"
```

**Step 3:** Access the shared state in your tool extensions:

```python
def register(server):
    client = server._my_client
    if client is None:
        return

    async def _handle(arguments, context):
        return client.do_something(arguments["query"])

    server.register_tool(name="my_tool", ..., handler=_handle)
```

**Rules:**
- The init module must define an `on_init(server)` function.
- Errors in the hook are logged but do not crash the server.
- The hook runs before extension discovery, so extensions can rely on state it sets up.
- Use `server._config.app` to access fork-specific configuration values.

---

## Fork-Specific Configuration

The `[app]` TOML section is a pass-through for your fork's configuration. The template does not validate or interpret it — you define its structure. Access it in your init hook and extensions via `server._config.app`:

```toml
[app]
database_url = "postgresql://localhost/mydb"
api_key_env = "MY_API_KEY"
cache_ttl = 300
```

```python
# In your init hook:
def on_init(server):
    db_url = server._config.app.get("database_url", "")
    server._db = connect(db_url)
```

Nested tables are supported:

```toml
[app]
name = "my-fork"

[app.database]
host = "localhost"
port = 5432
```

Accessed as `server._config.app["database"]["host"]`.

---

## Configuration

Edit `config/default.toml` to configure your server:

```toml
[server]
name = "my-server"            # Change this
version = "1.0.0"
transport = "stdio"           # Only stdio is supported currently
log_level = "INFO"

[security]
profile = "strict"            # strict | moderate | permissive

[security.rate_limits]
enabled = true
global_rpm = 60
per_tool_rpm = 30
burst_size = 10

[security.io_limits]
max_request_size = 1048576    # 1 MB
max_response_size = 5242880   # 5 MB

[security.input_validation]
enabled = true
max_string_length = 10000
max_array_length = 100
max_object_depth = 10

[security.input_sanitization]
enabled = true
level = "strict"              # strict | moderate | permissive

[security.auth]
enabled = false
provider = "none"

# Error verbosity: when false, error responses hide internal details
# (validation limits, schema paths) and include only the error code
# and correlation ID. Default depends on profile (strict=false, others=true).
# detailed_errors = false

[extensions]
auto_discover = true
# init_module = "fss_mcp.extensions.my_init"  # Optional init hook

[diagnostics]
health_check_enabled = true
include_config_summary = false
```

### Security Profiles

| Profile | Rate Limit | I/O Limits | Sanitization | Error Detail |
|---------|-----------|------------|--------------|--------------|
| `strict` | 60 rpm global, 30 rpm/tool | 1 MB req, 5 MB resp | Full (path traversal, shell metachars, control chars) | Generic |
| `moderate` | 120 rpm global, 60 rpm/tool | 5 MB req, 20 MB resp | Path traversal + control chars | Detailed |
| `permissive` | disabled | 50 MB req/resp | Null bytes only | Detailed |

**Sanitization details:**
- Path traversal removal handles stacked payloads (`....//` → caught) and URL-encoded evasion (`%2e%2e%2f` → decoded and caught)
- Shell metacharacter removal (strict only) strips `` ;|&$`\!#()[]{}<>"'~\n ``
- Schemas that set `"additionalProperties": false` will reject unexpected keys during validation

**Warning — strict sanitization and string content:** The shell metacharacter
set includes characters commonly found in JSON, code, and natural language:
`{`, `}`, `[`, `]`, `"`, `'`, and `\`. Sanitization operates on parsed Python
objects, so the JSON-RPC message structure is not affected. However, **string
values** within tool arguments that contain these characters will be modified. For example:
- `She said "hello"` becomes `She said hello`
- `{"key": "value"}` (as a string parameter) loses its structural characters
- Code snippets lose braces, brackets, and quotes

If your tools accept free-form text, code, embedded JSON, or any content that may contain these characters, use `moderate` (strips path traversal and control characters but preserves shell metacharacters) or `permissive` (strips only null bytes). Evaluate which sanitization level is appropriate for your tools' expected input.

### Environment Variable Overrides

```bash
MCP_LOG_LEVEL=DEBUG           # Override log level
MCP_SECURITY_PROFILE=moderate # Override security profile
MCP_RATE_LIMIT_ENABLED=false  # Disable rate limiting
MCP_CHASSIS_CONFIG=/path/to/config.toml  # Config file path
MCP_AUTH_TOKEN=secret123      # For future HTTP transport only
```

**Note:** Token auth (`provider = "token"`) is not supported on the stdio transport. The server will refuse to start if token auth is enabled on stdio. Over stdio, the OS provides process-level isolation. Token auth will be enforced when HTTP transport is implemented.

### Secrets and `.env` Files

The server does not auto-load `.env` files. Use the `--env-file` flag to explicitly load environment variables (e.g., API keys) from a file before the server starts:

```bash
python -m fss_mcp --config config/default.toml --env-file .env
```

The `.env` file uses `KEY=VALUE` format (one per line). Blank lines and `#` comments are skipped. Values may be optionally quoted. An `export ` prefix is accepted. Variables already set in the environment are **not** overwritten, so system-level env vars take precedence.

```bash
# .env example
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL="postgresql://localhost/mydb"
export FEATURE_FLAG=true
```

Access these in your init hook via `os.environ`:

```python
def on_init(server):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
```

For MCP client configurations (e.g., Claude Desktop), include `--env-file` in the args:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "fss_mcp", "--config", "/path/to/config.toml", "--env-file", "/path/to/.env"]
    }
  }
}
```

---

## Testing Your Extensions

Write unit tests in `tests/unit/` using pytest:

```python
import pytest
from fss_mcp.config import ServerConfig
from fss_mcp.context import HandlerContext
from fss_mcp.server import ChassisServer
from fss_mcp.extensions.tools.my_tool import register

@pytest.fixture()
def server() -> ChassisServer:
    config = ServerConfig()  # Uses defaults
    s = ChassisServer(config)
    return s

@pytest.mark.asyncio
async def test_my_tool(server: ChassisServer) -> None:
    register(server)
    ctx = HandlerContext(
        request_id="test",
        correlation_id="test",
        server_config=server._config,
    )
    handler = server._tools["my_tool_name"]["handler"]
    result = await handler({"param1": "hello"}, ctx)
    assert result == "Result: hello + 0"
```

Run tests:
```bash
make test          # All tests
make test-unit     # Unit tests only
make test-integration  # Integration tests only
```

---

## Running with Docker

```bash
# Build the image
docker build -t my-mcp-server .

# Run over stdio (pipe stdin/stdout)
docker run -i my-mcp-server

# With a custom config
docker run -i -v /path/to/config.toml:/app/config/default.toml my-mcp-server
```

---

## Adding Dependencies

### PyPI packages

Add packages to the `dependencies` list in `pyproject.toml`:

```toml
[project]
dependencies = [
    "mcp>=1.2.0,<2.0",
    "pydantic>=2.0",       # Add your dependencies here
    "httpx>=0.27",
]
```

Then reinstall: `pip install -e ".[dev]"`

### Local libraries (not on PyPI)

If your fork depends on a local Python package (e.g., a shared library in a sibling directory), you need it importable in two contexts:

**For tests (pytest):** Add the parent directory to `pythonpath` in
`pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src", "/path/to/library/parent"]
```

**For the server runtime:** Create a `.pth` file in the venv so Python can find the package at runtime:

```bash
echo "/path/to/library/parent" > .venv/lib/python3.12/site-packages/mylib.pth
```

Verify both contexts work:

```bash
# Runtime
python -c "from my_library import MyClass; print('OK')"

# Tests
python -m pytest tests/ -q
```

**For Docker:** Copy or mount the library into the container and add its path to `PYTHONPATH` in the Dockerfile:

```dockerfile
COPY /path/to/library /app/lib
ENV PYTHONPATH="/app/lib:${PYTHONPATH}"
```

---

## Running with Claude Desktop or Other MCP Clients

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "fss_mcp", "--config", "/path/to/config.toml", "--env-file", "/path/to/.env"]
    }
  }
}
```

Omit `--env-file` if your fork does not need secrets. See [Secrets and `.env` Files](#secrets-and-env-files) for details.

---

## Handler Context API

The `HandlerContext` object passed to all handlers provides:

```python
context.request_id        # str: unique ID for this request
context.correlation_id    # str: correlation ID for log tracing
context.server_config     # ServerConfig: current server configuration

# Logging methods (support %-style format args)
await context.log_debug("debug message")
await context.log_info("processing %s", name)
await context.log_warning("retry %d of %d", attempt, max_retries)
await context.log_error("failed to load %s: %s", path, err)

# Progress reporting (logs a percentage)
await context.report_progress(current=50, total=100, message="halfway done")
```

---

## Error Handling in Handlers

Raise exceptions freely — the server catches them and returns proper MCP error responses:

```python
async def _handle_my_tool(arguments: dict, context: HandlerContext) -> str:
    if not arguments.get("param1"):
        raise ValueError("param1 is required")
    # ... do work
    return "success"
```

For structured errors with codes, use the chassis error types:

```python
from fss_mcp.errors import ValidationError

async def _handle_my_tool(arguments: dict, context: HandlerContext) -> str:
    value = arguments["value"]
    if len(value) > 100:
        raise ValidationError("Value too long", code="VALUE_TOO_LONG")
    return value
```

---

## Security Considerations

1. **Never access `os.environ` directly** in extension handlers — use `context.server_config`.
2. **Never use `subprocess` with `shell=True`** — this is blocked by the security reviewer.
3. **Never use `eval()` or `exec()`** on any user-provided data.
4. **Never use `pickle.loads()`** on untrusted data.
5. **All string inputs are sanitized** before reaching your handler (based on profile). This applies to tool arguments and prompt arguments. Sanitization runs before validation in the pipeline. If two distinct argument keys collide after sanitization (e.g., `"path../a"` and `"patha"`), the request is rejected with a `KEY_COLLISION` error.
6. **Rate limiting is enforced** globally and per-tool/resource/prompt before your handler runs.
7. **Log to stderr only** — stdout is reserved for MCP JSON-RPC messages.
8. **Extension files must not be world-writable** — the auto-discovery system rejects files with unsafe permissions. All extension imports are logged at WARNING level.
9. **Error responses hide internal details by default** in strict mode. Set `detailed_errors = true` under `[security]` if you need verbose errors during development.

---

## Updating Your Fork from the Template

When the template receives bug fixes, security patches, or new features, you can pull those changes into your fork. The template is designed so that forks add new files (extensions, init hooks, config) rather than modifying template files — this means updates should merge cleanly.

### Setup (one time)

Add the template repository as a git remote in your fork:

```bash
cd my-fork/
git remote add template https://github.com/.../fss-mcp-server.git
git fetch template
```

### Pulling updates

```bash
# Fetch latest template changes
git fetch template

# Create a branch for the update
git checkout -b template-update

# Merge template changes into your fork
git merge template/main

# Run tests to verify everything works
make test

# If all tests pass, merge into your main branch
git checkout main
git merge template-update
```

### What to check after merging

1. **Run the full test suite** — `make test`. Your extension tests and the template's structural tests should all pass.
2. **Check your init hook** — if the template changed `ChassisServer.__init__` or the init hook mechanism, verify your `on_init()` function still works.
3. **Check your config** — if the template added new config sections or changed defaults, verify your `config/default.toml` is still correct.
4. **Review the changelog** — check what changed in the template to understand if any of your extensions need updating.

### Avoiding merge conflicts

The template's architecture is designed to minimize conflicts. If you follow these guidelines, `git merge` should apply cleanly:

- **Do not modify template source files** (`server.py`, `config.py`, `context.py`, `middleware/`, `security/`, `transport/`, `extensions/__init__.py`). Use init hooks and the `[app]` config section instead.
- **Keep your extensions in the standard directories** (`extensions/tools/`, `extensions/resources/`, `extensions/prompts/`). The template does not ship files in these directories that would conflict with yours (the example extensions are clearly named and meant to be deleted).
- **Keep your tests in separate files** from the template's tests. Do not modify `test_server.py`, `test_pipeline.py`, etc. — add your own test files.
- **Keep fork-specific config in `[app]`** rather than adding new TOML sections that might collide with future template sections.

If you do need to modify a template file (rare), document what you changed and why. This makes future merges easier to resolve.

### If merge conflicts occur

Conflicts typically mean the template changed a file that your fork also modified. To resolve:

1. Look at what the template changed and why (read the commit message).
2. Look at what your fork changed and why.
3. Keep both changes if they do not overlap, or adapt your change to work with the new template code.
4. Run `make test` after resolving to verify correctness.

If you find yourself frequently conflicting on a specific template file, consider whether your change could be restructured to use an init hook, the `[app]` config, or a separate extension file instead.

---

## Disabling Example Extensions

To remove the bundled example extensions, delete:
- `packages/fss-mcp/src/fss_mcp/extensions/tools/example_tool.py`
- `packages/fss-mcp/src/fss_mcp/extensions/resources/example_resource.py`
- `packages/fss-mcp/src/fss_mcp/extensions/prompts/example_prompt.py`
- `tests/integration/test_stdio_examples.py` (optional — auto-skips when examples are absent)

The auto-discovery system will automatically skip missing files.
Integration tests in `test_stdio_examples.py` auto-skip when the example extensions are absent, so deleting the test file is optional but keeps the test suite clean.
