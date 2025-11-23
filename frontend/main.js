/**
 * Electron Main Process
 * Handles window creation and native OS integration
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');

const API_URL = 'http://127.0.0.1:8001';

let mainWindow;
let backendProcess = null;

async function killExistingBackends() {
  // Kill any existing Python processes on port 8001
  const { exec } = require('child_process');

  return new Promise((resolve) => {
    exec('netstat -ano | findstr :8001', (error, stdout) => {
      if (!stdout) {
        resolve();
        return;
      }

      const lines = stdout.split('\n');
      const pids = new Set();

      for (const line of lines) {
        const match = line.match(/LISTENING\s+(\d+)/);
        if (match) {
          pids.add(match[1]);
        }
      }

      if (pids.size === 0) {
        resolve();
        return;
      }

      console.log('Killing existing backend processes:', Array.from(pids));

      let killed = 0;
      pids.forEach(pid => {
        exec(`taskkill //F //PID ${pid}`, () => {
          killed++;
          if (killed === pids.size) {
            // Wait a bit for ports to be released
            setTimeout(resolve, 1000);
          }
        });
      });
    });
  });
}

function startBackend() {
  // Check if running in production (packaged app)
  const isProd = !process.defaultApp;

  if (isProd) {
    // In production, run Python backend from bundled files
    const backendDir = path.join(process.resourcesPath, 'backend');
    const appPath = path.join(backendDir, 'app.py');

    if (fs.existsSync(appPath)) {
      console.log('Starting bundled backend with Python:', appPath);
      console.log('Backend directory:', backendDir);

      // Try different Python commands (python, python3, py)
      const pythonCommands = ['python', 'python3', 'py'];
      let attempted = 0;

      function tryPythonCommand(cmdIndex) {
        if (cmdIndex >= pythonCommands.length) {
          console.error('Failed to start backend: Python not found. Please install Python 3.10+');
          if (mainWindow) {
            mainWindow.webContents.executeJavaScript(`
              alert('Python not found! Please install Python 3.10 or later and restart the app.');
            `);
          }
          return;
        }

        const pythonCmd = pythonCommands[cmdIndex];
        console.log(`Trying ${pythonCmd}...`);

        backendProcess = spawn(pythonCmd, ['app.py'], {
          cwd: backendDir,
          env: { ...process.env },
          shell: true
        });

        backendProcess.stdout.on('data', (data) => {
          console.log(`Backend: ${data}`);
        });

        backendProcess.stderr.on('data', (data) => {
          console.error(`Backend Error: ${data}`);
        });

        backendProcess.on('error', (err) => {
          console.error(`Failed to start with ${pythonCmd}:`, err.message);
          tryPythonCommand(cmdIndex + 1);
        });

        backendProcess.on('close', (code) => {
          console.log(`Backend process exited with code ${code}`);
          if (code !== 0 && cmdIndex < pythonCommands.length - 1) {
            tryPythonCommand(cmdIndex + 1);
          }
        });
      }

      tryPythonCommand(0);
    } else {
      console.error('Backend app.py not found at:', appPath);
    }
  } else {
    // In development, assume backend is running separately
    console.log('Development mode - backend should be running separately');
  }
}

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

app.whenReady().then(async () => {
  // First, kill any existing backend processes
  await killExistingBackends();

  // Then start fresh backend
  startBackend();

  // Wait a bit for backend to start
  setTimeout(() => {
    createWindow();
  }, 3000); // Increased to 3 seconds to allow cleanup
});

app.on('window-all-closed', () => {
  // Kill backend process when app closes
  if (backendProcess) {
    backendProcess.kill();
  }

  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  // Ensure backend is killed on quit
  if (backendProcess) {
    backendProcess.kill();
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

ipcMain.handle('index-files', async (event, dirPath, forceReindex = false) => {
  try {
    // Validate path
    if (!dirPath) {
      throw new Error('No path provided for indexing');
    }

    // Normalize path for Windows (convert backslashes to forward slashes)
    const normalizedPath = dirPath.replace(/\\/g, '/');
    console.log('Indexing path:', normalizedPath);

    // Start indexing (this will run async on backend)
    const indexPromise = axios.post(`${API_URL}/index`, {
      path: normalizedPath,
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
