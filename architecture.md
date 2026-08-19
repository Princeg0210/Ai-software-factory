# System Architecture: AI Software Factory (ASF)

## 1. Overview
The AI Software Factory is an event-driven, verification-first automated software repair system that replaces stochastic agentic loops with a deterministic Finite State Machine (FSM).

```mermaid
graph TD
    A[Issue Ingestion: REST / Celery] --> B[FSM State Ledger: ISSUE_RECEIVED]
    B --> C[ANALYZING & SPEC_READY: Spec Contract Synthesizer]
    C --> D[LOCALIZATION: AST Symbol Graph + Ochiai SBFL]
    D --> E[PLANNING: Hierarchical Strategy & Ponytail YAGNI]
    E --> F[IMPLEMENTING: CodeAct Search/Replace Diff via ACI]
    F --> G[VALIDATING: Flake8 Syntax Gate + Compilation]
    G -- Syntax Error --> H[DEBUGGING: AST & Traceback Self-Correction]
    H --> F
    G -- Passed --> I[VERIFYING: Fail-to-Pass PoC + Regression Suite]
    I -- Tests Failed (Retries < 3) --> H
    I -- Tests Failed (Retries >= 3) --> Z[FAILED]
    I -- Tests Passed --> J[SECURITY_CHECK: SAST & Dependency Audit]
    J --> K[MUTATION_TESTING: Semantic Operator Fault Injections]
    K --> L[RISK_ASSESSMENT: RRI Multi-Factor Score]
    L -- Low Risk (RRI < 0.30) --> M[PR_READY / AUTO-MERGE]
    L -- High Risk (RRI >= 0.30) --> N[AWAITING_APPROVAL: Human Co-Sign Gate]
    N -- Approved --> M
    N -- Rejected --> Z
    M --> O[COMPLETED]
```

## 2. Decoupled Subsystem Layers
1. **API & Orchestration Layer (`main.py`, `fsm/`)**: Drives the deterministic state engine and persists immutable transition records into PostgreSQL/SQLite.
2. **Repository Intelligence Layer (`intelligence/`)**: AST symbol graph mapping, call-relationship indexing, and Ochiai spectrum-based fault localization.
3. **Agent & ACI Layer (`agents/`)**: Task-scoped agents (Localization, CodeAct Repair, Verification) operating inside a 100-line chunk viewing window under Ponytail rules.
4. **Deterministic Validation & Sandbox Layer (`sandbox/`, `verification/`, `security/`)**: Flake8 linter gate, ephemeral Docker sandbox isolation (`--network none`, non-root user), AST mutation testing engine, and SAST scanner.
5. **Risk-Adaptive Human Approval Layer (`risk/`)**: Calculates Regression Risk Index (RRI) and routes high-risk diffs to interactive Slack/Teams review gateways.
