# Architecture — MCP Chassis Server

## Overview

The template wraps the MCP Python SDK behind a custom framework layer that provides security middleware, configuration management, extension auto-discovery, and transport abstraction. This isolation means:

1. Fork developers interact with **our** decorator API, not the SDK directly.
2. Security middleware is enforced **before** any use-case code runs.
3. Swapping SDK versions (v1.x → v2.0) requires changes only in the wrapper layer.

```
┌─────────────────────────────────────────────────────┐
│                  MCP Client (stdio)                  │
└──────────────────────┬──────────────────────────────┘
                       │ JSON-RPC over stdin/stdout
┌──────────────────────▼──────────────────────────────┐
│               Transport Layer (stdio)                │
│  Future: SSE / StreamableHTTP stubs                  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Security Middleware Pipeline             │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ │
│  │I/O Limit│→│   Auth   │→│  Rate   │→│  Input   │ │
│  │ Check   │ │  Check   │ │ Limiter │ │Sanitize/ │ │
│  │         │ │          │ │         │ │ Validate │ │
│  └─────────┘ └──────────┘ └─────────┘ └──────────┘ │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Chassis Server Core                     │
│  ┌────────────────┐ ┌───────────────┐ ┌───────────┐ │
│  │ Tool Registry  │ │Resource Regist│ │Prompt Reg │ │
│  │ (extensions/)  │ │ (extensions/) │ │(extensions│ │
│  └───────┬────────┘ └──────┬────────┘ └─────┬─────┘ │
│          │                 │                │       │
│  ┌───────▼─────────────────▼────────────────▼─────┐ │
│  │          Extension Auto-Discovery              │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────┐ ┌───────────────┐ ┌───────────┐ │
│  │  Config Loader │ │  Diagnostics  │ │  Logging  │ │
│  └────────────────┘ └───────────────┘ └───────────┘ │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              MCP Python SDK (v1.x)                   │
│              Low-level Server class                  │
└─────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Entry Point — `src/mcp_chassis/__main__.py`

**Purpose:** CLI entry point. Parses arguments, loads config, creates and runs the server.

```python
# Allows: python -m mcp_chassis
# Allows: python -m mcp_chassis --config /path/to/config.toml
# Allows: python -m mcp_chassis --env-file /path/to/.env
# Allows: python -m mcp_chassis --version
# Allows: MCP_CHASSIS_CONFIG=/path/to/config.toml python -m mcp_chassis
```

**Responsibilities:**
- Parse CLI arguments (stdlib `argparse`)
- Load `.env` file if `--env-file` was provided (does not override existing env vars)
- Load configuration
- Initialize logging to stderr
- Create `ChassisServer` instance
- Run the server (blocking)
- Handle SIGTERM/SIGINT for graceful shutdown

### 2. Server Core — `src/mcp_chassis/server.py`

**Purpose:** The central orchestrator. Creates the MCP SDK `Server`, wires up middleware, discovers extensions, and runs the event loop.

**Key Class: `ChassisServer`**

```python
class ChassisServer:
    def __init__(self, config: ServerConfig) -> None:
        """Initialize with validated configuration."""

    def register_tool(self, name, description, input_schema, handler, *,
                      rate_limit_override=None, auth_scopes=None) -> None:
        """Register a tool with metadata for middleware."""

    def register_resource(self, uri, handler, *, name=None,
                          description=None, mime_type=None,
                          auth_scopes=None) -> None:
        """Register a resource with optional auth scopes."""

    def register_prompt(self, name, handler, *, description=None,
                        arguments=None, auth_scopes=None) -> None:
        """Register a prompt with optional auth scopes."""

    async def run(self) -> None:
        """Start the server on the configured transport."""

    async def shutdown(self) -> None:
        """Graceful shutdown."""
