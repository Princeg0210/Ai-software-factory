# Ponytail Rule Set: The "Lazy Senior Developer" Framework for AI Coding Agents

## Core Philosophy
The best code is the code you never wrote. Eliminate over-engineering, unnecessary abstractions, and bloated diffs. Always produce the minimal, clean, standard-library-first correction that directly resolves the issue.

---

## The Decision Ladder
Before writing any code or generating a plan, step through this decision ladder:

1. **Does this need to exist? (YAGNI - You Ain't Gonna Need It)**
   - Never add speculative helpers, extra config files, or unused method arguments.
   - Do not re-architect a module when a single conditional fix is sufficient.

2. **Already in this codebase?**
   - Inspect the symbol map first. Reuse existing utility functions, error classes, and validation routines.
   - Match existing coding conventions and style exactly.

3. **Does the standard library do it?**
   - Always prefer built-in Python standard library modules (`re`, `ast`, `json`, `math`, `datetime`, `urllib`, `collections`) before reaching for third-party libraries.
   - Never add new package dependencies to `requirements.txt` or `pyproject.toml` unless explicitly mandated by the issue.

4. **Can it be one line?**
   - Aim for the most concise and readable correction possible.

5. **Write the minimum code that works:**
   - Always write targeted, minimal search-and-replace unified diffs.
   - Never regenerate or rewrite entire source code files.

---

## Agent Enforcement Invariants

### 1. Minimal Change Invariant
- Every modified line must be strictly necessary to fix the reported defect or pass the verification tests.
- Do not refactor surrounding code, reformat unrelated lines, or add explanatory comments inside unchanged blocks.

### 2. Backward Compatibility Invariant
- Never break or change public method signatures or class interfaces unless the issue explicitly requests an API modification.
- Preserve existing exception types, return signatures, and parameter defaults.

### 3. Fail-to-Pass Test Verification
- Write minimal, isolated reproduction tests (PoCs) that prove the defect exists on unpatched code and passes cleanly after the patch is applied.
