# Modernisation decision record: preserve the original deployment assumptions first

**Status:** Working decision; review with the initial build before adopting any alternative architecture.

## Why the original project may use local `stdio`

The repository documents a local MCP server launched by an AI host (including Claude Desktop and Cloudera Agent Studio). The MCP server then calls the configured NiFi API. We do not have evidence of the author's personal rationale, so the following are hypotheses, not claims about his intent:

1. **Customer/platform fit:** the intended AI host may already support launching a local MCP process.
2. **Security and network boundaries:** a local process avoids exposing a separate MCP listener to a network. It does not, by itself, sandbox the process or guarantee safe permissions.
3. **Cost and operational simplicity:** local execution avoids the cost and work of hosting, monitoring and maintaining another service.
4. **Proof-of-concept speed:** `stdio` is a straightforward way to prove that an AI client can call NiFi tools without first building a remote service.
5. **Deployment or approval constraints:** the customer's infrastructure, procurement, security review or available time may have favoured the smallest deployment that worked.

These explanations may overlap. We should ask the author or customer rather than choosing one as fact.

## Initial modernisation decision

**Mirror the original operating model first, on the assumption that its constraints still apply until we learn otherwise.**

- Keep the existing local `stdio` entry point and AI-host configuration.
- Keep the NiFi API as the system of record; MCP tools must query and act on NiFi, not on a simulated display.
- Preserve the existing read-only-by-default posture and require explicit configuration for mutations.
- Improve the existing implementation within that boundary: dependency compatibility, authentication options, version handling, error reporting, secret redaction, safe retry behaviour, diagnostics, enforced NIFI_ALLOWED_ACTIONS tool filtering and tests.
- Do not make Cloudflare hosting, a browser-control agent, or a new remote transport a prerequisite for the first modernised build.
- Do not represent the TV page or simulated operations data as proof of MCP-to-NiFi integration.

This is a conservative first pass, not a claim that `stdio` is always best. It keeps the first version close enough to the original that we can validate and discuss it without conflating the results with a new architecture.

## Improvements made so far

The working local branch includes standalone NiFi authentication support and flowfile/provenance diagnostic tools from the existing fork branches, plus reliability and safety hardening. Nine local regression tests pass, including enforcement of the configured write-tool allowlist and read-only-mode coverage. These are code-level checks only: the server has **not** yet been demonstrated end to end against a live NiFi instance, and no live write operation has been verified.

The current local branch is `modernise/evidence-first-guardrails`, commit `b2cc77a`. The GitHub-folder copy is local/iCloud-synced; the push to the remote repository was denied by GitHub permissions, so this is not yet a published upstream change.

## Alternatives to evaluate after the initial build is approved

Evaluate these against actual requirements and evidence, rather than switching transports speculatively:

| Option | When it may be justified | What must be proved |
|---|---|---|
| Keep local `stdio` | One user or desktop/agent host can run the server locally | AI client launches it; real NiFi reads work; permissions and secrets are appropriately controlled |
| Remote MCP over Streamable HTTP | Multiple clients, hosted agents or central operations need a shared endpoint | Authentication, authorisation, TLS, network path to NiFi, session/transport compatibility, logging and failure behaviour |
| Cloudflare-hosted gateway or edge component | A real remote-access, identity, routing or policy need is identified | The gateway is deployed and authenticated; its path to NiFi is secure and reachable; an end-to-end AI tool call returns live NiFi data |
| Browser automation alongside MCP | A workflow truly requires operating a visible web UI in addition to the NiFi API | Browser actions are separately authorised and tested; UI control is not confused with MCP-to-NiFi control |
| Customer-specific deployment | Customer security, networking, cost or platform requirements dictate a different arrangement | The constraints are documented and the chosen configuration passes acceptance tests |

Cloudflare is an option, not proof of integration and not automatically the right place to run the NiFi process. A Worker alone cannot reach a private NiFi API unless a secure network path is established.

## Acceptance gate for the first modernised build

Before choosing a different architecture, demonstrate all of the following:

1. A supported AI host launches and connects to the modernised MCP server over the existing transport.
2. The server authenticates to an authorised, real NiFi instance.
3. The AI calls a read tool (at minimum, version and processor/flow listing) and receives actual NiFi results.
4. The results are independently compared with the NiFi UI/API; failures and missing coverage are reported honestly.
5. Read-only mode is verified. Any later mutation test uses an explicitly authorised, safe test flow and is independently verified.
6. The setup and result are repeatable from the documented instructions.

**Decision rule:** establish the original path first; approve the initial build; then choose any transport or hosting changes from demonstrated requirements. Keep unknowns labelled as unknowns.