```

**Internal Flow for `call_tool`:**
1. Receive `CallToolRequestParams` from SDK
2. Run through middleware pipeline (I/O limits → auth → rate limit → sanitize → validate)
3. If all pass, invoke the registered handler
4. Catch exceptions from handler, convert to MCP error responses
5. Run response through I/O limit check
6. Return `CallToolResult`

**Internal Flow for `read_resource`:**
1. Run through middleware pipeline (auth → rate limit)
2. If all pass, invoke the registered handler
3. Run response through I/O limit check
4. Return `ReadResourceContents`

**Internal Flow for `get_prompt`:**
1. Run through middleware pipeline (I/O limits → auth → rate limit → sanitize)
2. If all pass, invoke the registered handler with sanitized arguments
3. Return `GetPromptResult`

**Server Initialization Order:**
1. Create middleware pipeline
2. Run init hook (`config.extensions.init_module`) — forks use this to set up shared state (DB connections, API clients, etc.) before extensions load
3. Register SDK handlers
4. Register health check (if enabled)
5. Auto-discover extensions (if enabled)

**Design Decision:** We use the SDK's low-level `Server` class and register our own `on_list_tools`, `on_call_tool`, etc. handlers that delegate through the middleware pipeline to extension-registered handlers. This gives us full control over the request lifecycle.

### 3. Configuration — `src/mcp_chassis/config.py`

**Purpose:** Load, validate, and provide typed access to all configuration.

**File:** `config/default.toml` (TOML format, loaded via stdlib `tomllib`)

**Config Structure:**
```toml
[server]
name = "mcp-chassis-server"
version = "0.1.0"
transport = "stdio"         # "stdio" | "sse" | "streamable-http" (only stdio implemented)
log_level = "INFO"          # DEBUG | INFO | WARNING | ERROR

[security]
profile = "strict"          # "strict" | "moderate" | "permissive"
# detailed_errors = false   # Default depends on profile (strict=false, others=true)

[security.rate_limits]
enabled = true
global_rpm = 60             # Requests per minute, global
per_tool_rpm = 30           # Requests per minute, per tool
burst_size = 10             # Token bucket burst allowance

[security.io_limits]
max_request_size = 1048576      # 1 MB
max_response_size = 5242880     # 5 MB

[security.input_validation]
enabled = true
max_string_length = 10000
max_array_length = 100
max_object_depth = 10

[security.input_sanitization]
enabled = true
level = "strict"            # "strict" | "moderate" | "permissive"

[security.auth]
enabled = false             # Token auth not supported on stdio transport
provider = "none"           # "none" | "token" (token requires HTTP transport)
# token = ""               # Set via env: MCP_AUTH_TOKEN (HTTP only)

[extensions]
auto_discover = true
# init_module = "mcp_chassis.extensions.my_init"  # Optional init hook

[diagnostics]
health_check_enabled = true
include_config_summary = false

# [app]
# my_setting = "value"      # Fork-specific configuration pass-through
```

**Key Class: `ServerConfig`**

```python
@dataclass(frozen=True)
class ServerConfig:
    server: ServerSettings
    security: SecurityConfig
    extensions: ExtensionSettings
    diagnostics: DiagnosticSettings

    @classmethod
    def load(cls, config_path: Path | None = None) -> "ServerConfig":
        """Load from TOML file with env var overrides."""

    @classmethod
    def from_profile(cls, profile: str) -> "ServerConfig":
        """Create config from a named security profile."""
