# fss-chassis

[![Gate](https://github.com/3soos3/fss-chassis/actions/workflows/gate.yml/badge.svg)](https://github.com/3soos3/fss-chassis/actions/workflows/gate.yml)
[![CodeQL](https://github.com/3soos3/fss-chassis/actions/workflows/codeql.yml/badge.svg)](https://github.com/3soos3/fss-chassis/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/3soos3/fss-chassis/badge)](https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Python monorepo providing two packages that implement the Forensic Software Standard (FSS) for MCP servers.

| Package | PyPI | Implements | MCP dependency |
|---|---|---|---|
| `fss-core` | `pip install fss-core` | FSS-0004/FSS-0005 — protocol primitives | None |
| `fss-mcp` | `pip install fss-mcp` | FSS-0010 — MCP server chassis | `mcp>=1.2.0` |

`fss-core` is usable by any FSS-compliant service regardless of transport. `fss-mcp` is the MCP-specific layer built on top of it.

---

## What they provide

### fss-core

- **Provenance records** — assembles the `_provenance` block attached to every tool response (transaction ID, CAI digests, KB version, tool/server version, FSS conformance identifier)
- **Content-Addressed Identifiers (CAI)** — SHA-256/384/512 hashing with optional RFC 8785 JCS canonicalisation (FSS-0005)
- **Ed25519 signing** — `data_signature` and `provenance_signature` for L2/L3 deployments
- **Authentication providers** — `NoAuthProvider`, `TokenAuthProvider`, `ApiKeyProvider`, `OAuthJWTProvider`
- **FIT verification** — 11-step Forensic Investigation Token procedure (FSS-0007)
- **FSS context variables** — async-safe per-request context vars for investigation ID, analyst identity, client identity, FIT claims

### fss-mcp

- **`ChassisServer`** — wires the MCP SDK, middleware pipeline, and extension discovery
- **Security middleware** — I/O limits → auth → rate limiting → sanitisation → validation, applied before every handler
- **Extension auto-discovery** — `discovery_packages` config key points the scanner at any installed package; `init_module` runs a hook before discovery
- **Three security profiles** — `strict` / `moderate` / `permissive` with per-field overrides
- **Transports** — stdio (default) and HTTP/SSE

---

## Development setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/3soos3/fss-chassis
cd fss-chassis
uv sync --extra otel   # installs both packages editable + all dev/otel deps
```

```bash
make test        # pytest on both packages
make lint        # ruff check
make typecheck   # mypy packages/
make audit       # pip-audit on both packages
```

---

## Building an MCP server on fss-mcp

### 1. Declare the dependency

```toml
# pyproject.toml
[project]
dependencies = ["fss-mcp[http,auth,otel]>=0.3"]
```

### 2. Write an init hook

```python
# your_package/init.py
def on_init(server) -> None:
    import your_package
    server._server_version = your_package.__version__
    server._kb = load_your_data()
```

### 3. Write tool extensions

```python
# your_package/tools.py
def register(server) -> None:
    import your_package
    async def _handle(arguments, context):
        return {"result": server._kb.query(arguments["q"])}

    server.register_tool(
        name="my_tool",
        description="...",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
        handler=_handle,
        tool_version=your_package.__version__,
    )
```

### 4. Point config at your package

```toml
# config/default.toml
[extensions]
init_module = "your_package.init"
discovery_packages = ["your_package.tools"]
```

### 5. Run

```bash
python -m fss_mcp --config config/default.toml
```

---

## FSS conformance

Every tool response includes a `_provenance` block. The `assessed_under` field is constructed automatically from the installed package versions:

```
FSS-0010v{fss_mcp.__version__}@FSS-0009v{fss_core.__version__}L{FSS_LEVEL}
```

Set `FSS_LEVEL` to the conformance level you have self-assessed against FSS-0009 Appendix A (default: `1`). This is the only operator-facing FSS configuration required.

| Level | Key additions over previous |
|---|---|
| L1 | Provenance record in every response, tool manifest fields, CAI integrity |
| L2 | Ed25519 data_signature, JCS canonicalisation required, extended attribution |
| L3 | FIT verification, provenance_signature, evidentiary status, image_digest |
| L4 | SBOM, development standards (FSS-0008), KATs, dependency pinning |

---

## Security middleware

Every request passes through the pipeline in this order:

```
I/O limits → Auth → Rate limit → Sanitise → Validate
```

| Profile | Rate limit | I/O limits | Sanitisation |
|---|---|---|---|
| `strict` | 60 rpm global / 30 rpm per tool | 1 MB req / 5 MB resp | Path traversal, shell metacharacters, control chars |
| `moderate` | 120 rpm global / 60 rpm per tool | 5 MB req / 20 MB resp | Path traversal, control chars |
| `permissive` | Disabled | 50 MB req/resp | Null bytes only |

---

## Security

Vulnerability reports should be submitted via [GitHub Security Advisories](https://github.com/3soos3/fss-chassis/security/advisories/new) — do not use public issues for security matters.

Automated security controls on this repository:

| Control | Tool | Cadence |
|---|---|---|
| Dependency vulnerability scan | [pip-audit](https://github.com/pypa/pip-audit) | Every PR + weekly |
| Static analysis | [CodeQL](https://github.com/3soos3/fss-chassis/security/code-scanning) | Every PR + weekly |
| Supply-chain scorecard | [OpenSSF Scorecard](https://securityscorecards.dev/viewer/?uri=github.com/3soos3/fss-chassis) | Every push to main |
| Dependency licence review | [dependency-review-action](https://github.com/3soos3/fss-chassis/actions/workflows/dependency-review.yml) | Every PR |

---

## Documentation

| Document | Contents |
|---|---|
| [docs/FORK_GUIDE.md](docs/FORK_GUIDE.md) | Step-by-step guide to building a server on fss-mcp |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Component design and request lifecycle |
| [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Testing approach and manual test instructions |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [docs/CHASSIS_RECOMMENDATIONS.md](docs/CHASSIS_RECOMMENDATIONS.md) | Recommended patterns for production deployments |
