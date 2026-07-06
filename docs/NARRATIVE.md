# How the MCP Chassis Server Works

This document walks through how the MCP Chassis Server is built, how its components work together, and why it is designed the way it is. It is written for someone with a technical background who wants to understand the system without needing to read the source code.

---

## What This Server Does

The Model Context Protocol (MCP) is a standard for connecting AI language models (like Claude) to external data sources and tools. An MCP server is a program that listens for requests from an AI client, executes operations on its behalf, and returns results. Think of it like a web API, but specifically designed for AI assistants.

This template provides a ready-made MCP server with built-in security, configuration management, and an extension system. Rather than building an MCP server from scratch, a developer forks this template and adds their own tools, resources, and prompts as extension files. The template handles all the protocol mechanics, security enforcement, logging, and error handling automatically.

---

## The Big Picture

When the server is running, a request flows through several layers before reaching the code that actually does work:

```
AI Client (e.g., Claude Desktop)
     |
     v
Transport Layer (reads/writes stdin and stdout)
     |
     v
MCP Protocol Handler (parses JSON-RPC messages)
     |
     v
Security Middleware (checks size, auth, rate, sanitization, validation)
     |
     v
Extension Handler (the fork's business logic)
     |
     v
Response (back through the same layers in reverse)
```

Each layer has a specific job, and none of them know the details of the layers above or below. This separation is intentional — it means a fork developer only needs to think about the extension handler layer. Everything else is handled by the template.

---

## Starting the Server

### The Entry Point

When you run `python -m fss_mcp`, execution begins in the CLI module (`__main__.py`). This module does five things in order:

1. **Parse command-line arguments** — the user can specify a config file path (`--config`), a log level (`--log-level`), and an environment file (`--env-file`).
2. **Load environment file** — if `--env-file` was provided, the server reads `KEY=VALUE` pairs from the file and adds them to the process environment. Variables already set in the environment are not overwritten, so system-level settings take precedence. This is how forks supply secrets (API keys, database credentials) without hardcoding them in config files.
3. **Set up logging** — all log output is configured to go to stderr as structured JSON. This is critical because stdout is reserved exclusively for MCP protocol messages. If anything other than valid JSON-RPC appeared on stdout, the AI client would break.
4. **Load configuration** — the server reads its settings from a TOML file, then applies any environment variable overrides.
5. **Create and start the server** — this is where the real work begins.

### Signal Handling

The CLI also installs signal handlers for graceful shutdown. When the server receives SIGTERM or SIGINT (e.g., from Ctrl+C or a container orchestrator), it initiates a clean shutdown sequence: it tells the server to stop accepting new requests, closes stdin to unblock any waiting I/O, and gives the system 5 seconds to finish before force-exiting. A second signal during shutdown forces an immediate exit — this prevents the server from hanging indefinitely.

---

## Configuration

### How Configuration Works

The configuration system uses a layered approach where later sources override earlier ones:

1. **Built-in defaults** — every setting has a sensible default value hardcoded in the source.
2. **TOML config file** — a human-readable configuration file (by default at `config/default.toml`) that overrides the defaults.
3. **Environment variables** — specific `MCP_` prefixed variables that override the TOML values. This is useful in containerized deployments where you cannot easily modify files.

All configuration values are stored in frozen (immutable) data structures. Once the server starts, the configuration cannot change. This prevents accidental modification during request processing and eliminates an entire class of concurrency bugs.

### Security Profiles

Rather than requiring a fork developer to configure dozens of individual security settings, the template provides three named profiles:

- **Strict** (the default) — designed for production. Rate limiting is on, I/O limits are tight (1 MB requests, 5 MB responses), full input sanitization is active, and error messages hide internal details from clients.
- **Moderate** — designed for development. Rate limits are more generous, I/O limits are higher, sanitization is less aggressive, and error messages include full details for debugging.
- **Permissive** — designed for testing only. Rate limiting is disabled, I/O limits are very high (50 MB), and only null bytes are stripped from inputs. This profile should never be used in production.

A fork can use a profile as a starting point and override individual settings. For example, you might use the strict profile but increase the response size limit for a tool that returns large datasets.

### Fork-Specific Configuration

The template includes a generic `[app]` section in the TOML config that passes through to fork code as a plain dictionary. The template does not interpret or validate this section — it simply makes it available. A fork uses this for its own settings (database URLs, API keys, feature flags) without modifying the template's configuration code.