```

**Environment Variable Overrides:**
- `MCP_CHASSIS_CONFIG` — path to config file
- `MCP_LOG_LEVEL` — override log level
- `MCP_SECURITY_PROFILE` — override security profile
- `MCP_AUTH_TOKEN` — auth token (for future HTTP transport only; not used on stdio)
- `MCP_RATE_LIMIT_ENABLED` — toggle rate limiting
- All env vars prefixed with `MCP_` and follow the TOML path in UPPER_SNAKE_CASE.

### 4. Security Module — `src/mcp_chassis/security/`

#### 4a. Security Profiles — `profiles.py`

**Purpose:** Define named security configurations.

```python
PROFILES = {
    "strict": {
        "rate_limits": {"enabled": True, "global_rpm": 60, "per_tool_rpm": 30},
        "io_limits": {"max_request_size": 1_048_576, "max_response_size": 5_242_880},
        "input_sanitization": {"level": "strict", ...},
        "input_validation": {"enabled": True, "max_string_length": 10_000, ...},
    },
    "moderate": {
        "rate_limits": {"enabled": True, "global_rpm": 120, "per_tool_rpm": 60},
        "io_limits": {"max_request_size": 5_242_880, "max_response_size": 20_971_520},
        "input_sanitization": {"level": "moderate", ...},
        ...
    },
    "permissive": {
        "rate_limits": {"enabled": False},
        "io_limits": {"max_request_size": 52_428_800, "max_response_size": 52_428_800},
        "input_sanitization": {"level": "permissive", ...},
        ...
    },
}
```

#### 4b. Input Validation — `validation.py`

**Purpose:** Validate tool arguments against JSON schema and depth/size constraints.

**Key Function:**
```python
def validate_tool_input(arguments: dict, schema: dict, limits: ValidationLimits) -> ValidationResult:
    """Validate arguments against schema and structural limits.

    Uses stdlib json for basic type checking. Does NOT use jsonschema library.
    Validates: required fields, types (str/int/float/bool/list/dict/null),
    string length, array length, nesting depth, enum constraints,
    and additionalProperties rejection.
    """
```

**Rationale for no `jsonschema` dependency:** The MCP SDK generates simple schemas from type hints. We validate the core structural constraints (types, required fields, limits) using stdlib. The SDK itself does schema validation for complex cases.

#### 4c. Input Sanitization — `sanitization.py`

**Purpose:** Clean potentially dangerous content from string inputs.

**Key Function:**
```python
def sanitize_input(value: Any, level: str) -> Any:
    """Recursively sanitize input values.

    Strict: strip control chars, path traversal, shell metacharacters,
            null bytes, unicode exploits.
    Moderate: strip control chars, null bytes, path traversal.
    Permissive: strip null bytes only.
    """
```

**Sanitization Rules (Strict):**
- Remove ASCII control characters (0x00-0x1F except \t \n \r)
- Remove null bytes
- Normalize path separators, reject `../` and `..\\`
- Escape/strip shell metacharacters: `` ; | & $ ` \ ! # ( ) { } [ ] < > ``
- Normalize Unicode (NFC) to prevent homograph attacks
- Strip Unicode control characters (categories Cc, Cf except common whitespace)

#### 4d. Rate Limiter — `rate_limiter.py`

**Purpose:** Token-bucket rate limiting, in-memory.

**Key Class:**
```python
class RateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize with global and per-tool limits."""

    def check(self, tool_name: str) -> RateLimitResult:
        """Check if request is allowed. Returns allow/deny with retry-after."""

    def reset(self) -> None:
        """Reset all buckets (for testing)."""
```

**Algorithm:** Token bucket with configurable refill rate and burst size. Separate buckets for global and per-tool. Uses `time.monotonic()` for clock.

#### 4e. I/O Limits — `io_limits.py`

**Purpose:** Enforce maximum sizes on request and response payloads.

**Key Functions:**
```python
def check_request_size(data: bytes | str, max_size: int) -> None:
    """Raise IOLimitError if request exceeds max_size."""

def check_response_size(data: bytes | str, max_size: int) -> None:
    """Raise IOLimitError if response exceeds max_size."""
```

#### 4f. Auth Framework — `auth.py`

**Purpose:** Pluggable authentication and authorization interface.

```python
class AuthProvider(ABC):
    """Base class for auth providers."""

    @abstractmethod
    async def authenticate(self, request_context: dict) -> AuthResult:
        """Authenticate a request. Returns identity or rejection."""

    @abstractmethod
    async def authorize(self, identity: AuthIdentity, tool_name: str,
                       scopes: list[str]) -> bool:
        """Check if identity is authorized for this tool."""

class NoAuthProvider(AuthProvider):
    """Default: no authentication (for stdio/trusted environments)."""

    async def authenticate(self, request_context: dict) -> AuthResult:
        return AuthResult(authenticated=True, identity=AuthIdentity(id="local"))

    async def authorize(self, identity, tool_name, scopes) -> bool:
        return True

class TokenAuthProvider(AuthProvider):
    """Simple token-based auth. Token provided via env var."""
    # For future HTTP transport use
```

