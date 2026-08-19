# Implementation Guide: AI Software Factory

## 1. Codebase Directory Map
```
/ai-software-factory/
├── app-flow.py             # Core FSM Orchestrator & State Ledger
├── task.py                 # Sandbox Task Execution Engine (Linter & Test runner)
├── Dockerfile              # Hardened Sandbox environment Definition
├── docker-compose.yml      # Multi-Service Production Deployment Compose
├── mock-payload.json       # Mock Input payload for testing
├── schema.md               # PostgreSQL Schema Definitions (SQL DDL)
├── rules.md                # Specialized System Prompt instruction Rules
├── prd.md                  # Product Requirements
├── design.md               # Architecture & Flow Diagrams
└── techspec.md             # API Contracts & Command Specifications
```

## 2. Local Setup and Development Instructions

### Prerequisites
* Docker & Docker Compose v2+ installed
* Python 3.12+ (for local scripts)

### Installation
1. Clone your project files into a workspace directory.
2. Build and spin up the multi-service queue:
   ```bash
   docker-compose up --build -d
   ```
3. Run a mock repair cycle locally using the orchestrator:
   ```bash
   python3 app-flow.py
   ```

## 3. Deployment & Scaling Production Notes
* **DinD Setup:** Production deployments utilize Kubernetes. The worker Pods require access to a Docker daemon or utilize lightweight micro-VMs (e.g., Firecracker) to handle dynamic container sandboxing securely.
* **Celery Concurrency:** Scale workers horizontally using Celery. For high-throughput environments, configure dedicated queues for CPU-heavy tasks like mutation testing.
