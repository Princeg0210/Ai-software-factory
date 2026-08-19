# Product Requirements Document (PRD): AI Software Factory

## 1. Objectives & Overview
The AI Software Factory is an enterprise-grade automation system designed to autonomously ingest, localize, repair, and verify software engineering issues in Git repositories. The core product objective is to provide developers with a trustworthy, secure, and cost-effective "AI teammate" that reliably resolves bug reports and feature requests without introducing regressions or security vulnerabilities.

## 2. Key Customer Personas
* **Software Engineers:** Wants an automated tool to handle routine bug fixes, dependencies, and test generation, saving them time. Requires high precision, clear Git diffs, and zero false positives.
* **Engineering Managers:** Wants to increase team velocity and reduce time-to-resolution (TTR) for customer-reported issues. Requires cost controls and risk-adaptive approvals before code hits production.
* **Security Officers:** Requires absolute isolation when executing AI-generated code, ensuring no proprietary data is leaked and no remote execution risks threaten the corporate network.

## 3. Product Principles
1. **Verification-First:** No patch is considered a solution until it has been statically analyzed, compiled, linted, and verified by reproduction tests and mutation analysis.
2. **Guided Autonomy:** Replace open-ended, unpredictable agent loops with a strict Finite State Machine (FSM) orchestrator to ensure predictable execution times and costs.
3. **Risk-Adaptive Human Gating:** High-risk code changes always require human eyes; low-risk changes are automated.

## 4. Key Functional Features
* **FSM Orchestration:** Dynamic execution path restricted to structured state transitions.
* **AST-SBFL Code Localization:** Combining static structure analysis with runtime spectrum fault localization.
* **CodeAct Repair Agent:** Multi-line search-and-replace patching with interactive file viewers.
* **Mutation Gating:** Verifies test coverage strength before merging patches.
* **Air-Gapped Docker Container Sandboxing:** Safe execution of untrusted user tests and code.
* **Regression Risk Assessment:** Automatically scores proposed fixes on code metrics, AST modifications, and test confidence.

## 5. Non-Functional Requirements & Guardrails
* **Cost Controls:** Max API token budget per issue is capped at $3.00 USD. Max worker execution time is 10 minutes.
* **Security:** Docker runtime must have `--network none` during test execution. No root users.
* **Accuracy:** Target success rate of $> 50\%$ on human-vetted SWE-bench Verified tasks.