**Per-tool Authorization:**
- Tools can declare required scopes at registration time.
- The auth provider checks the caller's scopes against required scopes.
- In stdio/no-auth mode, all scopes are granted.

### 5. Middleware Pipeline — `src/mcp_chassis/middleware/pipeline.py`

**Purpose:** Chain security checks in a defined order.

```python
class MiddlewarePipeline:
    def __init__(self, config: SecurityConfig) -> None:
        """Initialize all middleware from config."""

    async def process_tool_request(self, tool_name: str, arguments: dict,
                                    schema: dict, request_context: dict) -> MiddlewareResult:
        """Run all middleware checks on an incoming tool call.

        Order: I/O limits → Auth → Rate limit → Sanitize → Validate
        Returns: sanitized arguments or error.
        """

    def check_response_size(self, response_data: str) -> None:
        """Check response payload size."""
```

**Error Handling:**
Each middleware step returns either a pass-through or an error. Errors are converted to MCP `CallToolResult` with `is_error=True` and a structured error message including a correlation ID.

### 6. Extension System — `src/mcp_chassis/extensions/`

**Purpose:** Allow forks to add tools, resources, and prompts by dropping modules into designated directories.

#### Auto-Discovery — `src/mcp_chassis/extensions/__init__.py`

```python
def discover_extensions(server: "ChassisServer", base_package: str) -> None:
    """Scan extensions/{tools,resources,prompts}/ and register all decorated items."""
```

**Discovery Mechanism:**
1. Scan `extensions/tools/`, `extensions/resources/`, `extensions/prompts/` for `.py` files (not `__init__.py`).
2. Import each module.
3. Look for module-level `register(server)` function in each module.
4. Call `register(server)` which uses `server.register_tool()` etc.

**Why `register()` function instead of decorators?** Decorators require the server instance at import time, creating circular dependencies. A `register(server)` function is called after the server is created, keeping modules clean and testable.

#### Example Tool — `src/mcp_chassis/extensions/tools/example_tool.py`

```python
"""Example tool demonstrating the extension pattern."""

def register(server: "ChassisServer") -> None:
    server.register_tool(
        name="example_echo",
        description="Echoes back the input. Demonstrates the tool extension pattern.",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to echo"}
            },
            "required": ["message"],
        },
        handler=_handle_echo,
    )

async def _handle_echo(arguments: dict, context: "HandlerContext") -> str:
    return arguments["message"]
```

#### Example Resource — `src/mcp_chassis/extensions/resources/example_resource.py`

```python
"""Example resource demonstrating the resource extension pattern."""

def register(server: "ChassisServer") -> None:
    server.register_resource(
        uri="template://example/info",
        name="Example Info",
        description="Returns static information about this server instance.",
        mime_type="application/json",
        handler=_handle_info,
    )

async def _handle_info(uri: str, context: "HandlerContext") -> str:
    import json
    return json.dumps({"chassis": "mcp-chassis-server", "status": "running"})
```

#### Example Prompt — `src/mcp_chassis/extensions/prompts/example_prompt.py`

```python
"""Example prompt demonstrating the prompt extension pattern."""

def register(server: "ChassisServer") -> None:
    server.register_prompt(
        name="example_greeting",
        description="Generates a greeting prompt.",
        arguments=[
            {"name": "name", "description": "Name to greet", "required": True}
        ],
        handler=_handle_greeting,
    )

async def _handle_greeting(arguments: dict, context: "HandlerContext") -> list:
    name = arguments.get("name", "World")
    return [{"role": "user", "content": f"Please greet {name} warmly."}]
```

### 7. Diagnostics — `src/mcp_chassis/diagnostics/health.py`

**Purpose:** Built-in health check tool registered by default.

**Tool Name:** `__health_check`

