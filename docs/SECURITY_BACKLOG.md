# Security Backlog

Items logged during Phase 3 hardening. CRITICAL and HIGH items have been resolved.
MEDIUM items below have been resolved or dispositioned. LOW items are documented for future consideration.

---

## Resolved (Phase 3)

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| S-001 | HIGH | Exception messages leak internals to clients (server.py) | Generic "internal server error" message returned; full details logged server-side |
| S-002 | HIGH | Dict keys not sanitized in sanitize_input (sanitization.py) | Keys now sanitized alongside values |
| S-003 | HIGH | No recursion depth guard in sanitize_input (sanitization.py) | Added _MAX_SANITIZE_DEPTH=50 with SanitizationError on exceed |
| S-004 | HIGH | Bare assert in rate_limiter.py (disabled by python -O) | Replaced with explicit if/raise RuntimeError |
| S-005 | MEDIUM | Health check discloses full Python build string (health.py) | Truncated to major.minor.micro only |
| S-006 | MEDIUM | Signal handler race — loop.stop() before shutdown completes (__main__.py) | Replaced with asyncio.Event + TaskGroup pattern |
| S-007 | MEDIUM | Extension module name not validated before import (extensions/__init__.py) | Added regex validation, skip invalid names |
| S-008 | MEDIUM | Example extensions use f-string with user input in logs | Replaced with %-style formatting |
| S-009 | MEDIUM | config.py _deep_copy is only 2-level deep | Replaced with copy.deepcopy |
| S-010 | BLOCKING | from_profile() ignores named profile values (config.py) | Now seeds from profiles.get_profile() before applying overrides |
| S-011 | BLOCKING | Prompt handler KeyError outside try/except (server.py) | Moved list comprehension inside try block |
| S-012 | MEDIUM | Path traversal regex misses bare trailing ".." | Extended regex pattern |
| S-013 | LOW | Dockerfile copies src/ redundantly | Removed COPY src/ from runtime stage |

## Open — LOW (for future consideration)

| ID | Severity | Finding | Disposition |
|----|----------|---------|-------------|
| S-014 | LOW | Server name/version in config accept unbounded-length strings | Accept risk — config is developer-controlled, not user input |
| S-015 | LOW | JSON Schema enum/pattern constraints not enforced by validator | Enum now enforced; pattern remains unsupported (ReDoS risk). Documented in TROUBLESHOOTING.md |
| S-016 | LOW | mcp dependency uses range (>=1.2.0,<2.0) not exact pin | Acceptable for template; forks should generate lock files |
| S-017 | LOW | Auth disabled in "strict" profile for stdio | Correct for stdio; added code comments on all three profiles warning about HTTP transport |

## Future HTTP Transport Security Requirements

When HTTP transport is implemented, these MUST be addressed:
1. DNS rebinding protection (enable by default, validate Host header)
2. Session store limits (cap concurrent sessions, enforce idle timeout)
3. Per-session request rate limiting
4. SSRF prevention (domain allowlist, block private IPs, disable redirect following)
5. PKCE with constant-time comparison (hmac.compare_digest)
6. Client registration rate limiting
7. Scope-filtered capability listings — `tools/list`, `resources/list`, and `prompts/list` currently return all registered capabilities regardless of the caller's auth scopes. On stdio this is acceptable (single caller, OS-level isolation), but over HTTP, unauthorized clients can enumerate protected tool names, descriptions, schemas, and resource URIs. The list handlers must filter results based on the caller's authenticated identity and scopes before returning.
8. Per-identity scope assignment — `TokenAuthProvider.authenticate()` (`auth.py:188`) grants wildcard scope (`frozenset(["*"])`) to every authenticated user, and `authorize()` (`auth.py:207`) short-circuits to `True` when the wildcard is present. This means `auth_scopes` on tools, resources, and prompts are never enforced — all authenticated users can access everything. When HTTP transport is added, the auth system must support assigning specific scopes per identity (e.g., via token claims, role mappings, or a scope configuration file) so that `auth_scopes` restrictions are meaningful.
