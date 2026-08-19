# Deterministic FSM State Machine Specification

## State Matrix & Transition Invariants

| State | Input | Operation | Output | Next State on Success | Next State on Failure | Retry Budget |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ISSUE_RECEIVED`** | Issue JSON payload | Validate schema & initialize ledger | Issue Primitive | `ANALYZING` | `FAILED` | 0 |
| **`ANALYZING`** | Issue Primitive | Extract requirements & symbols | Requirements Contract | `SPEC_READY` | `FAILED` | 1 |
| **`SPEC_READY`** | Requirements Contract | Synthesize preconditions/invariants | Specification Contract | `LOCALIZING` | `FAILED` | 1 |
| **`LOCALIZING`** | Repo files & Spec | Scan AST & run Ochiai SBFL | Suspicious Symbol List | `PLANNING` | `FAILED` | 1 |
| **`PLANNING`** | Suspicious Symbols | Synthesize minimal repair plan | Execution Plan | `IMPLEMENTING` | `FAILED` | 2 |
| **`IMPLEMENTING`** | Execution Plan | Generate unified diff / Search-Replace | Candidate Patch | `VALIDATING` | `DEBUGGING` | 3 |
| **`VALIDATING`** | Candidate Patch | Run Flake8 syntax gate & compilation | Syntax Validation Report | `VERIFYING` | `DEBUGGING` | 3 |
| **`DEBUGGING`** | Traceback / Lint Error | Parse failure & adjust plan | Corrected Plan | `IMPLEMENTING` | `FAILED` (if N >= 3) | 3 |
| **`VERIFYING`** | Patched repo | Execute Fail-to-Pass PoC & unit tests | Test Report | `SECURITY_CHECK` | `DEBUGGING` | 3 |
| **`SECURITY_CHECK`** | Candidate Patch | Run SAST (Bandit/Semgrep) checks | Security Audit Report | `MUTATION_TESTING`| `DEBUGGING` | 2 |
| **`MUTATION_TESTING`**| Patched code + tests| Inject AST operator mutations | Mutation Adequacy Score| `RISK_ASSESSMENT` | `DEBUGGING` | 2 |
| **`RISK_ASSESSMENT`** | Full Audit Metrics | Calculate Regression Risk Index (RRI) | Risk Profile & Tier | `PR_READY` / `AWAITING_APPROVAL` | `FAILED` | 0 |
| **`AWAITING_APPROVAL`**| Slack/Webhook payload | Await Human Sign-off | Decision (APPROVE/REJECT) | `PR_READY` | `FAILED` | 0 |
| **`PR_READY`** | Approved Patch | Commit Git branch & open PR | Published PR URL | `COMPLETED` | `FAILED` | 1 |
| **`COMPLETED`** | PR URL | Finalize transaction ledger | Success Event | Terminal | - | - |
| **`FAILED`** | Error Details | Atomic rollback of workspace | Failure Report | Terminal | - | - |
