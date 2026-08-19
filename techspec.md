# Technical Specification: AI Software Factory

## 1. Database Schema Specifications
We use PostgreSQL to store system states, tasks, and historical trajectories.
See `schema.md` for full DDL definitions.

## 2. Orchestration API Contracts

### POST /api/v1/factory/issues
Submit an issue for repair.
* **Payload Format:** See `mock-payload.json`.
* **Response:**
```json
{
  "issue_id": "89c1d2e3-fa89-49c5-9271-9876543210ab",
  "status": "INIT",
  "message": "Orchestrator initialized state machine."
}
```

### GET /api/v1/factory/issues/{issue_id}/status
Track FSM execution state and trajectories.
* **Response:**
```json
{
  "issue_id": "89c1d2e3-fa89-49c5-9271-9876543210ab",
  "current_state": "VERIFICATION",
  "retry_count": 1,
  "history": [
    {"state": "INIT", "timestamp": "2026-08-19T09:00:00Z"},
    {"state": "LOCALIZATION", "timestamp": "2026-08-19T09:00:15Z"},
    {"state": "PLANNING", "timestamp": "2026-08-19T09:01:10Z"},
    {"state": "REPAIR", "timestamp": "2026-08-19T09:01:45Z"}
  ]
}
```

## 3. Sandbox CLI Commands
Tasks running inside the sandbox use `task.py` to communicate back to the orchestrator.
* **Syntax Linter Command:**
  `flake8 --isolated --select=F821,F822,F831,E111,E112,E113,E999,E902 /workspace/repo/django/forms/models.py`
* **Test Runner Command:**
  `pytest -q /workspace/repo/tests/test_model_fields.py`
