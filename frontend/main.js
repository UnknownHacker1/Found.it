/**
 * Electron Main Process
 * Handles window creation and native OS integration
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const axios = require('axios');

const API_URL = 'http://127.0.0.1:8001';

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    backgroundColor: '#1a1a1a',
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#1a1a1a',
      symbolColor: '#ffffff'
    }
  });

  // Start with login page
  mainWindow.loadFile('login.html');

  // Open DevTools in development
  // mainWindow.webContents.openDevTools();
}

app.whenReady().then(() => {
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC Handlers for backend communication

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('index-files', async (event, path, forceReindex = false) => {
  try {
    // Start indexing (this will run async on backend)
    const indexPromise = axios.post(`${API_URL}/index`, {
      path: path,
      force_reindex: forceReindex
    });

    // Poll for progress updates - more frequently for smooth progress bar
    const pollProgress = setInterval(async () => {
      try {
        const progressResponse = await axios.get(`${API_URL}/index-progress`);
        event.sender.send('index-progress-update', progressResponse.data);
      } catch (error) {
        // Ignore polling errors
      }
    }, 200); // Poll every 200ms for smoother updates

    // Wait for indexing to complete
    const response = await indexPromise;

    // Stop polling
    clearInterval(pollProgress);

    // Send final 100% update
    event.sender.send('index-progress-update', { percentage: 100, status: 'complete' });

    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('search-files', async (event, query, topK = 10) => {
  try {
    const response = await axios.post(`${API_URL}/search`, {
      query: query,
      top_k: topK
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('get-status', async () => {
  try {
    const response = await axios.get(`${API_URL}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('clear-index', async () => {
  try {
    const response = await axios.post(`${API_URL}/clear-index`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('check-backend', async () => {
  try {
    const response = await axios.get(`${API_URL}/`, { timeout: 10000 });
    return { connected: true, data: response.data };
  } catch (error) {
    return { connected: false, error: error.message };
  }
});

ipcMain.handle('chat-with-ai', async (event, message, maxResults = 5) => {
  try {
    const response = await axios.post(`${API_URL}/chat`, {
      query: message,
      top_k: maxResults
    }, {
      timeout: 60000 // 60 second timeout for LLM responses
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('summarize-file', async (event, filePath) => {
  try {
    const response = await axios.post(`${API_URL}/summarize-file`, {
      file_path: filePath
    }, {
      timeout: 60000 // 60 second timeout for summary generation
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('clear-conversation', async () => {
  try {
    const response = await axios.post(`${API_URL}/clear-conversation`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});

ipcMain.handle('show-in-folder', async (event, filePath) => {
  shell.showItemInFolder(filePath);
});

ipcMain.handle('open-file', async (event, filePath) => {
  await shell.openPath(filePath);
});

ipcMain.handle('cancel-index', async () => {
  try {
    const response = await axios.post(`${API_URL}/cancel-index`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
});