**Returns:**
```json
{
    "server_name": "mcp-chassis-server",
    "server_version": "0.1.0",
    "chassis_version": "1.0.0",
    "python_version": "3.11.x",
    "uptime_seconds": 123.4,
    "tools_loaded": ["example_echo", "__health_check"],
    "resources_loaded": ["template://example/info"],
    "prompts_loaded": ["example_greeting"],
    "security_profile": "strict",
    "config_summary": {
        "transport": "stdio",
        "rate_limiting": true,
        "auth_enabled": false,
        "log_level": "INFO"
    }
}
```

### 8. Error Handling — `src/mcp_chassis/errors.py`

**Purpose:** Unified error types with correlation IDs.

```python
import uuid

class ChassisError(Exception):
    """Base error with correlation ID."""
    def __init__(self, message: str, code: str):
        self.correlation_id = uuid.uuid4().hex[:12]
        self.code = code
        super().__init__(message)

class ValidationError(ChassisError): ...
class SanitizationError(ChassisError): ...
class RateLimitError(ChassisError): ...
class IOLimitError(ChassisError): ...
class AuthError(ChassisError): ...
class ExtensionError(ChassisError): ...
```

Notable error codes:
- `SanitizationError` with code `KEY_COLLISION` — raised when two distinct dict keys collide after sanitization (e.g., `"path../a"` and `"patha"` both become `"patha"`). This protects against silent data loss from key merging.

All errors are caught in the server core and converted to structured error responses with the correlation ID included for log tracing. Tools return `CallToolResult(isError=True)`. Resources and prompts raise `McpError`.

### 9. Logging — `src/mcp_chassis/logging_config.py`

**Purpose:** Configure Python's `logging` module for structured JSON output to stderr.

```python
def configure_logging(level: str) -> None:
    """Configure logging to stderr with JSON format.

    Format: {"timestamp": "...", "level": "...", "logger": "...",
             "message": "...", "correlation_id": "..."}

    Uses stdlib logging with a custom JSONFormatter. No dependencies.
    """
```

**Key constraint:** All logging goes to stderr. stdout is reserved exclusively for MCP JSON-RPC messages.

### 10. Transport Abstraction — `src/mcp_chassis/transport/`

#### Base Interface — `base.py`

```python
class TransportBase(ABC):
    """Abstract base for MCP transports."""

    @abstractmethod
    async def start(self, server: "ChassisServer") -> None:
        """Start the transport and begin serving."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Graceful shutdown."""
```

#### Stdio Implementation — `stdio.py`

```python
class StdioTransport(TransportBase):
    """Stdio transport using MCP SDK's stdio_server."""

    async def start(self, server: "ChassisServer") -> None:
        """Run server over stdio."""

    async def shutdown(self) -> None:
        """Signal shutdown."""
```

#### Future Stubs — `http_stub.py`

```python
class SSETransport(TransportBase):
    """Stub for future SSE transport."""

    async def start(self, server):
        raise NotImplementedError(
            "SSE transport is not yet implemented. "
            "See MIGRATION_NOTES.md for planned HTTP transport support."
        )

class StreamableHTTPTransport(TransportBase):
    """Stub for future Streamable HTTP transport."""
    # Same pattern
```

### 11. Handler Context — `src/mcp_chassis/context.py`

**Purpose:** Provide a clean context object to extension handlers, abstracting away SDK internals.

```python
@dataclass
class HandlerContext:
    """Context passed to tool/resource/prompt handlers."""

    request_id: str
    correlation_id: str
    server_config: ServerConfig
    lifespan_state: Any  # User-defined lifespan state

    async def log_debug(self, message: str, *args: object) -> None: ...
    async def log_info(self, message: str, *args: object) -> None: ...
    async def log_warning(self, message: str, *args: object) -> None: ...
    async def log_error(self, message: str, *args: object) -> None: ...
    async def report_progress(self, progress: float, total: float,
                               message: str = "") -> None: ...
```

**Rationale:** Extension code should not import from `mcp.*` directly. Our `HandlerContext` provides the needed capabilities and will be adapted when migrating to SDK v2.0.

---

## Data Flow

### Tool Call Flow (detailed)