---

## The Server Core

### ChassisServer

The `ChassisServer` class is the central coordinator. When it is created, it does the following in order:

1. **Creates the middleware pipeline** — this is the security enforcement layer (described in detail below).
2. **Runs the init hook** — if the fork has configured an init module, it is imported and its `on_init(server)` function is called. This is where a fork sets up shared resources like database connections or knowledge base instances that multiple extensions will need.
3. **Registers protocol handlers** — these are the low-level MCP handlers that receive parsed protocol messages and route them to the right dispatch method.
4. **Registers the health check** — a built-in diagnostic tool that reports server status.
5. **Discovers and loads extensions** — scans the extension directories and registers all tools, resources, and prompts it finds.

### Three Types of MCP Capabilities

The MCP protocol defines three types of capabilities a server can offer:

- **Tools** — operations the AI can invoke with arguments (like calling a function). Example: "search the database for records matching this query."
- **Resources** — named data the AI can read (like reading a file). Example: "read the server's current status."
- **Prompts** — pre-built conversation templates the AI can use. Example: "generate a greeting for this person."

Each type has its own registration method, dispatch path, and middleware configuration. Tools get the most thorough security treatment (all five middleware stages), while resources get a lighter treatment (no input arguments to sanitize or validate).

### The Dispatch Methods

When an MCP request arrives, the protocol handler calls the appropriate dispatch method (`_dispatch_tool`, `_dispatch_resource`, or `_dispatch_prompt`). Each dispatch method follows the same general pattern:

1. Create a handler context with a unique request ID and correlation ID.
2. Look up the registered handler by name (return an error if not found).
3. Run the request through the middleware pipeline.
4. If middleware passes, call the handler with the sanitized arguments and context.
5. Serialize the response to JSON and check its size.
6. Return the result to the protocol layer.

If anything goes wrong at any step — middleware rejection, handler exception, serialization failure — the dispatch method catches it and returns a structured error response. The AI client never sees a raw Python traceback.

---

## The Middleware Pipeline

The middleware pipeline is the security backbone of the server. Every request passes through a series of checks before reaching the handler. If any check fails, the request is rejected immediately and subsequent checks are skipped.

### The Five Stages

The stages run in this order, and the order matters:

**Stage 1: I/O Limits** — The request arguments are serialized to JSON and their byte size is measured. If the payload exceeds the configured maximum (e.g., 1 MB in strict mode), the request is rejected before any further processing. This is the cheapest check and runs first to prevent expensive downstream work on oversized payloads.

