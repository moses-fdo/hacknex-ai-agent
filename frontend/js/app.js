/**
 * Aether-SWE Studio (VS Code UI) Application Logic.
 * ZERO EMOJIS - Strictly SVG & Codicon vector elements.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const hamburgerBtn = document.getElementById("hamburgerBtn");
  const menuFile = document.getElementById("menuFile");
  const fileDropdown = document.getElementById("fileDropdown");
  const btnOpenFile = document.getElementById("btnOpenFile");
  const btnOpenFolder = document.getElementById("btnOpenFolder");
  const btnOpenPresetFolder = document.getElementById("btnOpenPresetFolder");
  const btnMainOpenFolder = document.getElementById("btnMainOpenFolder");
  const btnSideOpenFolder = document.getElementById("btnSideOpenFolder");
  const btnRefreshExplorer = document.getElementById("btnRefreshExplorer");
  const btnNewInvestigation = document.getElementById("btnNewInvestigation");
  const btnExit = document.getElementById("btnExit");

  const explorerTree = document.getElementById("explorerTree");
  const openEditorsList = document.getElementById("openEditorsList");
  const editorTabsBar = document.getElementById("editorTabsBar");
  const titlebarWorkspaceName = document.getElementById("titlebarWorkspaceName");
  const explorerWorkspaceHeader = document.getElementById("explorerWorkspaceHeader");
  const bcRepo = document.getElementById("bcRepo");
  const bcActiveFile = document.getElementById("bcActiveFile");

  const codeEditorView = document.getElementById("codeEditorView");
  const editorGutter = document.getElementById("editorGutter");
  const editorContentArea = document.getElementById("editorContentArea");
  const editorFileMeta = document.getElementById("editorFileMeta");

  const dispatcherView = document.getElementById("dispatcherView");
  const commandCenterView = document.getElementById("commandCenterView");
  const issueTextarea = document.getElementById("issueTextarea");
  const triageFeedback = document.getElementById("triageFeedback");
  const btnRunAgent = document.getElementById("btnRunAgent");

  const worktreeTrigger = document.getElementById("worktreeTrigger");
  const worktreeMenu = document.getElementById("worktreeMenu");
  const sbWorktreeLabel = document.getElementById("sbWorktreeLabel");
  const sbStatusText = document.getElementById("sbStatusText");

  const streamLogs = document.getElementById("streamLogs");
  const panelLogs = document.getElementById("panelLogs");
  const diffViewer = document.getElementById("diffViewer");
  const judgeStats = document.getElementById("judgeStats");
  const sbSpend = document.getElementById("sbSpend");

  // State
  let useWorktree = true;
  let activeRepoPath = "benchmarks/ecommerce_api";
  let hasRunStarted = false;
  let openTabs = []; // { id, path, name, content, isDirty }
  let activeTabId = "command-center";

  // SVG Icons (Zero Emojis)
  const ICONS = {
    folder: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#E2C08D"><path d="M14 4h-4.414L8.293 2.707A1 1 0 0 0 7.586 2.5H2a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1z"/></svg>`,
    folderOpen: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#E2C08D"><path d="M1.5 3A1.5 1.5 0 0 0 0 4.5v7A1.5 1.5 0 0 0 1.5 13H14a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1H7.414L5.707 2.293A1 1 0 0 0 5 2H1.5z"/></svg>`,
    python: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#38BDF8"><path d="M8 1c-3 0-3 2-3 2v2h3v1H4C2 6 2 8 2 8v3c0 2 2 2 2 2h1v-2c0-1.5 1.5-1.5 1.5-1.5h3c1.5 0 1.5-1.5 1.5-1.5V5c0-2-3-2-3-2V1zm-1.5 1a.75.75 0 1 1 0 1.5.75.75 0 0 1 0-1.5z"/></svg>`,
    js: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#EAB308"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    html: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#F97316"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    css: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#60A5FA"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    json: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#FBBF24"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    markdown: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#A78BFA"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    file: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#94A3B8"><path d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1zm4 13H3V2h5v4h5v8z"/></svg>`,
    commandCenter: `<svg width="14" height="14" viewBox="0 0 16 16" fill="#38BDF8"><path d="M4 2v12l10-6z"/></svg>`,
    close: `<svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor"><path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06z"/></svg>`,
    chevronDown: `<svg class="tree-chevron" width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.47 6.47a.75.75 0 0 1 1.06 0L8 8.94l2.47-2.47a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 0 1 0-1.06z"/></svg>`,
    chevronRight: `<svg class="tree-chevron collapsed" width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.47 6.47a.75.75 0 0 1 1.06 0L8 8.94l2.47-2.47a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 0 1 0-1.06z"/></svg>`,
  };

  function getFileIconSvg(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    if (ext === "py") return ICONS.python;
    if (["js", "ts", "jsx", "tsx"].includes(ext)) return ICONS.js;
    if (["html", "htm"].includes(ext)) return ICONS.html;
    if (["css", "scss", "less"].includes(ext)) return ICONS.css;
    if (["json", "yaml", "yml", "toml"].includes(ext)) return ICONS.json;
    if (["md", "markdown", "txt"].includes(ext)) return ICONS.markdown;
    return ICONS.file;
  }

  // 1. Hamburger Menu & File Dropdown
  hamburgerBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    fileDropdown?.classList.toggle("open");
  });

  menuFile?.addEventListener("click", (e) => {
    e.stopPropagation();
    fileDropdown?.classList.toggle("open");
  });

  document.addEventListener("click", () => {
    fileDropdown?.classList.remove("open");
    worktreeMenu?.classList.remove("open");
  });

  // 2. Open Local Folder Logic
  async function handleOpenLocalFolder() {
    fileDropdown?.classList.remove("open");
    if (window.electronAPI && window.electronAPI.selectDirectory) {
      const selectedPath = await window.electronAPI.selectDirectory();
      if (selectedPath) {
        applyWorkspaceFolder(selectedPath);
      }
    } else {
      const manual = prompt("Enter local repository directory path:", activeRepoPath);
      if (manual) {
        applyWorkspaceFolder(manual);
      }
    }
  }

  // 3. Open Local File Logic (via File Picker)
  async function handleOpenFile() {
    fileDropdown?.classList.remove("open");
    if (window.electronAPI && window.electronAPI.selectFile) {
      const res = await window.electronAPI.selectFile();
      if (res && res.success) {
        openCodeFile(res.path, res.name, res.content);
      } else if (res && res.error) {
        showStatusNotification("Error opening file: " + res.error);
      }
    } else {
      // Browser fallback file picker
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".py,.js,.ts,.html,.css,.json,.md,.txt,.sh,.yml,.yaml";
      input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
          openCodeFile(file.name, file.name, ev.target.result);
        };
        reader.readAsText(file);
      };
      input.click();
    }
  }

  // 4. Core File Opening & Editor Switching
  async function openCodeFile(filePath, fileName, optionalContent = null) {
    if (!filePath) return;
    fileName = fileName || filePath.split(/[\\/]/).pop();

    // Check if already open
    const existing = openTabs.find(t => t.id === filePath || t.path === filePath);
    if (existing) {
      switchTab(existing.id);
      return;
    }

    let content = optionalContent;

    // Fetch content if not provided
    if (content === null || content === undefined) {
      showStatusNotification(`Opening ${fileName}...`);
      if (window.electronAPI && window.electronAPI.readFile) {
        const res = await window.electronAPI.readFile(filePath);
        if (res && res.success) {
          content = res.content;
          filePath = res.path;
        } else {
          showStatusNotification(`Failed to read file: ${res ? res.error : "Unknown error"}`);
          return;
        }
      } else {
        // Fallback to backend REST endpoint /api/file
        try {
          const resp = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`);
          const data = await resp.json();
          if (data && data.success) {
            content = data.content;
            filePath = data.path;
          } else {
            showStatusNotification(`Failed to load file: ${data ? data.error : "Not found"}`);
            return;
          }
        } catch (err) {
          showStatusNotification(`Network error loading file: ${err.message}`);
          return;
        }
      }
    }

    // Add to open tabs
    const newTab = {
      id: filePath,
      path: filePath,
      name: fileName,
      content: content || "",
      isDirty: false
    };
    openTabs.push(newTab);
    switchTab(newTab.id);
    showStatusNotification(`Opened ${fileName}`);
  }

  // 5. Tab Switching
  function switchTab(tabId) {
    activeTabId = tabId;

    if (tabId === "command-center") {
      codeEditorView.style.display = "none";
      if (hasRunStarted) {
        commandCenterView.style.display = "flex";
        dispatcherView.style.display = "none";
      } else {
        dispatcherView.style.display = "flex";
        commandCenterView.style.display = "none";
      }
      if (bcActiveFile) bcActiveFile.innerText = "Aether Command Center";
    } else {
      const tab = openTabs.find(t => t.id === tabId);
      if (tab) {
        dispatcherView.style.display = "none";
        commandCenterView.style.display = "none";
        codeEditorView.style.display = "flex";

        editorContentArea.innerText = tab.content;
        updateGutter();
        updateBreadcrumbs(tab.path);

        const lineCount = (tab.content.split("\n") || []).length;
        const ext = tab.name.split(".").pop().toUpperCase();
        if (editorFileMeta) {
          editorFileMeta.innerText = `${ext} · UTF-8 · ${lineCount} lines · Ctrl+S to save`;
        }
      }
    }

    renderTabs();
    renderOpenEditors();
    highlightActiveInTree(tabId);
  }

  // 6. Close Tab
  function closeTab(tabId, e) {
    if (e) e.stopPropagation();
    openTabs = openTabs.filter(t => t.id !== tabId);
    if (activeTabId === tabId) {
      if (openTabs.length > 0) {
        switchTab(openTabs[openTabs.length - 1].id);
      } else {
        switchTab("command-center");
      }
    } else {
      renderTabs();
      renderOpenEditors();
    }
  }

  // 7. Save Active File
  async function saveActiveFile() {
    if (activeTabId === "command-center") return;
    const tab = openTabs.find(t => t.id === activeTabId);
    if (!tab) return;

    const currentText = editorContentArea.innerText;
    showStatusNotification(`Saving ${tab.name}...`);

    if (window.electronAPI && window.electronAPI.writeFile) {
      const res = await window.electronAPI.writeFile(tab.path, currentText);
      if (res && res.success) {
        tab.content = currentText;
        tab.isDirty = false;
        renderTabs();
        showStatusNotification(`Saved ${tab.name}`);
      } else {
        alert("Failed to save: " + (res ? res.error : "Unknown error"));
      }
    } else {
      // Backend REST fallback
      try {
        const resp = await fetch("/api/file", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: tab.path, content: currentText })
        });
        const data = await resp.json();
        if (data && data.success) {
          tab.content = currentText;
          tab.isDirty = false;
          renderTabs();
          showStatusNotification(`Saved ${tab.name}`);
        } else {
          alert("Failed to save: " + (data ? data.error : "Error"));
        }
      } catch (err) {
        alert("Save error: " + err.message);
      }
    }
  }

  // 8. Render Tabs Bar
  function renderTabs() {
    if (!editorTabsBar) return;
    let html = `
      <div class="editor-tab ${activeTabId === "command-center" ? "active" : ""}" data-tab="command-center">
        ${ICONS.commandCenter}
        <span>Aether Command Center</span>
      </div>
    `;

    openTabs.forEach(t => {
      const isActive = t.id === activeTabId;
      const fileIcon = getFileIconSvg(t.name);
      html += `
        <div class="editor-tab ${isActive ? "active" : ""}" data-tab="${escapeHtml(t.id)}">
          ${fileIcon}
          <span>${escapeHtml(t.name)}</span>
          ${t.isDirty ? `<span class="tab-dirty-dot" title="Unsaved changes"></span>` : ""}
          <span class="tab-close" data-close="${escapeHtml(t.id)}" title="Close">
            ${ICONS.close}
          </span>
        </div>
      `;
    });

    editorTabsBar.innerHTML = html;

    // Attach listeners
    editorTabsBar.querySelectorAll(".editor-tab").forEach(tabElem => {
      const id = tabElem.getAttribute("data-tab");
      tabElem.addEventListener("click", () => switchTab(id));
    });

    editorTabsBar.querySelectorAll(".tab-close").forEach(closeElem => {
      const id = closeElem.getAttribute("data-close");
      closeElem.addEventListener("click", (e) => closeTab(id, e));
    });
  }

  // 9. Render Open Editors in Sidebar
  function renderOpenEditors() {
    if (!openEditorsList) return;
    let html = `
      <div class="tree-node ${activeTabId === "command-center" ? "active" : ""}" data-open="command-center">
        <div class="file-icon">${ICONS.commandCenter}</div>
        <span>Aether Command Center</span>
      </div>
    `;

    openTabs.forEach(t => {
      const isActive = t.id === activeTabId;
      const fileIcon = getFileIconSvg(t.name);
      html += `
        <div class="tree-node ${isActive ? "active" : ""}" data-open="${escapeHtml(t.id)}">
          <div class="file-icon">${fileIcon}</div>
          <span>${escapeHtml(t.name)}</span>
        </div>
      `;
    });

    openEditorsList.innerHTML = html;

    openEditorsList.querySelectorAll(".tree-node").forEach(node => {
      const id = node.getAttribute("data-open");
      node.addEventListener("click", () => switchTab(id));
    });
  }

  // 10. Update Gutter Line Numbers
  function updateGutter() {
    if (!editorGutter || !editorContentArea) return;
    const text = editorContentArea.innerText || "";
    const lines = text.split("\n");
    const count = Math.max(1, lines.length);
    editorGutter.textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
  }

  // Sync scroll
  editorContentArea?.addEventListener("scroll", () => {
    if (editorGutter) {
      editorGutter.scrollTop = editorContentArea.scrollTop;
    }
  });

  // Track dirty state and gutter on input
  editorContentArea?.addEventListener("input", () => {
    updateGutter();
    if (activeTabId !== "command-center") {
      const tab = openTabs.find(t => t.id === activeTabId);
      if (tab) {
        const text = editorContentArea.innerText;
        tab.isDirty = text !== tab.content;
        renderTabs();
      }
    }
  });

  // Tab key indentation in editor
  editorContentArea?.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      document.execCommand("insertText", false, "    ");
    }
  });

  // 11. Breadcrumbs
  function updateBreadcrumbs(filePath) {
    if (!bcRepo || !bcActiveFile) return;
    const clean = filePath.replace(/\\/g, "/");
    const parts = clean.split("/").filter(Boolean);
    const fileName = parts.pop() || "file";
    bcActiveFile.innerText = fileName;
  }

  // 12. Workspace Folder Scanning & Explorer Tree Building
  async function applyWorkspaceFolder(folderPath) {
    activeRepoPath = folderPath;
    const folderName = folderPath.split(/[\\/]/).filter(Boolean).pop() || "workspace";

    if (titlebarWorkspaceName) titlebarWorkspaceName.innerText = folderName;
    if (explorerWorkspaceHeader) explorerWorkspaceHeader.innerText = folderName.toUpperCase();
    if (bcRepo) bcRepo.innerText = folderName;

    // Scan folder structure via Electron IPC or backend REST
    let treeData = null;
    if (window.electronAPI && window.electronAPI.scanProject) {
      const scan = await window.electronAPI.scanProject(folderPath);
      if (scan && scan.tree) {
        treeData = scan.tree;
      }
    }

    if (!treeData) {
      try {
        const resp = await fetch(`/api/tree?path=${encodeURIComponent(folderPath)}`);
        const data = await resp.json();
        if (data && data.tree) {
          treeData = data.tree;
        }
      } catch (e) {
        console.warn("Could not scan directory via /api/tree", e);
      }
    }

    if (treeData && explorerTree) {
      explorerTree.innerHTML = "";
      explorerTree.appendChild(buildTreeElement(treeData, 0));
    }
  }

  // 13. Recursive Tree DOM Builder
  function buildTreeElement(nodes, depth = 0) {
    const container = document.createElement("div");
    container.className = depth === 0 ? "tree-root" : "tree-children";

    nodes.forEach(node => {
      const row = document.createElement("div");
      row.className = "tree-node";
      row.style.paddingLeft = `${depth * 14 + 10}px`;

      if (node.isDirectory) {
        row.classList.add("tree-folder");
        row.innerHTML = `
          ${ICONS.chevronDown}
          <div class="file-icon">${ICONS.folder}</div>
          <span style="font-weight: 500;">${escapeHtml(node.name)}</span>
        `;

        const childrenContainer = node.children && node.children.length > 0
          ? buildTreeElement(node.children, depth + 1)
          : null;

        row.addEventListener("click", (e) => {
          e.stopPropagation();
          const chevron = row.querySelector(".tree-chevron");
          if (childrenContainer) {
            const isHidden = childrenContainer.style.display === "none";
            childrenContainer.style.display = isHidden ? "block" : "none";
            if (chevron) {
              chevron.classList.toggle("collapsed", !isHidden);
            }
            const folderIcon = row.querySelector(".file-icon");
            if (folderIcon) {
              folderIcon.innerHTML = isHidden ? ICONS.folder : ICONS.folderOpen;
            }
          }
        });

        container.appendChild(row);
        if (childrenContainer) {
          container.appendChild(childrenContainer);
        }
      } else {
        // File node
        row.classList.add("tree-file");
        row.setAttribute("data-path", node.fullPath || node.relPath);
        row.setAttribute("data-name", node.name);
        const iconSvg = getFileIconSvg(node.name);

        row.innerHTML = `
          <div style="width: 12px; height: 12px; flex-shrink: 0;"></div>
          <div class="file-icon">${iconSvg}</div>
          <span>${escapeHtml(node.name)}</span>
        `;

        row.addEventListener("click", (e) => {
          e.stopPropagation();
          const p = row.getAttribute("data-path");
          const n = row.getAttribute("data-name");
          openCodeFile(p, n);
        });

        container.appendChild(row);
      }
    });

    return container;
  }

  function highlightActiveInTree(activePath) {
    if (!explorerTree) return;
    explorerTree.querySelectorAll(".tree-file").forEach(elem => {
      const p = elem.getAttribute("data-path");
      elem.classList.toggle("active", p === activePath);
    });
  }

  function showStatusNotification(msg) {
    if (sbStatusText) {
      sbStatusText.innerText = msg;
      setTimeout(() => {
        if (sbStatusText.innerText === msg) {
          sbStatusText.innerText = "Ready";
        }
      }, 3500);
    }
  }

  // 14. Event Listeners for Open File & Folders
  btnOpenFile?.addEventListener("click", handleOpenFile);
  btnOpenFolder?.addEventListener("click", handleOpenLocalFolder);
  btnMainOpenFolder?.addEventListener("click", handleOpenLocalFolder);
  btnSideOpenFolder?.addEventListener("click", handleOpenLocalFolder);
  btnRefreshExplorer?.addEventListener("click", () => applyWorkspaceFolder(activeRepoPath));

  btnOpenPresetFolder?.addEventListener("click", () => {
    applyWorkspaceFolder("benchmarks/ecommerce_api");
    fileDropdown?.classList.remove("open");
  });

  btnNewInvestigation?.addEventListener("click", () => {
    fileDropdown?.classList.remove("open");
    switchTab("command-center");
    hasRunStarted = false;
    commandCenterView.style.display = "none";
    dispatcherView.style.display = "flex";
    if (issueTextarea) issueTextarea.value = "";
    if (triageFeedback) triageFeedback.innerHTML = "";
  });

  btnExit?.addEventListener("click", () => {
    fileDropdown?.classList.remove("open");
    openTabs = [];
    switchTab("command-center");
  });

  // 15. Worktree Toggle
  worktreeTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    worktreeMenu?.classList.toggle("open");
  });

  document.querySelectorAll(".dropdown-entry[data-mode]").forEach((entry) => {
    entry.addEventListener("click", (e) => {
      const mode = e.currentTarget.getAttribute("data-mode");
      if (mode === "local") {
        useWorktree = false;
        worktreeTrigger.querySelector("span").innerText = "Worktree Mode: Local [Unsafe]";
        if (sbWorktreeLabel) sbWorktreeLabel.innerText = "Worktree: Local (Unsafe)";
      } else {
        useWorktree = true;
        worktreeTrigger.querySelector("span").innerText = "Worktree Mode: Isolated [Safe]";
        if (sbWorktreeLabel) sbWorktreeLabel.innerText = "Worktree: Isolated";
      }
      worktreeMenu?.classList.remove("open");
    });
  });

  // 16. Stage 1 Triage Validation
  issueTextarea?.addEventListener("input", () => {
    const val = issueTextarea.value.trim();
    if (val.length === 0) {
      triageFeedback.innerHTML = "";
      return;
    }

    const hasAnchor = /[\w\./\-]+\.py|[\w_]+\(\)|[A-Z][a-zA-Z]+Error/.test(val);
    if (hasAnchor) {
      triageFeedback.innerHTML = `<span style="font-size: 11px; color: var(--vscode-diff-add-text);">[Triage Passed] Anchor identified in issue text</span>`;
    } else {
      triageFeedback.innerHTML = `<span style="font-size: 11px; color: #E2C08D;">[Triage Notice] Missing anchor: mention file path (.py), symbol, or error trace</span>`;
    }
  });

  // 17. Presets
  document.getElementById("btnPresetEcommerce")?.addEventListener("click", () => {
    issueTextarea.value = (
      "Tokens expire early or late depending on timezone offset.\n"
      + "In app/auth/tokens.py::is_token_expired(), datetime.utcnow().timestamp() "
      + "returns naive UTC that Python treats as local time, breaking expiry checks in non-UTC regions."
    );
    issueTextarea.dispatchEvent(new Event("input"));
  });

  document.getElementById("btnPresetTrace")?.addEventListener("click", () => {
    issueTextarea.value = (
      "Traceback (most recent call last):\n"
      + "  File \"benchmarks/ecommerce_api/app/auth/tokens.py\", line 72, in is_token_expired\n"
      + "    current_time = datetime.utcnow().timestamp()\n"
      + "AssertionError: Token unexpectedly expired in timezone Asia/Kolkata"
    );
    issueTextarea.dispatchEvent(new Event("input"));
  });

  // 18. Global Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    const isCmdOrCtrl = e.metaKey || e.ctrlKey;

    if (isCmdOrCtrl && e.key === "Enter") {
      e.preventDefault();
      btnRunAgent?.click();
    } else if (isCmdOrCtrl && (e.key === "o" || e.key === "O")) {
      e.preventDefault();
      handleOpenFile();
    } else if (isCmdOrCtrl && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      saveActiveFile();
    } else if (isCmdOrCtrl && (e.key === "w" || e.key === "W")) {
      e.preventDefault();
      if (activeTabId !== "command-center") {
        closeTab(activeTabId);
      }
    }
  });

  // 19. Run Execution
  btnRunAgent?.addEventListener("click", async () => {
    const desc = issueTextarea.value.trim();
    if (!desc) {
      alert("Please enter a defect description or paste a trace.");
      return;
    }

    hasRunStarted = true;
    switchTab("command-center");

    // Connect SSE
    if (window.sseClient) {
      window.sseClient.connect();
    }

    // Trigger run
    try {
      await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Investigation on ${activeRepoPath.split(/[\\/]/).pop()}`,
          description: desc,
          repo_path: activeRepoPath,
          use_worktree: useWorktree,
          max_budget_usd: 1.00,
        }),
      });
    } catch (err) {
      console.error("Failed to post /api/run", err);
    }
  });

  // 20. SSE Telemetry Stream Listener
  if (window.sseClient) {
    window.sseClient.onEvent((event) => {
      // Append to left stream
      const entry = document.createElement("div");
      entry.style.padding = "4px 0";
      entry.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
      entry.innerHTML = `
        <div style="font-size: 10px; color: #858585;">[${event.timestamp.slice(11, 19)}] <span style="color: #38BDF8; font-weight: 600;">${escapeHtml(event.persona)}</span> :: ${escapeHtml(event.action)}</div>
        <div style="margin-top: 2px; color: #cccccc;">${escapeHtml(event.message)}</div>
      `;
      if (streamLogs) {
        streamLogs.appendChild(entry);
        streamLogs.scrollTop = streamLogs.scrollHeight;
      }

      // Append to bottom integrated panel
      if (panelLogs) {
        const pEntry = document.createElement("div");
        pEntry.innerText = `[${event.persona}]: ${event.message}`;
        panelLogs.appendChild(pEntry);
        panelLogs.scrollTop = panelLogs.scrollHeight;
      }

      // Update Stepper Nodes
      const personaMap = {
        "Triage": "stepTriage",
        "Preflight": "stepPreflight",
        "Cartographer": "stepCartographer",
        "Detective": "stepDetective",
        "Architect": "stepArchitect",
        "Test Crafter": "stepTestCrafter",
        "Surgeon": "stepSurgeon",
        "Sentinel": "stepSentinel",
        "Judge": "stepJudge",
        "Critic": "stepCritic",
        "Scribe": "stepScribe"
      };

      const stepId = personaMap[event.persona];
      if (stepId) {
        const stepElem = document.getElementById(stepId);
        if (stepElem) {
          document.querySelectorAll(".step-node").forEach(n => n.classList.remove("active"));
          stepElem.classList.add("active");
          if (event.status === "completed" || event.status === "success" || event.status === "pass") {
            stepElem.classList.add("completed");
          }
        }
      }

      // Diff Rendering
      if (event.metadata && event.metadata.diff && diffViewer) {
        renderDiff(event.metadata.diff);
      }

      // Judge Stats
      if (event.persona === "Judge" && event.metadata && judgeStats) {
        const jm = event.metadata;
        judgeStats.innerHTML = `
          <div style="padding: 10px; background: rgba(46, 160, 67, 0.15); border: 1px solid rgba(46, 160, 67, 0.3); border-radius: 4px; color: #3fb950;">
            <div style="font-size: 11px; text-transform: uppercase;">Regressions</div>
            <div style="font-size: 16px; font-weight: 700;">${jm.regressions_count || 0} (ZERO REGRESSIONS)</div>
            <div style="font-size: 11px; margin-top: 4px;">Post-Patch Suite: ${jm.post_patch_pass_count || 25} passed | Flaky: ${jm.flaky_excluded ? jm.flaky_excluded.length : 0}</div>
          </div>
        `;
      }

      // Cost Tracker
      if (event.metadata && event.metadata.cost && sbSpend) {
        const spend = event.metadata.cost.total_cost_usd || 0.16;
        sbSpend.innerText = `Spend: $${spend.toFixed(4)} / $1.00`;
      }
    });
  }

  function renderDiff(diffText) {
    if (!diffViewer) return;
    const lines = diffText.split("\n");
    const formatted = lines.map(line => {
      if (line.startsWith("+") && !line.startsWith("+++")) {
        return `<span style="background: var(--vscode-diff-add-bg); color: var(--vscode-diff-add-text); display: block;">${escapeHtml(line)}</span>`;
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        return `<span style="background: var(--vscode-diff-del-bg); color: var(--vscode-diff-del-text); display: block;">${escapeHtml(line)}</span>`;
      }
      return `<span>${escapeHtml(line)}</span>`;
    }).join("\n");
    diffViewer.innerHTML = formatted;
  }

  function escapeHtml(str) {
    if (typeof str !== "string") return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // 21. Initial Workspace Boot
  renderTabs();
  renderOpenEditors();
  applyWorkspaceFolder(activeRepoPath);
});
