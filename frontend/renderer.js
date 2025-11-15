/**
 * Renderer Process - UI Logic
 * Handles user interactions and communicates with backend via IPC
 */

const { ipcRenderer } = require('electron');
const { shell } = require('electron');

// UI Elements
const selectFolderBtn = document.getElementById('select-folder-btn');
const quickIndexBtn = document.getElementById('quick-index-btn');
const clearIndexBtn = document.getElementById('clear-index-btn');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const resultsTitle = document.getElementById('results-title');
const resultsCount = document.getElementById('results-count');
const backendStatus = document.getElementById('backend-status');
const indexStatus = document.getElementById('index-status');
const indexProgress = document.getElementById('index-progress');
const progressText = document.getElementById('progress-text');
const progressStats = document.getElementById('progress-stats');
const progressFill = document.getElementById('progress-fill');
const searchHelp = document.getElementById('search-help');

// State
let isIndexing = false;
let isSearching = false;

// Initialize
init();

async function init() {
    await checkBackendStatus();
    await updateIndexStatus();

    // Set up event listeners
    selectFolderBtn.addEventListener('click', handleSelectFolder);
    quickIndexBtn.addEventListener('click', handleQuickIndex);
    clearIndexBtn.addEventListener('click', handleClearIndex);
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Check backend status periodically
    setInterval(checkBackendStatus, 5000);
}

async function checkBackendStatus() {
    try {
        const result = await ipcRenderer.invoke('check-backend');
        if (result.connected) {
            updateBackendStatus(true);
        } else {
            updateBackendStatus(false);
        }
    } catch (error) {
        updateBackendStatus(false);
    }
}

function updateBackendStatus(connected) {
    const dot = backendStatus.querySelector('.dot');
    if (connected) {
        backendStatus.innerHTML = '<span class="dot online"></span> Backend Connected';
        enableUI();
    } else {
        backendStatus.innerHTML = '<span class="dot offline"></span> Backend Offline - Start Python server';
        disableUI();
    }
}

async function updateIndexStatus() {
    try {
        const status = await ipcRenderer.invoke('get-status');
        const count = status.indexed_files || 0;
        if (count > 0) {
            indexStatus.textContent = `${count} files indexed`;
        } else {
            indexStatus.textContent = 'No files indexed';
        }
    } catch (error) {
        console.error('Error getting status:', error);
    }
}

function enableUI() {
    selectFolderBtn.disabled = false;
    quickIndexBtn.disabled = false;
    clearIndexBtn.disabled = false;
    searchBtn.disabled = false;
    searchInput.disabled = false;
}

function disableUI() {
    selectFolderBtn.disabled = true;
    quickIndexBtn.disabled = true;
    clearIndexBtn.disabled = true;
    searchBtn.disabled = true;
    searchInput.disabled = true;
}

async function handleSelectFolder() {
    const path = await ipcRenderer.invoke('select-directory');
    if (path) {
        await indexFiles(path);
    }
}

async function handleQuickIndex() {
    const userProfile = process.env.USERPROFILE || process.env.HOME;
    const desktopPath = `${userProfile}\\Desktop`;
    await indexFiles(desktopPath);
}

async function indexFiles(path) {
    if (isIndexing) return;

    isIndexing = true;
    selectFolderBtn.disabled = true;
    quickIndexBtn.disabled = true;

    // Show progress
    indexProgress.classList.remove('hidden');
    progressText.textContent = 'Indexing files...';
    progressStats.textContent = '';
    progressFill.style.width = '50%';

    try {
        const result = await ipcRenderer.invoke('index-files', path, false);

        progressText.textContent = 'Indexing complete!';
        progressStats.textContent = `${result.files_indexed} files indexed (${result.skipped} skipped, ${result.total_files} total)`;
        progressFill.style.width = '100%';

        await updateIndexStatus();

        setTimeout(() => {
            indexProgress.classList.add('hidden');
        }, 3000);

    } catch (error) {
        progressText.textContent = 'Error indexing files';
        progressStats.textContent = error.message;
        progressFill.style.width = '0%';
        alert(`Error: ${error.message}`);
    } finally {
        isIndexing = false;
        selectFolderBtn.disabled = false;
        quickIndexBtn.disabled = false;
    }
}

async function handleClearIndex() {
    if (!confirm('Are you sure you want to clear the index? This will remove all indexed files.')) {
        return;
    }

    try {
        await ipcRenderer.invoke('clear-index');
        await updateIndexStatus();
        resultsSection.classList.add('hidden');
        alert('Index cleared successfully');
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function handleSearch() {
    const query = searchInput.value.trim();

    if (!query) {
        alert('Please enter a search query');
        return;
    }

    if (isSearching) return;

    isSearching = true;
    searchBtn.textContent = 'Searching...';
    searchBtn.disabled = true;

    // Hide help text
    searchHelp.classList.add('hidden');

    try {
        const results = await ipcRenderer.invoke('search-files', query, 20);

        displayResults(query, results);

    } catch (error) {
        alert(`Error: ${error.message}\n\nMake sure you've indexed some files first!`);
    } finally {
        isSearching = false;
        searchBtn.textContent = 'Search';
        searchBtn.disabled = false;
    }
}

function displayResults(query, results) {
    resultsSection.classList.remove('hidden');
    resultsTitle.textContent = `Results for "${query}"`;
    resultsCount.textContent = `${results.length} files found`;

    resultsContainer.innerHTML = '';

    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <p>No results found</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem;">Try a different search term or index more files</p>
            </div>
        `;
        return;
    }

    results.forEach(result => {
        const resultElement = createResultElement(result);
        resultsContainer.appendChild(resultElement);
    });
}

function createResultElement(result) {
    const div = document.createElement('div');
    div.className = 'result-item';

    const scorePercent = Math.round(result.similarity_score * 100);

    // Show if filename match boosted the score
    const filenameMatch = result.filename_boost > 0;
    const matchBadge = filenameMatch ? '<span style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem;">Filename Match</span>' : '';

    div.innerHTML = `
        <div class="result-header">
            <div>
                <div class="result-name">${escapeHtml(result.file_name)}${matchBadge}</div>
                <div class="result-path">${escapeHtml(result.file_path)}</div>
            </div>
            <div class="result-type">${result.file_type || 'file'}</div>
        </div>
        ${result.preview ? `<div class="result-preview">${escapeHtml(result.preview)}</div>` : ''}
        <div style="margin-top: 0.75rem;">
            <div class="similarity-score">
                <span>Match Score:</span>
                <div class="score-bar">
                    <div class="score-fill" style="width: ${scorePercent}%"></div>
                </div>
                <span>${scorePercent}%</span>
            </div>
        </div>
    `;

    // Open file on click
    div.addEventListener('click', () => {
        shell.openPath(result.file_path);
    });

    return div;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
