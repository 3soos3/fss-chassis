# Migration Notes — MCP SDK v2.0

This document explains what MCP Python SDK v2.0 changes, how this template's
architecture is designed to absorb those changes, and what fork developers
need to do when v2.0 becomes stable.

---

## Background

The MCP Python SDK is currently at v1.x (this template was developed against
v1.2+). The SDK maintainers have signaled an upcoming v2.0 that will
introduce breaking changes to the low-level server API.

**This template pins to `mcp>=1.2.0,<2.0` in `pyproject.toml` to prevent
accidental breakage when v2.0 is released.**

---

## What Is Changing in v2.0

Based on publicly available information and SDK commit history up to the
template's knowledge cutoff:

### 1. High-Level Server API Replaces Low-Level `Server`

v1.x:
```python
from mcp.server.lowlevel.server import Server
```

v2.0 introduces a new high-level class (name may vary — check SDK release notes)
that provides decorator-based tool/resource/prompt registration and built-in
lifespan support. The low-level `Server` class may be deprecated or removed.

### 2. `ServerRequestContext` Becomes Typed Context

In v1.x, `request_ctx` is a `ContextVar[RequestContext]`. v2.0 provides a typed
`MCPContext` object with cleaner attribute access to request metadata and progress
reporting.

### 3. Transport API Refactored

v1.x transports are ad-hoc; v2.0 standardizes `run(transport="stdio")`,
`run(transport="sse")`, etc. The `stdio_server()` context manager is replaced
by a transport parameter on the server's `run()` method.

### 4. `SessionMessage` / Message Wrapping

Internal message wrapping types have changed. v1.x code that directly
constructs `SessionMessage` objects will need updating.

### 5. `mcp.types` Type Model Updates

Some types in `mcp.types` may be renamed or have field renames. For example,
`CallToolResult.isError` field casing may change to match JSON-RPC conventions.

---

## How This Template Is Protected

The template was architected specifically to minimize migration impact for
fork developers. Here is how each architectural layer maps to the change:

### Extension API: Zero Impact

**Why:** Extension code (in `extensions/tools/`, `extensions/resources/`,
`extensions/prompts/`) only interacts with:
- `server.register_tool()`, `server.register_resource()`, `server.register_prompt()`
- `HandlerContext` methods (`log_debug`, `log_info`, etc.)

Neither of these touches the SDK directly. When the template migrates to v2.0,
the extension API stays identical. **Fork developers with custom extensions
will not need to change any extension code.**

### HandlerContext: Internal Adaptation Only

`HandlerContext` is the template's isolation layer. In v1.x, it wraps
`request_ctx.get()`. In v2.0, it will wrap `MCPContext`. This change is
internal to `context.py`. Extension handlers remain unchanged.

### ChassisServer Core: One-Time Refactor

`server.py` will need updating when migrating to v2.0:

1. Replace `from mcp.server.lowlevel.server import Server` with the v2.0 import.
2. Replace manually registered `@sdk_server.list_tools()` etc. with the new API.
3. Update `register_tool()` to internally use the v2.0 decorator API.
4. Adapt `run_on_streams()` to the new transport API.

This refactor is isolated to `server.py` and `transport/stdio.py`.

### Middleware Pipeline: No Impact

The middleware pipeline (`middleware/pipeline.py`) operates on plain Python
dicts and our custom error types. It has no SDK imports.

### Transport Layer: Minor Updates

`transport/stdio.py` wraps the SDK's stdio machinery. The custom size-bounding
logic (D-006) may be simplified in v2.0 if the SDK gains native size limits.
The `SSETransport` and `StreamableHTTPTransport` stubs will become real
implementations using the v2.0 HTTP transport.

---

## Migration Checklist (for Template Maintainers)

When MCP SDK v2.0 is declared stable, perform these steps:

- [ ] Update `pyproject.toml`: change `mcp>=1.2.0,<2.0` to `mcp>=2.0,<3.0`
- [ ] Read the official v2.0 migration guide and release notes
- [ ] Update `src/mcp_chassis/server.py`:
  - [ ] Replace low-level `Server` import with v2.0 equivalent
  - [ ] Adapt `_register_sdk_handlers()` to new decorator API
  - [ ] Update `run_on_streams()` if the transport API changed
- [ ] Update `src/mcp_chassis/transport/stdio.py`:
  - [ ] Adapt to new `stdio_server()` interface (or remove if SDK handles it)
  - [ ] Verify size-bounding protection still works
- [ ] Update `src/mcp_chassis/context.py`:
  - [ ] Adapt `_make_context()` in `server.py` to wrap the new context type
  - [ ] Verify all `HandlerContext` methods still work
- [ ] Update `src/mcp_chassis/transport/http_stub.py`:
  - [ ] Implement real SSE and Streamable HTTP transports using v2.0 API
- [ ] Run full test suite: `make test`
- [ ] Run security review on changed modules
- [ ] Update this file to reflect the completed migration

---

## What Fork Developers Need to Do

**For forks that only add custom extensions (the typical case):**

Nothing. Update the template to the post-migration version and run `make test`.
Your extension code is not affected.

**For forks that modified `server.py` or transport files:**

Review the changes in the updated template's `server.py` and apply equivalent
changes to your fork's modified version.

**For forks that import from `mcp.*` directly:**

This is against the template's guidelines (see `FORK_GUIDE.md`). You will need
to update these imports manually following the v2.0 migration guide.

---

## Timeline

As of the current template version (0.1.0), MCP SDK v2.0 is not yet stable.
The template pins to v1.x and will release a new version when v2.0 migration
is complete. Watch the template repository for a `v2.0-migration` release.

To check whether v2.0 has been released:
```bash
pip index versions mcp
```

Do not upgrade to v2.0 without following this migration guide.
