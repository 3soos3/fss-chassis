# MCP Chassis Recommendations

Friction points and improvement suggestions identified during the development of the SOLVE-IT MCP Server fork. These are recommendations for the upstream MCP Chassis template project.

Each item includes its resolution status for this fork.

---

## High Impact

### 1. Ship a `run.py` launcher in the template

**Status:** Resolved in this fork (created `run.py`). Recommend for upstream.

**Problem:** MCP clients (Claude Code, Claude Desktop) don't support a `cwd` field in their server configuration. Forks that use relative paths in config (which the template encourages) break when launched by MCP clients because the working directory is unpredictable. Every fork has to independently solve this by creating a launcher script or wrapper.

**Recommendation:** Include a `run.py` at the project root that adds `src/` to `sys.path` and calls `main()`. Forks get it for free, and MCP client configuration becomes a simple `python3 /path/to/run.py --config /path/to/config.toml` everywhere — no shell wrappers, no `pip install` required for basic usage.

### 2. Move example extensions out of the auto-discovery path

**Status:** Resolved in this fork (deleted example files). Recommend for upstream.

**Problem:** The `example_echo`, `example_resource`, and `example_prompt` extensions are in `extensions/tools/`, `extensions/resources/`, and `extensions/prompts/` — the auto-discovery directories. They get registered alongside fork extensions, polluting the tool list. Every fork has to manually delete them. The FORK_GUIDE documents this, but it's easy to forget during development.

**Recommendation:** Move examples to `docs/examples/` (outside the auto-discovery path), or gate them behind a config flag like `[diagnostics] include_examples = false`. Fork developers can copy them back into the discovery path when needed as a starting point.

---

## Medium Impact

### 3. No env var overrides for `[app]` config

**Status:** Resolved in this fork (implemented `MCP_APP_*` env var overrides in init hook).

**Problem:** The chassis supports env var overrides for core settings (`MCP_LOG_LEVEL`, `MCP_SECURITY_PROFILE`, etc.) but not for the `[app]` section. Fork-specific settings can only be changed via TOML files. This limits deployment flexibility — particularly in containerized environments where env vars are the standard configuration mechanism.

**Recommendation:** Either add a generic `[app]` env var override mechanism (e.g., `MCP_APP_*` prefix maps to `[app]` keys with underscore-to-dot conversion), or document a pattern for forks to implement their own env var handling in the init hook. See `solveit_init.py` in this fork for a working implementation.

### 4. Init hook errors are swallowed silently

**Status:** Resolved in this fork (implemented `init_required` config flag with `sys.exit(1)` bypass).

**Problem:** If the init hook raises an exception, the chassis logs it but continues starting the server. For forks where the init hook is essential (e.g., loading a knowledge base that all tools depend on), this results in a server that starts successfully but has no useful tools — with no obvious indication of why unless you check logs.

**Recommendation:** Add a `[extensions] init_required = true` option. When set, an init hook failure causes the server to exit with a clear error message instead of starting in a degraded state. Forks that need their init hook to succeed (which is most forks — the init hook sets up the core resource) can enable this to prevent silently broken servers.

**Fork workaround:** `sys.exit(1)` raises `SystemExit` (a `BaseException`), which bypasses the chassis's `except Exception` handler. See `solveit_init.py` for the implementation.

### 5. Server name defaults to `"fss-mcp-server"`

**Status:** Resolved in this fork (renamed to `"solveit-mcp"`).

**Problem:** The default config ships with `name = "fss-mcp-server"`. Forks that forget to change this have logs, health checks, and MCP server info all identifying as the chassis template rather than their actual project.

**Recommendation:** Use a placeholder name like `"my-mcp-server"` or `"CHANGE-ME"` that's obviously meant to be replaced, and/or add a comment `# TODO: rename this for your fork`.

### 6. The `[app]` config dict is untyped

**Status:** Resolved in this fork (implemented `SolveItAppConfig` dataclass with `from_raw()` validation and typo warnings).

**Problem:** The `[app]` section is passed through as a raw `dict[str, Any]`. Every access requires `.get()` with defaults, there's no validation at load time, typos in config keys silently do nothing, and nested sections (e.g., `[app.search]`) come through as nested dicts that are easy to get wrong.

**Recommendation:** Document a recommended pattern in the FORK_GUIDE for forks to define their own config dataclass and validate the `[app]` section in the init hook. See `SolveItAppConfig` in `solveit_init.py` for a working implementation with nested config support and unrecognized-key warnings.

---

## Low Impact

### 7. `test_stdio_examples.py` doesn't auto-skip after example deletion

**Status:** Resolved in this fork (deleted the test file alongside the examples).

**Problem:** The integration test file for example extensions gets collected by pytest even after the example extensions are deleted. Forks have to manually delete the test file too.

**Recommendation:** Use `pytest.importorskip` or a fixture-level skip that gracefully handles missing examples, so the test file can remain in the template without causing issues for forks that have removed the examples.

### 8. FORK_GUIDE code samples reference deleted examples

**Status:** Resolved in this fork (FORK_GUIDE deleted, content absorbed into README).

**Problem:** The FORK_GUIDE uses `example_echo` in many code samples. After a fork deletes the example extensions (as recommended), these references are stale and potentially confusing for developers reading the guide.

**Recommendation:** Use generic placeholder names in code samples (e.g., `my_tool`, `my_resource`) rather than referencing the shipped examples.

### 9. `batch.py` `not_found_check` only handles `None`

**Status:** Not applicable to this fork (SOLVE-IT KB returns `None` for missing items). Documented for awareness.

**Problem:** The batch helper's `not_found_check` returns a not-found error when the method returns `None`. If a fork's data source returns an empty dict `{}` or other falsy value for not-found, the check doesn't catch it.

**Recommendation:** Either document this limitation clearly, or accept an optional `not_found_value` parameter (defaulting to `None`) so forks can specify what their data source returns for missing items.

**Note:** This is a chassis core file (`extensions/batch.py`) that cannot be modified in forks without violating the "don't modify chassis core" constraint. Forks whose data sources use a different sentinel should use manual registration instead of the batch helper for affected tools.

### 10. Health check tool uses `__` prefix naming

**Status:** Cannot change (chassis core file). Cosmetic only.

**Problem:** The health check tool is named `__health_check`, which looks like a Python dunder convention. This is a cosmetic issue but can cause confusion — it's not a special Python method, it's just a tool name.

**Recommendation:** Consider a naming convention like `chassis_health_check` or `system_health_check` that doesn't borrow Python's dunder semantics.