```
Client → stdin → JSON-RPC parse
                     │
                     ▼
          ┌─ I/O Limit Check ─┐
          │  (request size)    │
          │  FAIL → error resp │
          └────────┬───────────┘
                   ▼
          ┌─ Auth Check ───────┐
          │  (if enabled)      │
          │  FAIL → error resp │
          └────────┬───────────┘
                   ▼
          ┌─ Rate Limit Check ─┐
          │  (global + tool)   │
          │  FAIL → error resp │
          └────────┬───────────┘
                   ▼
          ┌─ Input Sanitization┐
          │  (clean strings)   │
          └────────┬───────────┘
                   ▼
          ┌─ Input Validation ─┐
          │  (schema + limits) │
          │  FAIL → error resp │
          └────────┬───────────┘
                   ▼
          ┌─ Handler Dispatch ─┐
          │  (extension code)  │
          │  ERROR → error resp│
          └────────┬───────────┘
                   ▼
          ┌─ I/O Limit Check ─┐
          │  (response size)   │
          │  FAIL → error resp │
          └────────┬───────────┘
                   ▼
          ┌─ JSON-RPC response ┐
          └──── → stdout ──────┘
```

### Server Startup Flow

```
1. Parse CLI args (--config, --env-file, --version)
2. Load .env file if --env-file provided
3. Load config (TOML file → env var overrides → validate)
4. Configure logging (JSON to stderr)
5. Create ChassisServer(config)
   a. Initialize SecurityMiddlewarePipeline
   b. Run init hook (if configured)
   c. Register SDK handlers
   d. Register built-in health check tool
   e. Discover and register extensions
6. Install signal handlers (SIGTERM, SIGINT)
7. Create transport (StdioTransport)
8. Run transport → server.run() → SDK server.run()
9. On shutdown signal: graceful shutdown
```

---

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | MCP SDK requirement, `tomllib` in stdlib |
| MCP SDK | `mcp<2.0` (latest v1.x) | Brief requirement: no v2.0 pre-alpha |
| Config format | TOML (`tomllib`) | Stdlib, no dependency, Python ecosystem standard |
| Logging | stdlib `logging` | No dependency, flexible, well-known |
| Async runtime | `anyio` (via MCP SDK) | Already a transitive dependency |
| JSON schema validation | Custom (stdlib) | Avoids `jsonschema` dependency |
| Rate limiting | Custom token bucket | Simple, stdlib-only, in-memory |
| Testing | `pytest` + `pytest-asyncio` | De facto standard, minimal |
| Type checking | `mypy` | Strict type checking for template quality |
| Linting | `ruff` | Fast, comprehensive, single tool |

---

## Error Handling Strategy

1. **Extension handler errors:** Caught by server core, wrapped in `CallToolResult(is_error=True)` with correlation ID. Logged at ERROR level.

2. **Middleware errors (validation, rate limit, etc.):** Returned as `CallToolResult(is_error=True)` with specific error code and correlation ID. Logged at WARNING level.

3. **SDK/transport errors:** Logged at ERROR level. If recoverable (single request failure), continue serving. If fatal (broken pipe), trigger shutdown.

4. **Startup errors (bad config, missing extension):** Logged at CRITICAL level, exit with non-zero code. Errors are human-readable.

5. **Never crash on a single request.** All request-handling code is wrapped in try/except.

---

## File Manifest

