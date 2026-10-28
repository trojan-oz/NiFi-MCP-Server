# NiFi MCP Server modernisation — local verification receipt

## Scope

This working branch combines the two existing fork improvements for standalone NiFi authentication and flowfile/provenance diagnostics, then adds safety and reliability guardrails. It does not modify Kevin Talbert's upstream repository.

## Changes in this branch

- **Secret redaction:** normalize key names across camelCase, snake_case, hyphenated and mixed-case variants; cover API keys, authorization, cookies, access/refresh tokens, private keys, keytabs and keystore/truststore passwords.
- **Mutation retry safety:** automatic retries remain for read-only GET calls and only for transient connection/timeouts, HTTP 429 and 5xx responses. POST/PUT/DELETE are not retried automatically because a timeout can occur after the server has applied the mutation.
- **Version detection:** remove the silent fallback to NiFi 1.0.0. Parse normal and snapshot versions; fail explicitly when `/flow/about` cannot establish a version.
- **Health confidence:** record check coverage for processors, connections, controller services and bulletins. Failed optional checks are surfaced as errors and the overall result becomes `UNKNOWN`, not falsely `HEALTHY`.
- **Dependency compatibility:** constrain the existing FastMCP implementation to MCP SDK v1 (`mcp<2`) rather than permitting v2, which removes/renames the imported API and currently breaks server startup. Test dependencies are available via the `test` extra.
- **Regression tests:** add tests for redaction, unknown/version parsing, mutation timeout retry behaviour, non-retryable read errors and incomplete health-check coverage.

## Verification performed locally

- `PYTHONPATH=src python -m unittest discover -s tests -v`: 9 tests passed in the current checkout.
- `PYTHONPATH=src python -m compileall -q src tests scripts`: passed.
- `git diff --check`: passed after whitespace cleanup.
- No Docker used and no live NiFi/Knox cluster contacted.

## Not yet verified / blocked

- No live NiFi endpoint was available for end-to-end integration tests.
- No write operation was exercised against a real NiFi instance.
- The local GitHub connector reports `push: false` for the `Vinz2168/NiFi-MCP-Server-cloudera` fork; this branch has not been published or opened as a PR.
- Ruff reports numerous pre-existing project-wide modernization/style findings (including legacy `typing` aliases); these were not mass-rewritten because that would create unrelated churn.

## Reproducible setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m unittest discover -s tests -v
python -m compileall -q src tests
```


## Repeatable MCP protocol smoke checks — 2026-10-28

Verified again on the connected Mac using `/tmp/nifi-mcp-modernise/.venv/bin/python`:

- `python -m unittest discover -s tests -v`: **5/5 passed**.
- `python -m compileall -q src tests scripts`: passed.
- `git diff --check`: passed.
- `PYTHONPATH=src python scripts/smoke_mcp.py`: passed; MCP protocol `2025-11-25`, server `nifi-mcp-server 1.30.0`, 35 tools registered; all four required tools found.
- Started Streamable HTTP locally on `127.0.0.1:8000`, then ran `scripts/smoke_mcp.py --transport streamable-http --url http://127.0.0.1:8000/mcp`: passed with the same 35 tools; MCP HTTP requests returned 200/202 as expected. The temporary server was terminated after the test.

**Scope limitation remains:** both protocol tests use `NIFI_API_BASE=http://127.0.0.1:1/nifi-api`, an intentionally unreachable placeholder, and `NIFI_READONLY=true`. They do not call NiFi tools or prove live API connectivity/authentication. Safe config discovery found no NiFi entry in Claude Desktop's MCP server list, no NiFi-related environment variables, and no local listeners on ports 8000, 8080, 8443 or 9090 after the test. The only discovered `.env` file contains unrelated MCP-governance settings; its values were not displayed. A real authorised NiFi endpoint and approved authentication method remain required for end-to-end acceptance.



Additional MCP transport check after allowlist implementation:

- A real stdio MCP client session launched the server with NIFI_READONLY=false and NIFI_ALLOWED_ACTIONS=start_processor.
- MCP tools/list returned 36 tools: start_processor was exposed, create_processor and empty_connection_queue were absent, and read-only get_controller_service_details remained available.
- No NiFi tool was invoked; this proves MCP-level tool exposure only, not NiFi API connectivity or a write operation.

## Action allowlist enforcement — 2026-10-28

A follow-up audit found that ServerConfig parsed NIFI_ALLOWED_ACTIONS, but the server did not apply the setting when registering mutation tools. This meant the configuration looked available without actually limiting the tool surface. That gap is now fixed in this branch:

- With NIFI_READONLY=true, no mutation tools are registered.
- When NIFI_READONLY=false and NIFI_ALLOWED_ACTIONS is non-empty, only exact comma-separated mutation-tool names are registered (case-insensitive; surrounding whitespace ignored).
- Unknown names fail startup rather than silently enabling an unintended tool set.
- An empty allowlist preserves backward compatibility: explicitly setting NIFI_READONLY=false exposes the full mutation tool set.
- Read-only tools remain available regardless of the write allowlist.

Three regression tests cover allowlist filtering, unknown action rejection, and backward-compatible explicit write enablement. Current checkout suite: 8/8 tests pass. The allowlist is an MCP tool-exposure guardrail, not a substitute for NiFi's own authentication/authorisation policies.
