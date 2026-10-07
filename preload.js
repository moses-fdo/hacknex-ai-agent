/**
 * Preload script exposing secure local filesystem access, dialogs, and file reading/writing.
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  isElectron: true,

  // Open native OS folder picker
  selectDirectory: async () => {
    return await ipcRenderer.invoke("dialog:openDirectory");
  },

  // Open native OS file picker
  selectFile: async () => {
    return await ipcRenderer.invoke("dialog:openFile");
  },

  // Read code file content from disk
  readFile: async (filePath) => {
    return await ipcRenderer.invoke("fs:readFile", filePath);
  },

  // Write/save code file content to disk
  writeFile: async (filePath, content) => {
    return await ipcRenderer.invoke("fs:writeFile", filePath, content);
  },

  // Scan files and recursive directory structure of a project folder
  scanProject: async (folderPath) => {
    return await ipcRenderer.invoke("fs:scanProject", folderPath);
  },

  // Get recently accessed local project folders
  getRecentProjects: async () => {
    return await ipcRenderer.invoke("fs:getRecentProjects");
  }
});