**Stage 2: Authentication** — The request is checked against the configured auth provider. In the default stdio configuration, authentication is disabled (the operating system's process isolation provides security). For future HTTP transport, a token-based auth provider is available that uses constant-time comparison to prevent timing attacks.

**Stage 3: Rate Limiting** — The server uses a token bucket algorithm with two buckets per request: a global bucket (shared across all tools) and a per-tool bucket. A request is allowed only if both buckets have tokens available. Tokens refill at a configured rate (e.g., 1 per second for 60 RPM). The server checks both buckets before consuming from either — this prevents a denied per-tool request from wasting a global token.

**Stage 4: Input Sanitization** — String values in the request arguments are cleaned according to the configured level. In strict mode, this removes path traversal sequences (`../`), shell metacharacters (`;`, `|`, `&`, etc.), control characters, and Unicode tricks. In moderate mode, shell metacharacters are preserved but path traversal is still removed. In permissive mode, only null bytes are stripped. Sanitization also checks for key collisions — if two dictionary keys become identical after cleaning (e.g., `"path../a"` and `"patha"` both become `"patha"`), the request is rejected to prevent silent data loss.

**Important caveat about strict sanitization:** The shell metacharacter set includes characters that are also used in JSON and natural language: `{`, `}`, `[`, `]`, `"`, `'`, and `\`. Sanitization operates on the *parsed* Python objects, not on the raw JSON-RPC message — so the structural JSON of the request itself is not affected. However, if a tool accepts a string parameter that *contains* JSON, code, or quoted natural language, strict sanitization will damage it. For example, a string value like `She said "hello"` becomes `She said hello`, and an embedded JSON string like `{"key": "value"}` loses its structural characters entirely. Tools that accept free-form text, code snippets, or embedded structured data should use **moderate** or **permissive** sanitization. Fork developers should evaluate which sanitization level is appropriate for each tool's expected input.

**Stage 5: Input Validation** — The sanitized arguments are validated against the tool's JSON schema. This checks types (is this field really a string?), required fields (is the mandatory `id` parameter present?), and structural limits (is this string longer than 10,000 characters? Is this array larger than 100 elements? Is this object nested more than 10 levels deep?). The validator reports all errors at once rather than stopping at the first one.

### Why This Order?

The ordering is deliberate:

- **I/O limits first** because there is no point authenticating, rate-limiting, or sanitizing a 100 MB payload that will be rejected anyway.
- **Auth before rate limiting** because an unauthenticated request should not consume rate limit tokens.
- **Rate limiting before sanitization** because sanitization is more expensive and should not run on requests that will be rate-limited.
- **Sanitization before validation** because validators see the cleaned data. If sanitization removed characters that a validator checks for, the validator would get confused. By sanitizing first, the schema validation operates on the data the handler will actually receive.

### Different Pipelines for Different Types

Not all three capability types need the same pipeline:

| Stage | Tools | Resources | Prompts |
|-------|-------|-----------|---------|
| I/O Limits | Yes (on arguments) | No (no arguments) | Yes (on arguments) |
| Authentication | Yes | Yes | Yes |
| Rate Limiting | Yes | Yes | Yes |
| Sanitization | Yes | No (no arguments) | Yes |
| Validation | Yes (against schema) | No (no schema) | No (no schema) |
| Response Size | Yes | Yes | Yes |

---

## The Transport Layer

### What a Transport Does

The transport layer handles the raw I/O between the server and the MCP client. It converts bytes on a wire (or pipe) into structured messages and back. The template defines a transport interface (`TransportBase`) that any transport implementation must follow, with two methods: `start()` (begin serving) and `shutdown()` (stop serving).

### The Stdio Transport

The only production transport currently implemented is stdio — the server reads JSON-RPC messages from stdin and writes responses to stdout. This is the standard MCP transport for local servers launched by AI clients like Claude Desktop.

The stdio transport includes a critical safety feature: bounded line reading. Standard Python `readline()` buffers the entire line in memory before returning it. If a malicious or buggy client sent a single line without a newline that was, say, 10 GB long, the server would try to allocate 10 GB of memory and crash. The template's reader avoids this by reading stdin in fixed 8 KB chunks and tracking how many bytes have accumulated for the current line. If a line exceeds 1 MB, the excess bytes are discarded and an error is logged. The server stays alive and continues processing subsequent requests.

This 1 MB transport limit is independent of the middleware's I/O limits. The transport limit is about keeping the process alive; the middleware limit is about what content the security policy accepts. They serve different purposes and are configured separately.

---

## Extensions

### How Extensions Work

Extensions are the fork developer's primary interface for adding functionality. An extension is a Python file placed in one of three directories:

- `extensions/tools/` — for tools (operations the AI can call)
- `extensions/resources/` — for resources (data the AI can read)
- `extensions/prompts/` — for prompts (conversation templates)

Each extension file must define a `register(server)` function. When the server starts, the auto-discovery system scans these directories, imports each Python file, and calls its `register()` function. The function receives the server instance and uses it to register capabilities:

```python
def register(server):
    server.register_tool(
        name="my_tool",
        description="Does something useful.",
        input_schema={...},
        handler=my_handler_function,
    )
```

The handler function receives the validated, sanitized arguments and a context object. It returns a result (a string or JSON-serializable value), and the template takes care of everything else — wrapping it in the MCP protocol format, checking the response size, and sending it back to the client.

Extensions should never use `print()` or configure their own loggers. Instead, they call `await context.log_info("message")` (or `log_debug`, `log_warning`, `log_error`). These methods automatically write to the same JSON-formatted stderr stream that the rest of the server uses, with the same correlation ID for the current request. They also send the log message to the AI client as an MCP notification, so the client can see what the server is doing. The extension does not need to configure any logging infrastructure — the template sets it all up at startup, and the context methods route everything to the right place.

### The Init Hook

If a fork needs shared state that multiple extensions will access — a database connection, an API client, a loaded dataset — it uses the init hook mechanism. The fork creates a module with an `on_init(server)` function and configures it in the TOML config:

```toml
[extensions]
init_module = "fss_mcp.extensions.my_init"
```

The init hook runs after the middleware pipeline is set up but before extensions are discovered. This means extensions can rely on the shared state being available when their `register()` function is called. If the init hook fails, the error is logged but the server continues — extensions that need the shared state will simply skip their registration (they check for it and return early if it is not present).

### Batch Registration

When a fork has many similar tools — for example, a knowledge base with "get item by ID" tools for several item types — writing one file per tool creates a lot of repetitive code. The template provides a batch registration helper that lets you declare multiple tools as a data structure in a single file:

```python
TOOLS = [
    {"name": "get_item", "method": "get_item", "param": "item_id", "not_found_check": True, ...},
    {"name": "list_items", "method": "list_all", ...},
]

def register(server):
    register_simple_tools(server, my_data_source, TOOLS)
```

The helper generates the handler functions, input schemas, and registrations automatically. Complex tools with custom logic still use the standard one-file-per-tool pattern.

### Extension Security

The auto-discovery system includes a security check: on Unix systems, it verifies that extension files are not world-writable before importing them. Since importing a Python file executes all module-level code with the server's full privileges, a world-writable extension file would be a backdoor — any local user could inject code into the server. Files that fail this check are skipped with a warning. On Windows, where Unix file permissions are not meaningful, this check is skipped entirely.

---

## The Handler Context

Every handler — whether for a tool, resource, or prompt — receives a `HandlerContext` object. This object provides:

- **Request and correlation IDs** for tracing a request through logs.
- **Access to the server configuration** so the handler can read settings without importing config modules directly.
- **Logging methods** (`log_debug`, `log_info`, `log_warning`, `log_error`) that automatically include the correlation ID and send MCP log notifications to the AI client.

The context deliberately hides the MCP SDK's internal objects. Extensions never import from `mcp.*` directly. This means when the SDK upgrades (even with breaking changes), only the template's internal code needs updating — extension code remains unchanged. This is the key architectural decision that makes the template upgrade-safe for forks.

---

## Error Handling

### Error Types

The template defines a hierarchy of error types, all inheriting from `FSSCoreError`:

- `ValidationError` — input does not match the expected schema
- `SanitizationError` — input sanitization encountered an unrecoverable issue (like a key collision)
- `RateLimitError` — the request exceeds the configured rate limit (includes a retry-after hint)
- `IOLimitError` — the request or response payload is too large
- `AuthError` — authentication or authorization failed
- `ExtensionError` — an extension failed to load or register

Every error automatically generates a 12-character correlation ID. This ID appears in the error response sent to the client and in the server's log output. An operator investigating a problem can search for this ID to find all log entries related to a specific failed request.

### Error Verbosity

The template supports two error verbosity modes controlled by the `detailed_errors` configuration:

- **Detailed mode** (on by default in moderate and permissive profiles) — error responses include the full error message, including specifics like "string length 15,000 exceeds limit 10,000." This is useful during development.
- **Generic mode** (on by default in strict profile) — error responses include only the error code and correlation ID, like "VALIDATION_ERROR: Request failed [correlation_id=a1b2c3d4e5f6]." Internal details are hidden from the client. This prevents information leakage in production.

In both modes, the full error details are always written to the server's log output. The verbosity setting only controls what the client sees.

---

## Logging

All log output goes to stderr as single-line JSON objects. Each log entry includes:

- A UTC timestamp in ISO 8601 format
- The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- The logger name (which module produced the log)
- The formatted message (with control characters stripped to prevent log injection)
- The correlation ID (if the log was produced during request processing)
- The full exception traceback (if an exception was being logged)

The JSON format ensures that log entries can be parsed by log aggregation tools (Elasticsearch, Splunk, CloudWatch, etc.) without custom parsing rules. The single-line constraint prevents multi-line log entries from being split across multiple records in these tools. Control characters (including newlines) are stripped from the message before JSON serialization — this prevents a malicious input from injecting fake log entries.

Stdout is never used for logging. It is reserved exclusively for MCP JSON-RPC messages. Even a single stray `print()` statement would corrupt the protocol stream and break the connection with the AI client.

---

## The Health Check

The server includes a built-in diagnostic tool called `__health_check`. When called, it returns a JSON report containing:

- Server name, version, and template version
- Python version
- Uptime in seconds
- Lists of all loaded tools, resources, and prompts
- The active security profile
- Optionally, a summary of the server's configuration

This tool is useful for verifying that the server started correctly, that expected extensions loaded, and that the right security profile is active. It is enabled by default and can be disabled in the configuration.

---

## How Forking Works

The template is designed to be forked. A fork is a copy of the template that adds its own extensions and configuration. The template provides several mechanisms to make forking clean:

1. **Init hooks** — forks set up shared state without modifying `server.py`.
2. **The `[app]` config section** — forks add configuration without modifying `config.py`.
3. **Extension auto-discovery** — forks add tools by placing files in the right directory.
4. **The batch helper** — forks with many similar tools avoid boilerplate.
5. **Example extensions** — the template ships with example tools, resources, and prompts that serve as starting points. The integration tests for these examples auto-skip when the examples are deleted, so removing them during forking does not break the test suite.

The result is that a fork can add significant functionality without modifying any of the template's core files. This means the fork can pull in template updates (bug fixes, new features) without merge conflicts.

---

## Design Decisions and Trade-offs

### Why Sanitization Runs Before Validation

This is not obvious and deserves explanation. If validation ran first, a tool schema might require a field to match a certain pattern. But sanitization might remove characters that the pattern expects. By running sanitization first, validation checks the data that the handler will actually receive — not the raw client input that will be modified before the handler sees it.

### Why the Validator Uses No External Libraries

The input validator is built entirely on the Python standard library. It does not use `jsonschema` or any other validation package. This was a deliberate choice: fewer dependencies mean a smaller attack surface, fewer compatibility issues, and no risk of supply-chain attacks through validation library vulnerabilities. The trade-off is that the validator supports only basic JSON schema features (types, required fields, length limits, nesting depth). Advanced features like pattern matching, format specifiers, and schema composition (`oneOf`/`anyOf`) are not supported.

### Why Rate Limiting Uses Two Buckets

A single global rate limit would allow one heavily-used tool to starve all other tools. A per-tool-only limit would allow a client to overwhelm the server by calling many different tools rapidly. The dual-bucket design (global + per-tool) prevents both scenarios: the global bucket limits total server load, while per-tool buckets prevent any single tool from dominating.

### Why the Transport Reads in Chunks

Standard Python I/O reads entire lines into memory. A single line without a newline could be arbitrarily large. The template's chunk-based reader reads 8 KB at a time and tracks how much has accumulated. This bounds memory usage regardless of what the client sends. The 1 MB per-line limit is generous enough for any legitimate MCP message while preventing memory exhaustion from malicious input.

### Why Errors Do Not Crash the Server

Throughout the codebase, errors are caught, logged, and converted to structured responses rather than propagated as crashes. A bad extension does not prevent other extensions from loading. A failed auth check does not crash the middleware. A non-serializable handler return does not crash the dispatch method. This resilience is intentional — in production, a single bad request should never bring down the entire server.

### Why Configuration Is Immutable

Once the server starts, its configuration cannot be changed. This eliminates an entire category of bugs where a request handler accidentally modifies a shared configuration value, affecting subsequent requests. Immutable configuration also makes the server easier to reason about: the behavior at any point during execution is determined entirely by the configuration that was loaded at startup.

---

## Summary

The MCP Chassis Server is a layered system where each layer has a clear responsibility:

| Layer | Responsibility | Key Components |
|-------|---------------|----------------|
| **CLI** | Bootstrap and lifecycle | `__main__.py` |
| **Configuration** | Load, validate, expose settings | `config.py`, `profiles.py`, `default.toml` |
| **Transport** | Raw I/O with safety bounds | `stdio.py`, `base.py` |
| **Protocol** | MCP JSON-RPC handling | MCP SDK integration in `server.py` |
| **Middleware** | Security enforcement | `pipeline.py`, `auth.py`, `rate_limiter.py`, `sanitization.py`, `validation.py`, `io_limits.py` |
| **Extensions** | Fork-specific business logic | `extensions/`, `batch.py`, init hooks |
| **Diagnostics** | Operational visibility | `health.py`, `logging_config.py`, `errors.py` |

The design prioritizes security (defense in depth with five middleware stages), extensibility (init hooks, auto-discovery, batch helpers), and operational transparency (structured JSON logging, correlation IDs, health checks). Fork developers interact primarily with the extension layer and the `[app]` config section, while the template handles everything else.