```
src/mcp_chassis/
├── __init__.py                          # Package init, version
├── __main__.py                          # CLI entry point
├── server.py                            # ChassisServer core
├── config.py                            # Configuration loading
├── context.py                           # HandlerContext for extensions
├── errors.py                            # Error types with correlation IDs
├── logging_config.py                    # JSON logging to stderr
├── security/
│   ├── __init__.py
│   ├── profiles.py                      # Security profile definitions
│   ├── validation.py                    # Input validation
│   ├── sanitization.py                  # Input sanitization
│   ├── rate_limiter.py                  # Token bucket rate limiter
│   ├── io_limits.py                     # Request/response size limits
│   └── auth.py                          # Auth provider interface + impls
├── middleware/
│   ├── __init__.py
│   └── pipeline.py                      # Security middleware pipeline
├── transport/
│   ├── __init__.py
│   ├── base.py                          # Transport abstract base
│   ├── stdio.py                         # Stdio transport implementation
│   └── http_stub.py                     # Stubs for future HTTP transports
├── diagnostics/
│   ├── __init__.py
│   └── health.py                        # Health check tool
└── extensions/
    ├── __init__.py                      # Auto-discovery logic
    ├── batch.py                         # Batch registration helper
    ├── tools/
    │   ├── __init__.py
    │   └── example_tool.py              # Example tool
    ├── resources/
    │   ├── __init__.py
    │   └── example_resource.py          # Example resource
    └── prompts/
        ├── __init__.py
        └── example_prompt.py            # Example prompt

config/
└── default.toml                         # Default configuration

tests/
├── conftest.py                          # Shared fixtures
├── unit/
│   ├── test_config.py
│   ├── test_validation.py
│   ├── test_sanitization.py
│   ├── test_rate_limiter.py
│   ├── test_io_limits.py
│   ├── test_auth.py
│   ├── test_pipeline.py
│   ├── test_health.py
│   ├── test_errors.py
│   └── test_server.py
└── integration/
    └── test_stdio_integration.py

pyproject.toml                           # Project metadata, dependencies
Makefile                                 # Standard targets
Dockerfile                               # Container build
FORK_GUIDE.md                            # How to fork and extend
TROUBLESHOOTING.md                       # Common issues
MIGRATION_NOTES.md                       # SDK v2.0 migration notes
```

---

## SDK v2.0 Migration Strategy

**Current approach (v1.x):**
- Use low-level `Server` class with `on_*` handler functions
- Our `ChassisServer` wraps the SDK server and manages registrations
- Extensions register via `server.register_tool()` etc.

**Migration to v2.0 (when stable):**
1. Replace internal `Server` with `MCPServer`
2. Our `register_tool()` internally calls `MCPServer.tool()` instead of building tool lists manually
3. `HandlerContext` wraps `MCPServer.Context` instead of `ServerRequestContext`
4. Transport abstraction maps to `MCPServer.run(transport="...")`
5. Auth integrates with SDK's `AuthSettings`
6. **Extension API (`register()` function) does NOT change** — forks need no modification

**Impact to forks on v2.0 migration:** None, if they use only `server.register_tool/resource/prompt()` and `HandlerContext`. The migration is internal to the template.

---

## Threat Model Summary

Security review of the architecture identified these items relevant to our template (SDK-internal issues are excluded):

### Mitigations Built Into Architecture

| Threat | Mitigation |
|--------|-----------|
| **Stdio message size DoS** (SDK has no stdin size limit) | Our `StdioTransport` reads stdin in fixed-size chunks (8 KB), assembling lines up to a 1 MB limit. Lines exceeding the limit are discarded before they can exhaust memory. This is a streaming bound — memory usage is capped regardless of input size. |
| **Input injection** (shell, path traversal, control chars) | Sanitization middleware applied before handler dispatch |
| **Rate-based DoS** | Token bucket rate limiter in middleware pipeline |
| **Large payload DoS** | I/O limits enforced at transport layer |
| **Log injection** (untrusted data in log messages) | Our JSON formatter sanitizes control characters; never use f-strings with untrusted content in log calls |
| **Config injection via .env** | No auto-loading of `.env` files; config requires explicit path |
| **Extension code injection** | Extensions loaded only from designated directories; errors in extensions are caught and logged, never crash the server |

### Items for Future HTTP Transport

When HTTP transport is implemented, the following MUST be addressed:
1. DNS rebinding protection (enable by default, validate Host header)
2. Session store limits (cap concurrent sessions, enforce idle timeout)
3. Per-session request rate limiting
4. SSRF prevention (domain allowlist, block private IPs, disable redirect following)
5. PKCE with constant-time comparison (`hmac.compare_digest`)
6. Client registration rate limiting

### Health Check Information Disclosure

The `__health_check` tool exposes server metadata. Mitigation: config summary excludes secrets (auth tokens, API keys). In `strict` profile, `include_config_summary` defaults to `false`.
