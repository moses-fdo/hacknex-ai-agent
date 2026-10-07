const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const http = require("http");
const { spawn } = require("child_process");

let mainWindow = null;
let backendProcess = null;
const RECENT_FILE = path.join(app.getPath("userData"), "recent_projects.json");

function getRecentProjects() {
  try {
    if (fs.existsSync(RECENT_FILE)) {
      return JSON.parse(fs.readFileSync(RECENT_FILE, "utf-8"));
    }
  } catch (e) {
    // fallback
  }
  return [path.resolve(__dirname, "benchmarks/ecommerce_api")];
}

function saveRecentProject(folderPath) {
  try {
    let recents = getRecentProjects();
    recents = [folderPath, ...recents.filter((p) => p !== folderPath)].slice(0, 10);
    fs.writeFileSync(RECENT_FILE, JSON.stringify(recents, null, 2), "utf-8");
  } catch (e) {
    console.error("Failed to save recent project", e);
  }
}

function startBackend() {
  const venvPython = path.resolve(__dirname, ".venv/bin/uvicorn");
  const pythonPath = fs.existsSync(venvPython) ? venvPython : "uvicorn";

  console.log("Starting Python FastAPI backend process...");
  backendProcess = spawn(
    pythonPath,
    ["backend.api.server:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: __dirname,
      env: {
        ...process.env,
        PYTHONPATH: `${__dirname}:${path.resolve(__dirname, "benchmarks/ecommerce_api")}`,
      },
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Backend]: ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[Backend ERR]: ${data}`);
  });

  backendProcess.on("close", (code) => {
    console.log(`Backend process exited with code ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 1000,
    minHeight: 640,
    title: "Aether-SWE Studio",
    backgroundColor: "#1e1e1e",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the frontend UI once the backend is ready
  const appUrl = "http://127.0.0.1:8000";

  function tryLoad(retries = 20) {
    http.get(`${appUrl}/api/status`, (res) => {
      if (res.statusCode === 200) {
        mainWindow.loadURL(appUrl);
      } else if (retries > 0) {
        setTimeout(() => tryLoad(retries - 1), 300);
      } else {
        mainWindow.loadURL(appUrl);
      }
    }).on("error", () => {
      if (retries > 0) {
        setTimeout(() => tryLoad(retries - 1), 300);
      } else {
        mainWindow.loadFile(path.join(__dirname, "frontend/index.html"));
      }
    });
  }

  tryLoad();

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// IPC Handlers: Folder Picker
ipcMain.handle("dialog:openDirectory", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select Repository or Project Folder",
    properties: ["openDirectory"],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const selectedPath = result.filePaths[0];
  saveRecentProject(selectedPath);
  return selectedPath;
});

// IPC Handler: File Picker
ipcMain.handle("dialog:openFile", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Open Code File",
    properties: ["openFile"],
    filters: [
      { name: "Code & Text Files", extensions: ["py", "js", "html", "css", "json", "md", "txt", "sh", "yml", "yaml", "toml"] },
      { name: "All Files", extensions: ["*"] }
    ]
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const selectedPath = result.filePaths[0];
  try {
    const content = fs.readFileSync(selectedPath, "utf-8");
    return {
      success: true,
      path: selectedPath,
      name: path.basename(selectedPath),
      content
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// IPC Handler: Read File
ipcMain.handle("fs:readFile", async (event, filePath) => {
  try {
    let target = filePath;
    if (!fs.existsSync(target)) {
      const candidates = [
        path.resolve(__dirname, filePath),
        path.resolve(__dirname, "benchmarks/ecommerce_api", filePath),
      ];
      for (const cand of candidates) {
        if (fs.existsSync(cand)) {
          target = cand;
          break;
        }
      }
    }
    if (!fs.existsSync(target)) {
      return { success: false, error: `File not found: ${filePath}` };
    }
    const content = fs.readFileSync(target, "utf-8");
    return {
      success: true,
      path: target,
      name: path.basename(target),
      content
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// IPC Handler: Write File
ipcMain.handle("fs:writeFile", async (event, filePath, content) => {
  try {
    let target = filePath;
    if (!path.isAbsolute(target)) {
      target = path.resolve(__dirname, filePath);
    }
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf-8");
    return { success: true, path: target };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

// Recursive tree builder
function readDirRecursive(dirPath, rootPath, depth = 0, maxDepth = 4) {
  if (depth > maxDepth) return [];
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    entries.sort((a, b) => {
      if (a.isDirectory() && !b.isDirectory()) return -1;
      if (!a.isDirectory() && b.isDirectory()) return 1;
      return a.name.localeCompare(b.name);
    });
    const list = [];
    for (const ent of entries) {
      if (ent.name.startsWith(".") || ent.name === "__pycache__" || ent.name === "node_modules" || ent.name === ".venv") {
        continue;
      }
      const fullPath = path.join(dirPath, ent.name);
      const relPath = path.relative(rootPath, fullPath);
      const isDir = ent.isDirectory();
      list.push({
        name: ent.name,
        relPath,
        fullPath,
        isDirectory: isDir,
        children: isDir ? readDirRecursive(fullPath, rootPath, depth + 1, maxDepth) : []
      });
    }
    return list;
  } catch (e) {
    return [];
  }
}

// IPC Handler: Scan Project
ipcMain.handle("fs:scanProject", async (event, folderPath) => {
  try {
    if (!fs.existsSync(folderPath)) {
      return { error: "Folder does not exist" };
    }
    const tree = readDirRecursive(folderPath, folderPath);
    return {
      path: folderPath,
      name: path.basename(folderPath),
      hasGit: fs.existsSync(path.join(folderPath, ".git")),
      hasTests: fs.existsSync(path.join(folderPath, "tests")),
      tree
    };
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle("fs:getRecentProjects", async () => {
  return getRecentProjects();
});

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill("SIGTERM");
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  if (backendProcess) {
    backendProcess.kill("SIGTERM");
  }
});
