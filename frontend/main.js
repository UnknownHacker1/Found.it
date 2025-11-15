/**
 * Electron Main Process
 * Handles window creation and native OS integration
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
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

  mainWindow.loadFile('index-chat.html');

  // Open DevTools in development
  // mainWindow.webContents.openDevTools();
}

app.whenReady().then(createWindow);

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
    const response = await axios.post(`${API_URL}/index`, {
      path: path,
      force_reindex: forceReindex
    });
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
    const response = await axios.get(`${API_URL}/`, { timeout: 2000 });
    return { connected: true, data: response.data };
  } catch (error) {
    return { connected: false, error: error.message };
  }
});

ipcMain.handle('chat-with-ai', async (event, message) => {
  try {
    const response = await axios.post(`${API_URL}/chat`, {
      query: message,
      top_k: 5
    }, {
      timeout: 60000 // 60 second timeout for LLM responses
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
