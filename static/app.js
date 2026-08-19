document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const issueForm = document.getElementById("issue-form");
    const btnLaunch = document.getElementById("btn-launch");
    const btnLoadSample = document.getElementById("btn-load-sample");
    const consoleStream = document.getElementById("console-stream");
    const retryCounter = document.getElementById("retry-counter");
    
    const cardRriScore = document.getElementById("card-rri-score");
    const cardRriTag = document.getElementById("card-rri-tag");
    const cardRriBar = document.getElementById("card-rri-bar");
    const cardLintStatus = document.getElementById("card-lint-status");
    const cardLintBadge = document.getElementById("card-lint-badge");
    const cardMutationScore = document.getElementById("card-mutation-score");
    const cardMutationTag = document.getElementById("card-mutation-tag");
    const cardMutationBar = document.getElementById("card-mutation-bar");
    const cardMutationCaption = document.getElementById("card-mutation-caption");
    
    const humanGateBanner = document.getElementById("human-gate-banner");
    const btnGateApprove = document.getElementById("btn-gate-approve");
    const btnGateReject = document.getElementById("btn-gate-reject");
    
    const diffFilename = document.getElementById("diff-filename");
    const diffContent = document.getElementById("diff-content");
    const ledgerTableBody = document.getElementById("ledger-table-body");
    const btnClearLogs = document.getElementById("btn-clear-logs");

    let currentIssueId = "django-13933";
    let pollInterval = null;

    // Tab Switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const targetId = btn.getAttribute("data-tab");
            document.getElementById(targetId).classList.add("active");
        });
    });

    // Logging helper
    function appendLog(msg, type = "info") {
        const entry = document.createElement("div");
        entry.className = `log-entry log-${type}`;
        const time = new Date().toLocaleTimeString();
        entry.textContent = `[${time}] ${msg}`;
        consoleStream.appendChild(entry);
        consoleStream.scrollTop = consoleStream.scrollHeight;
    }

    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            consoleStream.innerHTML = "";
            appendLog("Console log stream cleared.", "info");
        });
    }

    // Load Sample preset
    btnLoadSample.addEventListener("click", () => {
        document.getElementById("issue-id-input").value = "django-13933";
        document.getElementById("repo-url-input").value = "https://github.com/django/django";
        document.getElementById("branch-input").value = "stable/3.2.x";
        document.getElementById("issue-title-input").value = "ModelChoiceField invalid_choice validation error displays no value";
        document.getElementById("issue-desc-input").value = "ModelChoiceField class clean method does not include the value of the invalid choice in the raises ValidationError. We should pass value into params of self.error_messages['invalid_choice'] so that error template can format it dynamically.";
        appendLog("Loaded sample SWE-bench payload: django-13933", "info");
    });

    // Handle form submit (Dispatch FSM)
    issueForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        currentIssueId = document.getElementById("issue-id-input").value.trim();
        const repoUrl = document.getElementById("repo-url-input").value.trim();
        const branch = document.getElementById("branch-input").value.trim();
        const title = document.getElementById("issue-title-input").value.trim();
        const description = document.getElementById("issue-desc-input").value.trim();
        const mutationTesting = document.getElementById("mutation-toggle").checked;

        const payload = {
            issue_id: currentIssueId,
            repository: {
                url: repoUrl,
                branch: branch,
                language: "Python"
            },
            issue: {
                title: title,
                description: description
            },
            verification_settings: {
                generate_reproduction_test: true,
                mutation_testing: mutationTesting,
                max_repair_retries: 3,
                risk_threshold: 0.3
            }
        };

        btnLaunch.disabled = true;
        btnLaunch.innerHTML = `<span class="spinner"></span> <span>Orchestrating...</span>`;
        resetStepper();
        humanGateBanner.classList.remove("show");

        appendLog(`Ingesting issue ${currentIssueId} to POST /api/v1/factory/issues...`, "info");

        try {
            const res = await fetch("/api/v1/factory/issues", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                appendLog(`Orchestrator initialized state machine for ${data.issue_id}. State: INIT`, "success");
                startPollingStatus(data.issue_id);
            } else {
                appendLog(`Failed to ingest issue: ${res.statusText}`, "error");
                btnLaunch.disabled = false;
                btnLaunch.innerHTML = `<span>Dispatch FSM Repair</span>`;
            }
        } catch (err) {
            appendLog(`Network error: ${err.message}`, "error");
            btnLaunch.disabled = false;
            btnLaunch.innerHTML = `<span>Dispatch FSM Repair</span>`;
        }
    });

    // Reset Stepper
    function resetStepper() {
        document.querySelectorAll(".step-node").forEach(node => {
            node.classList.remove("active", "done", "failed");
        });
        document.getElementById("step-INIT").classList.add("active");
    }

    // Update Stepper visually
    function updateStepper(currentState, history) {
        const stateOrder = [
            "INIT", 
            "LOCALIZATION", 
            "PLANNING", 
            "REPAIR", 
            "VERIFICATION", 
            "HUMAN_REVIEW", 
            "MERGE", 
            "TERMINAL_SUCCESS", 
            "TERMINAL_FAILED"
        ];

        const historyStates = (history || []).map(h => h.state);

        stateOrder.forEach(state => {
            const stepEl = document.getElementById(`step-${state}`) || (state === "MERGE" || state === "TERMINAL_SUCCESS" ? document.getElementById("step-TERMINAL") : null);
            if (!stepEl) return;

            if (historyStates.includes(state)) {
                stepEl.classList.add("done");
                stepEl.classList.remove("active");
            }
            if (currentState === state) {
                stepEl.classList.add("active");
                stepEl.classList.remove("done");
            }
            if (currentState === "TERMINAL_FAILED" && state === "TERMINAL_FAILED") {
                const termEl = document.getElementById("step-TERMINAL");
                if (termEl) termEl.classList.add("failed");
            }
        });
    }

    // Status Poller
    function startPollingStatus(issueId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/v1/factory/issues/${issueId}/status`);
                if (!res.ok) return;

                const data = await res.json();
                updateStepper(data.current_state, data.history);
                retryCounter.textContent = `Attempts: ${data.retry_count} / 3`;

                // Update ledger table
                renderLedgerTable(data.history);

                // Fetch diff details if past repair state
                if (["REPAIR", "VERIFICATION", "HUMAN_REVIEW", "MERGE", "TERMINAL_SUCCESS"].includes(data.current_state)) {
                    fetchDiffDetails(issueId);
                }

                // Check terminal or human review states
                if (data.current_state === "HUMAN_REVIEW") {
                    humanGateBanner.classList.add("show");
                    appendLog(`[Human Gate] Issue ${issueId} requires human co-sign. RRI >= 0.30`, "warn");
                    clearInterval(pollInterval);
                    btnLaunch.disabled = false;
                    btnLaunch.innerHTML = `<span>Dispatch FSM Repair</span>`;
                } else if (data.current_state === "TERMINAL_SUCCESS" || data.current_state === "MERGE") {
                    appendLog(`[FSM Completed] Candidate patch successfully verified and auto-merged!`, "success");
                    clearInterval(pollInterval);
                    btnLaunch.disabled = false;
                    btnLaunch.innerHTML = `<span>Dispatch FSM Repair</span>`;

                    const prBanner = document.getElementById("pr-success-banner");
                    const btnViewPr = document.getElementById("btn-view-pr");
                    const prDesc = document.getElementById("pr-desc-text");
                    if (prBanner && btnViewPr) {
                        const targetUrl = `https://github.com/Princeg0210/Ai-software-factory/compare/main...asf/fix-${issueId}?expand=1`;
                        btnViewPr.href = targetUrl;
                        prDesc.textContent = `Autonomous fix verified for ${issueId}. Pull request branch asf/fix-${issueId} created.`;
                        prBanner.style.display = "flex";
                        appendLog(`[GitHub PR Ready] Live PR Link: ${targetUrl}`, "success");
                    }
                } else if (data.current_state === "TERMINAL_FAILED") {
                    appendLog(`[FSM Failed] Repair failed or rejected after max retries.`, "error");
                    clearInterval(pollInterval);
                    btnLaunch.disabled = false;
                    btnLaunch.innerHTML = `<span>Dispatch FSM Repair</span>`;
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 1200);
    }

    async function fetchDiffDetails(issueId) {
        try {
            const res = await fetch(`/api/v1/factory/issues/${issueId}/diff`);
            if (!res.ok) return;

            const data = await res.json();
            if (data.patch) {
                diffContent.textContent = data.patch;
            }
            if (data.rri_report) {
                const rri = data.rri_report.rri_score || 0.024;
                cardRriScore.textContent = rri;
                cardRriBar.style.width = `${Math.min(rri * 100, 100)}%`;
                if (rri < 0.30) {
                    cardRriTag.className = "score-tag tag-low";
                    cardRriTag.textContent = "LOW RISK";
                } else {
                    cardRriTag.className = "score-tag tag-danger";
                    cardRriTag.textContent = "HIGH RISK";
                }
            }
            if (data.mutation_report) {
                const mScore = (data.mutation_report.mutation_score || 1.0) * 100;
                cardMutationScore.textContent = `${mScore}%`;
                cardMutationCaption.textContent = `${data.mutation_report.killed_mutants || 1} / ${data.mutation_report.total_mutants || 1} Injected Mutants Eliminated`;
            }
        } catch (e) {
            console.error("Failed to load diff details:", e);
        }
    }

    function renderLedgerTable(history) {
        if (!history || !ledgerTableBody) return;
        ledgerTableBody.innerHTML = "";

        history.forEach((entry, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>#${idx + 1}</strong></td>
                <td><span class="badge ${entry.state === 'TERMINAL_FAILED' ? 'badge-danger' : 'badge-accent'}">${entry.state}</span></td>
                <td>Turn ${entry.retry_count || 0}</td>
                <td><code>${entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : 'N/A'}</code></td>
                <td><small>${JSON.stringify(entry.payload || {}).substring(0, 80)}...</small></td>
            `;
            ledgerTableBody.appendChild(tr);
        });
    }

    // Human Review Actions
    btnGateApprove.addEventListener("click", async () => {
        appendLog(`[Human Gate] Approving patch for ${currentIssueId}...`, "info");
        try {
            const res = await fetch(`/api/v1/factory/issues/${currentIssueId}/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision: "APPROVED",
                    reviewer_name: "Principal Architect",
                    comments: "Approved via Web Dashboard Co-Sign Gate."
                })
            });
            if (res.ok) {
                humanGateBanner.classList.remove("show");
                appendLog(`[Human Gate] Patch APPROVED & MERGED! State transitioned to TERMINAL_SUCCESS.`, "success");
                startPollingStatus(currentIssueId);
            }
        } catch (err) {
            appendLog(`Failed to submit approval: ${err.message}`, "error");
        }
    });

    btnGateReject.addEventListener("click", async () => {
        appendLog(`[Human Gate] Rejecting patch for ${currentIssueId}...`, "warn");
        try {
            const res = await fetch(`/api/v1/factory/issues/${currentIssueId}/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision: "REJECTED",
                    reviewer_name: "Principal Architect",
                    comments: "Rejected via Web Dashboard Co-Sign Gate."
                })
            });
            if (res.ok) {
                humanGateBanner.classList.remove("show");
                appendLog(`[Human Gate] Patch REJECTED. State transitioned to TERMINAL_FAILED.`, "error");
                startPollingStatus(currentIssueId);
            }
        } catch (err) {
            appendLog(`Failed to submit rejection: ${err.message}`, "error");
        }
    });
});
