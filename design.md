# System Design Document: AI Software Factory

## 1. System Architecture
The AI Software Factory consists of three main decoupled subsystems:
1. **Web Dashboard & API Orchestrator:** Manages the user interface, payload ingestion, and drives the FSM Orchestrator.
2. **Task Queue & Workers:** Distributed Celery workers that execute individual state actions (e.g., localization, repair, verification).
3. **Hardened Execution Sandbox:** Highly isolated Docker containers where repository source code, AST parsers, linters, and test suites are executed safely.

## 2. Core Subsystems

### FSM State Orchestrator
Uses an immutable state ledger in PostgreSQL. State transitions are governed by the `AppFlowOrchestrator` inside `app-flow.py`.

```
                  ┌───────────────────────────────┐
                  │          INIT STATE           │
                  └───────────────┬───────────────┘
                                  │ Issue Payload
                                  ▼
                  ┌───────────────────────────────┐
                  │      LOCALIZATION STATE       │◄────────┐
                  └───────────────┬───────────────┘         │
                                  │ Suspicious Files        │
                                  ▼                         │
                  ┌───────────────────────────────┐         │
                  │        PLANNING STATE         │         │ Max
                  └───────────────┬───────────────┘         │ Retries
                                  │ Repair Strategy         │ (3)
                                  ▼                         │
                  ┌───────────────────────────────┐         │
                  │         REPAIR STATE          │◄─────┐  │
                  └───────────────┬───────────────┘      │  │
                                  │ Generated Patch      │  │
                                  ▼                      │  │
                  ┌───────────────────────────────┐      │  │
                  │      VERIFICATION STATE       ├──────┴──┘
                  └───────────────┬───────────────┘ Fail Tests / Lint
                                  │ Pass Tests
                                  ▼
                  ┌───────────────────────────────┐
                  │      HUMAN REVIEW GATE        │ (Risk-adaptive)
                  └───────────────┬───────────────┘
                                  │ Approved
                                  ▼
                  ┌───────────────────────────────┐
                  │          MERGE STATE          │
                  └───────────────────────────────┘
```

### AST & Repository Map Backend
Integrates tree-sitter in Python to map classes and methods. It calculates Ochiai spectrum-based suspiciousness scores using a helper dynamic test coverage framework to prioritize code search.

### Agent-Computer Interface (ACI)
Implements CodeActAgent. Rather than writing arbitrary files, the agent is restricted to standard commands (`open_file`, `scroll_file`, `edit_file`, `run_tests`) that provide structured, truncated feedback to minimize context window usage.
