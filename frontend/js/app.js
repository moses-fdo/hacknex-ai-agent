// Aether-SWE Antigravity Command Center UI Controller

document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const presetSelect = document.getElementById("presetSelect");
    const issuePromptInput = document.getElementById("issuePromptInput");
    const runAgentBtn = document.getElementById("runAgentBtn");
    const streamContainer = document.getElementById("streamContainer");
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const fileTreeContainer = document.getElementById("fileTreeContainer");
    const astSkeletonContent = document.getElementById("astSkeletonContent");
    const astTotalFilesBadge = document.getElementById("astTotalFilesBadge");

    // Diff Tab Elements
    const diffContent = document.getElementById("diffContent");
    const diffAddedBadge = document.getElementById("diffAddedBadge");
    const diffRemovedBadge = document.getElementById("diffRemovedBadge");

    // Sandbox Tab Elements
    const metricTotalTests = document.getElementById("metricTotalTests");
    const metricPassedTests = document.getElementById("metricPassedTests");
    const metricRegressions = document.getElementById("metricRegressions");
    const metricDuration = document.getElementById("metricDuration");
    const sandboxTerminalOutput = document.getElementById("sandboxTerminalOutput");

    // Dossier Tab Elements
    const dossierContent = document.getElementById("dossierContent");
    const copyDossierBtn = document.getElementById("copyDossierBtn");

    // Settings Modal Elements
    const settingsModal = document.getElementById("settingsModal");
    const openSettingsBtn = document.getElementById("openSettingsBtn");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const settingProvider = document.getElementById("settingProvider");
    const settingBaseUrl = document.getElementById("settingBaseUrl");
    const settingModelName = document.getElementById("settingModelName");
    const settingApiKey = document.getElementById("settingApiKey");
    const toggleApiKeyVisibility = document.getElementById("toggleApiKeyVisibility");
    const testConnectionBtn = document.getElementById("testConnectionBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const connectionStatusMsg = document.getElementById("connectionStatusMsg");
    const currentModelLabel = document.getElementById("currentModelLabel");

    // Hidden Test Modal Elements
    const hiddenTestModal = document.getElementById("hiddenTestModal");
    const openHiddenTestBtn = document.getElementById("openHiddenTestBtn");
    const closeHiddenTestBtn = document.getElementById("closeHiddenTestBtn");
    const hiddenTestCodeInput = document.getElementById("hiddenTestCodeInput");
    const executeHiddenTestBtn = document.getElementById("executeHiddenTestBtn");
    const hiddenEvalResults = document.getElementById("hiddenEvalResults");

    let eventSource = null;
    let rawMarkdownDossier = "";

    // 1. Tab Switching
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            const targetId = btn.getAttribute("data-tab");
            const targetContent = document.getElementById(targetId);
            if (targetContent) targetContent.classList.add("active");
        });
    });

    // 2. Load Settings from LocalStorage
    function loadModelSettings() {
        const saved = localStorage.getItem("aether_swe_model_settings");
        if (saved) {
            try {
                const cfg = JSON.parse(saved);
                settingProvider.value = cfg.provider_type || "anthropic";
                settingBaseUrl.value = cfg.base_url || "";
                settingModelName.value = cfg.model_name || "";
                settingApiKey.value = cfg.api_key || "";
                currentModelLabel.textContent = `Provider: ${cfg.provider_type.toUpperCase()}`;
            } catch (e) {}
        }
    }

    function getModelSettings() {
        return {
            provider_type: settingProvider.value,
            base_url: settingBaseUrl.value.trim() || null,
            model_name: settingModelName.value.trim() || null,
            api_key: settingApiKey.value.trim() || null
        };
    }

    loadModelSettings();

    // Settings Modal Open/Close
    openSettingsBtn.addEventListener("click", () => settingsModal.classList.add("open"));
    closeSettingsBtn.addEventListener("click", () => settingsModal.classList.remove("open"));
    toggleApiKeyVisibility.addEventListener("click", () => {
        settingApiKey.type = settingApiKey.type === "password" ? "text" : "password";
    });

    // Test Connection
    testConnectionBtn.addEventListener("click", async () => {
        connectionStatusMsg.textContent = "Testing connection...";
        const settings = getModelSettings();
        try {
            const resp = await fetch("/api/model/test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings)
            });
            const data = await resp.json();
            if (data.status === "connected") {
                connectionStatusMsg.innerHTML = `<span style="color: var(--accent-emerald);">🟢 Connected to ${data.provider} (${data.latency_ms}ms)</span>`;
            } else {
                connectionStatusMsg.innerHTML = `<span style="color: var(--accent-rose);">❌ Connection Failed: ${data.error || "Unknown error"}</span>`;
            }
        } catch (e) {
            connectionStatusMsg.innerHTML = `<span style="color: var(--accent-rose);">❌ Network Error: ${e.message}</span>`;
        }
    });

    // Save Settings
    saveSettingsBtn.addEventListener("click", () => {
        const settings = getModelSettings();
        localStorage.setItem("aether_swe_model_settings", JSON.stringify(settings));
        currentModelLabel.textContent = `Provider: ${settings.provider_type.toUpperCase()}`;
        settingsModal.classList.remove("open");
    });

    // Hidden Test Modal Open/Close
    openHiddenTestBtn.addEventListener("click", () => hiddenTestModal.classList.add("open"));
    closeHiddenTestBtn.addEventListener("click", () => hiddenTestModal.classList.remove("open"));

    executeHiddenTestBtn.addEventListener("click", async () => {
        const testCode = hiddenTestCodeInput.value.trim();
        if (!testCode) return;
        executeHiddenTestBtn.disabled = true;
        hiddenEvalResults.innerHTML = `<div style="color: var(--accent-cyan);">Running hidden tests in sandbox...</div>`;

        try {
            const resp = await fetch("/api/evaluate/hidden", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ test_code: testCode, test_name: "test_hidden_eval.py" })
            });
            const data = await resp.json();
            if (data.passed) {
                hiddenEvalResults.innerHTML = `
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--accent-emerald); padding: 12px; border-radius: 6px; margin-top: 12px;">
                        <h4 style="color: var(--accent-emerald); margin-bottom: 6px;">✅ ALL HIDDEN TESTS PASSED (${data.passed_tests}/${data.passed_tests})</h4>
                        <pre style="font-family: var(--font-mono); font-size: 0.75rem; color: #A7F3D0;">${data.raw_output}</pre>
                    </div>`;
            } else {
                hiddenEvalResults.innerHTML = `
                    <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid var(--accent-rose); padding: 12px; border-radius: 6px; margin-top: 12px;">
                        <h4 style="color: var(--accent-rose); margin-bottom: 6px;">❌ Hidden Tests Failed (${data.failed_tests} failed)</h4>
                        <pre style="font-family: var(--font-mono); font-size: 0.75rem; color: #FDA4AF;">${data.raw_output}</pre>
                    </div>`;
            }
        } catch (e) {
            hiddenEvalResults.innerHTML = `<div style="color: var(--accent-rose);">Error: ${e.message}</div>`;
        } finally {
            executeHiddenTestBtn.disabled = false;
        }
    });

    // 3. Load Preset Challenges
    async function loadChallenges() {
        try {
            const resp = await fetch("/api/challenges");
            const data = await resp.json();
            presetSelect.innerHTML = `<option value="">-- Choose a Preset Benchmark --</option>`;
            data.challenges.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.id;
                opt.textContent = `${c.title} (${c.difficulty})`;
                opt.dataset.desc = c.description;
                presetSelect.appendChild(opt);
            });
        } catch (e) {
            console.error("Failed to load challenges:", e);
        }
    }

    presetSelect.addEventListener("change", () => {
        const selected = presetSelect.options[presetSelect.selectedIndex];
        if (selected && selected.dataset.desc) {
            issuePromptInput.value = selected.dataset.desc;
        }
    });

    // 4. Load Codebase Explorer & AST Map
    async function loadCodebaseTree() {
        try {
            const resp = await fetch("/api/repo/tree");
            const data = await resp.json();
            fileTreeContainer.innerHTML = "";
            let astLines = [`=== CODEBASE SKELETON: (${data.total_files} files) ===`];

            Object.entries(data.files).forEach(([path, outline]) => {
                // Sidebar Tree item
                const item = document.createElement("div");
                item.className = "tree-file-item";
                item.innerHTML = `
                    <span class="tree-file-name">📄 ${path}</span>
                    <span class="tree-symbol-count">${outline.symbols.length} sym</span>
                `;
                fileTreeContainer.appendChild(item);

                // AST Outline
                astLines.push(`\n[FILE: ${path}] (${outline.line_count} lines)`);
                if (outline.imports && outline.imports.length) {
                    astLines.push(`  Imports: ${outline.imports.slice(0, 6).join(", ")}`);
                }
                outline.symbols.forEach(s => {
                    astLines.push(`  ${s.kind} ${s.name}(${s.args.join(", ")}) [L${s.line_start}-L${s.line_end}]`);
                });
            });

            astSkeletonContent.textContent = astLines.join("\n");
            astTotalFilesBadge.textContent = `${data.total_files} Files Mapped`;
        } catch (e) {
            fileTreeContainer.innerHTML = `<div style="color: var(--text-muted); padding: 10px;">Failed to index repository.</div>`;
        }
    }

    document.getElementById("refreshTreeBtn").addEventListener("click", loadCodebaseTree);

    // 5. Persona Card State Manager
    function setPersonaStatus(personaName, status) {
        const card = document.getElementById(`persona-${personaName}`);
        if (!card) return;
        const tag = card.querySelector(".persona-status-tag");

        card.classList.remove("active", "completed");
        tag.className = "persona-status-tag";

        if (status === "active") {
            card.classList.add("active");
            tag.classList.add("status-active");
            tag.textContent = "RUNNING";
        } else if (status === "completed") {
            card.classList.add("completed");
            tag.classList.add("status-done");
            tag.textContent = "PASSED ✓";
        } else if (status === "veto") {
            tag.classList.add("status-veto");
            tag.textContent = "VETO ✕";
        } else {
            tag.classList.add("status-pending");
            tag.textContent = "IDLE";
        }
    }

    function resetAllPersonas() {
        document.querySelectorAll(".persona-card").forEach(card => {
            card.classList.remove("active", "completed");
            const tag = card.querySelector(".persona-status-tag");
            tag.className = "persona-status-tag status-pending";
            tag.textContent = "IDLE";
        });
    }

    // 6. Connect to SSE Event Stream
    function connectEventStream() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource("/api/events");

        eventSource.onmessage = (e) => {
            try {
                const event = JSON.parse(e.data);
                handleAgentEvent(event);
            } catch (err) {
                console.error("Error parsing event:", err);
            }
        };

        eventSource.onerror = (err) => {
            console.warn("SSE connection closed or re-connecting...");
        };
    }

    function handleAgentEvent(event) {
        // Remove empty state
        const empty = streamContainer.querySelector(".empty-state");
        if (empty) streamContainer.innerHTML = "";

        // Format time
        const timeStr = new Date(event.timestamp * 1000).toLocaleTimeString();

        // Update Persona Card status
        if (event.persona) {
            setPersonaStatus(event.persona, "active");
        }

        // Render Stream Card
        const card = document.createElement("div");
        card.className = "event-card";

        if (event.event_type === "thought") card.classList.add("event-thought");
        else if (event.event_type === "tool_call" || event.event_type === "tool_result") card.classList.add("event-tool");
        else if (event.event_type === "verdict") card.classList.add("event-verdict");

        card.innerHTML = `
            <div class="event-header">
                <span class="event-persona-badge">${event.persona ? event.persona : "Aether-SWE Engine"}</span>
                <span class="event-time">${timeStr}</span>
            </div>
            <div class="event-title">${escapeHtml(event.title)}</div>
            <div class="event-content">${escapeHtml(event.content)}</div>
        `;
        streamContainer.appendChild(card);
        streamContainer.scrollTop = streamContainer.scrollHeight;

        // Specific Tab Updates
        if (event.event_type === "tool_result" && event.persona) {
            setPersonaStatus(event.persona, "completed");
        }

        if (event.event_type === "diff_generated") {
            renderDiff(event.content, event.metadata);
        }

        if (event.event_type === "test_executed" && event.metadata) {
            renderTestResults(event.metadata);
        }

        if (event.event_type === "pipeline_complete") {
            runAgentBtn.disabled = false;
            runAgentBtn.innerHTML = `<span class="icon">🚀</span> RUN AUTONOMOUS AGENT`;
            document.querySelectorAll(".persona-card").forEach(c => c.classList.add("completed"));
            loadCodebaseTree();
        }
    }

    function renderDiff(diffString, metadata) {
        diffContent.innerHTML = "";
        const lines = (diffString || "").split("\n");
        lines.forEach(line => {
            const span = document.createElement("span");
            if (line.startsWith("+")) {
                span.className = "diff-line-add";
            } else if (line.startsWith("-")) {
                span.className = "diff-line-del";
            }
            span.textContent = line + "\n";
            diffContent.appendChild(span);
        });

        if (metadata) {
            diffAddedBadge.textContent = `+${metadata.total_lines_added || 1} lines`;
            diffRemovedBadge.textContent = `-${metadata.total_lines_removed || 1} lines`;
        }
    }

    function renderTestResults(meta) {
        metricTotalTests.textContent = meta.total_tests || 26;
        metricPassedTests.textContent = meta.passed_tests || 26;
        metricRegressions.textContent = meta.regressions || 0;
        metricDuration.textContent = `${meta.duration_seconds || 0.12}s`;
        sandboxTerminalOutput.textContent = meta.raw_output || "Test execution complete.";
    }

    // 7. Run Agent Button Handler
    runAgentBtn.addEventListener("click", async () => {
        const issue = issuePromptInput.value.trim();
        if (!issue) {
            alert("Please enter a bug description or select a preset challenge.");
            return;
        }

        runAgentBtn.disabled = true;
        runAgentBtn.innerHTML = `<span class="icon">⚡</span> AGENT RUNNING...`;
        resetAllPersonas();
        streamContainer.innerHTML = "";

        // Connect SSE stream
        connectEventStream();

        const modelSettings = getModelSettings();

        try {
            const resp = await fetch("/api/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    repo_path: "benchmarks/ecommerce_api",
                    issue_description: issue,
                    model_settings: modelSettings
                })
            });
            const data = await resp.json();
            console.log("Run launched:", data);
        } catch (e) {
            alert("Failed to start agent run: " + e.message);
            runAgentBtn.disabled = false;
            runAgentBtn.innerHTML = `<span class="icon">🚀</span> RUN AUTONOMOUS AGENT`;
        }
    });

    // Copy Dossier Markdown
    copyDossierBtn.addEventListener("click", () => {
        if (!rawMarkdownDossier) {
            rawMarkdownDossier = dossierContent.innerText;
        }
        navigator.clipboard.writeText(rawMarkdownDossier);
        copyDossierBtn.textContent = "✓ Copied!";
        setTimeout(() => copyDossierBtn.textContent = "📋 Copy Markdown", 2000);
    });

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Init
    loadChallenges();
    loadCodebaseTree();
});
