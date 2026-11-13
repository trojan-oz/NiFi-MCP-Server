# Delivery and Execution Policy

T4H uses Cloudflare-first delivery. GitHub is for source control, code review, issues, decisions and durable evidence, not execution infrastructure.

## Execution boundary
- Do not add, enable or rely on GitHub Actions or GitHub-hosted runners for builds, tests, orchestration or deployment.
- Prefer Cloudflare Workers Builds for supported Git-connected Worker build/deploy pipelines. For custom CI pipelines, use Cloudflare Workflows with the Cloudflare CI SDK (`@cloudflare/ci`) and its isolated sandbox runners. Select the appropriate Cloudflare Workers, Pages, Containers, Workflows, Queues and related services for the workload.
- Cloudflare may post build status, previews and check results to GitHub. These are evidence surfaces, not GitHub Actions execution.
- Never assume a runner, integration, binding, secret or credential exists until verified.

## Required delivery sequence
1. Inspect the existing repository, canonical implementation, runtime, deployment target, dependencies, data boundaries, credentials and production state. Reuse existing infrastructure; do not create competing systems or orphans.
2. Build in an isolated, owned sandbox. Do not depend on a developer's Mac or a GitHub-hosted runner.
3. Dry-run before promotion. Run relevant unit, integration, regression, security, compatibility and deployment checks. Record commands, outcomes, commit SHA and gaps. Unexecuted tests are not passes.
4. Move execution to Cloudflare. Configure the appropriate Cloudflare build/Workflow pipeline, isolated runner(s), approved secrets, bindings, observability and recovery. Verify the Cloudflare execution actually runs.
5. Promote a tested artifact through a controlled Cloudflare deployment. Keep preview/staging separate from production; preserve rollback and avoid unrelated production changes.
6. Verify live production critical paths. Capture deployment/version ID, real request or user-path results, runtime telemetry, logs and data-integrity checks.
7. Close with proof: outcome, repository/commit, Cloudflare project/environment, build/deployment receipt, test evidence, live verification, telemetry, recovery path and gaps. A queue entry, PR, commit, configured workflow or green check alone is not completion.

## Evidence and change control
A task is REAL only when execution has a verifiable receipt and the resulting runtime change is observed. Missing receipts/telemetry, stale evidence, unverified dependencies or untested recovery downgrade the result. Classify incomplete work honestly as PARTIAL, BLOCKED or DEGRADED. Do not expose credentials, bypass authority, alter customer data or make unrelated production changes. Obtain human approval for destructive, safety-sensitive, legal or authority-bound actions. Prefer reversible minimal-delta releases.

This policy applies to all build, test, automation and deployment work in this repository. Repository-specific instructions may add controls, but must not weaken this baseline.