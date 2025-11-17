/**
 * Renderer Process - Chat UI Logic
 * Handles conversational interface for AI file assistant
 */

const { ipcRenderer, shell } = require('electron');

// UI Elements
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const backendStatus = document.getElementById('backend-status');
const ragStatus = document.getElementById('rag-status');
const indexStatus = document.getElementById('index-status');
const selectFolderBtn = document.getElementById('select-folder-btn');
const quickIndexBtn = document.getElementById('quick-index-btn');
const clearConversationBtn = document.getElementById('clear-conversation-btn');
const clearIndexBtn = document.getElementById('clear-index-btn');
const indexProgress = document.getElementById('index-progress');
const progressText = document.getElementById('progress-text');
const progressFill = document.getElementById('progress-fill');
const cancelIndexBtn = document.getElementById('cancel-index-btn');
const userInfoDiv = document.getElementById('user-info');
const logoutBtn = document.getElementById('logout-btn');
const themeToggle = document.getElementById('theme-toggle');
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeSettings = document.getElementById('close-settings');
const saveSettings = document.getElementById('save-settings');
const cancelSettings = document.getElementById('cancel-settings');

// State
let isProcessing = false;
let isIndexing = false;
let authToken = null;
let currentUser = null;
let activeFileTypeFilters = []; // Array of selected filter types
let lastSearchResults = [];

// Initialize
init();

async function init() {
    // Check authentication
    checkAuth();

    // Load saved theme
    loadTheme();

    await checkBackendStatus();
    await updateStatus();

    // Event listeners
    sendBtn.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', handleKeyDown);
    chatInput.addEventListener('input', handleInputChange);
    selectFolderBtn.addEventListener('click', handleSelectFolder);
    quickIndexBtn.addEventListener('click', handleQuickIndex);
    clearConversationBtn.addEventListener('click', handleClearConversation);
    clearIndexBtn.addEventListener('click', handleClearIndex);
    cancelIndexBtn.addEventListener('click', handleCancelIndex);
    themeToggle.addEventListener('click', toggleTheme);
    settingsBtn.addEventListener('click', openSettings);
    closeSettings.addEventListener('click', closeSettingsModal);
    cancelSettings.addEventListener('click', closeSettingsModal);
    saveSettings.addEventListener('click', saveSettingsHandler);

    // Auto-resize textarea
    chatInput.addEventListener('input', autoResize);

    // Check status periodically
    setInterval(async () => {
        await checkBackendStatus();
        await updateStatus();
    }, 5000);

    // File type filter dropdown event listeners
    setupFilterDropdown();
}

function autoResize() {
    chatInput.style.height = 'auto';
    chatInput.style.height = chatInput.scrollHeight + 'px';
}

function handleInputChange() {
    const hasText = chatInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isProcessing;
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
}

async function handleSend() {
    const message = chatInput.value.trim();
    if (!message || isProcessing) return;

    // Add user message to chat
    addUserMessage(message);

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    handleInputChange();

    // Show thinking indicator
    const thinkingId = showThinking();

    isProcessing = true;

    try {
        // Get max results from settings
        const maxResults = parseInt(localStorage.getItem('maxResults') || '5');

        // Send to backend
        const response = await ipcRenderer.invoke('chat-with-ai', message, maxResults);

        // Remove thinking indicator
        removeThinking(thinkingId);

        // Store results for filtering
        lastSearchResults = response.files || [];

        // Filter results based on active filters
        const filteredFiles = filterFilesByType(lastSearchResults, activeFileTypeFilters);

        // Add assistant response with filtered files
        addAssistantMessage(response.response, filteredFiles, response.reasoning);

    } catch (error) {
        removeThinking(thinkingId);
        addAssistantMessage(
            `Sorry, I encountered an error: ${error.message}\n\nMake sure files are indexed and the backend is running.`,
            [],
            error.message
        );
    } finally {
        isProcessing = false;
        handleInputChange();
    }
}

function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';

    messageDiv.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <div class="message-text">
                <p>${escapeHtml(text)}</p>
            </div>
            <div class="message-timestamp">${getCurrentTime()}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addAssistantMessage(text, files = [], reasoning = '') {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';

    let filesHTML = '';
    if (files && files.length > 0) {
        filesHTML = '<div class="file-results">';
        files.forEach(file => {
            const scorePercent = Math.round(file.similarity_score * 100);
            filesHTML += `
                <div class="file-result" data-path="${escapeHtml(file.file_path)}">
                    <div class="file-result-header">
                        <div>
                            <div class="file-name">${escapeHtml(file.file_name)}</div>
                            <div class="file-path">${escapeHtml(file.file_path)}</div>
                        </div>
                        <div class="file-actions">
                            <button class="file-action-btn show-folder-btn" title="Show in folder" data-path="${escapeHtml(file.file_path)}">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                                </svg>
                            </button>
                            <button class="file-action-btn summarize-btn" title="Summarize file" data-path="${escapeHtml(file.file_path)}">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"></circle>
                                    <path d="m21 21-4.35-4.35"></path>
                                </svg>
                            </button>
                            <div class="file-type">${file.file_type || 'file'}</div>
                        </div>
                    </div>
                    ${file.preview ? `<div class="file-preview">${escapeHtml(file.preview)}</div>` : ''}
                    <div class="file-summary" style="display: none;"></div>
                </div>
            `;
        });
        filesHTML += '</div>';
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">
                ${formatMessageText(text)}
                ${filesHTML}
            </div>
            <div class="message-timestamp">${getCurrentTime()}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);

    // Add click handlers to file results
    messageDiv.querySelectorAll('.file-result').forEach(el => {
        el.addEventListener('click', async (e) => {
            // Don't open file if clicking action buttons
            if (e.target.closest('.summarize-btn') || e.target.closest('.show-folder-btn')) return;

            const path = el.dataset.path;
            await ipcRenderer.invoke('open-file', path);
        });
    });

    // Add click handler for show in folder button
    messageDiv.querySelectorAll('.show-folder-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const path = btn.dataset.path;
            await ipcRenderer.invoke('show-in-folder', path);
        });
    });

    // Add click handlers to summarize buttons
    messageDiv.querySelectorAll('.summarize-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const filePath = btn.dataset.path;
            const fileCard = btn.closest('.file-result');
            const summaryDiv = fileCard.querySelector('.file-summary');

            // Toggle summary
            if (summaryDiv.style.display === 'block') {
                summaryDiv.style.display = 'none';
                btn.classList.remove('active');
                return;
            }

            // Show loading
            summaryDiv.innerHTML = '<div class="summary-loading">Generating summary...</div>';
            summaryDiv.style.display = 'block';
            btn.classList.add('active');

            try {
                const summary = await ipcRenderer.invoke('summarize-file', filePath);
                summaryDiv.innerHTML = `
                    <div class="summary-header">📄 Summary</div>
                    <div class="summary-text">${escapeHtml(summary.summary)}</div>
                `;
            } catch (error) {
                summaryDiv.innerHTML = `<div class="summary-error">Failed to generate summary: ${error.message}</div>`;
            }
        });
    });

    scrollToBottom();
}

function showThinking() {
    const thinkingId = 'thinking-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.id = thinkingId;

    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">
                <div class="thinking-indicator">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                </div>
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return thinkingId;
}

function removeThinking(thinkingId) {
    const el = document.getElementById(thinkingId);
    if (el) el.remove();
}

function formatMessageText(text) {
    // Convert newlines to paragraphs
    const paragraphs = text.split('\n').filter(p => p.trim());
    return paragraphs.map(p => {
        // Check if it's a list item
        if (p.trim().match(/^[\d]+\./)) {
            return `<p>${escapeHtml(p)}</p>`;
        }
        return `<p>${escapeHtml(p)}</p>`;
    }).join('');
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function checkBackendStatus() {
    try {
        const result = await ipcRenderer.invoke('check-backend');
        if (result.connected) {
            backendStatus.innerHTML = '<span class="dot online"></span> Connected';
        } else {
            backendStatus.innerHTML = '<span class="dot offline"></span> Backend Offline';
        }
    } catch (error) {
        backendStatus.innerHTML = '<span class="dot offline"></span> Backend Offline';
    }
}

async function updateStatus() {
    try {
        const status = await ipcRenderer.invoke('get-status');

        // Index status
        const count = status.indexed_files || 0;
        if (count > 0) {
            indexStatus.textContent = `${count} files indexed`;
        } else {
            indexStatus.textContent = 'No files indexed';
        }

        // RAG status
        if (status.rag_ready) {
            ragStatus.innerHTML = '<span class="dot online"></span> AI: Ready';
            sendBtn.disabled = false;
        } else {
            ragStatus.innerHTML = '<span class="dot offline"></span> AI: Not Ready';
            sendBtn.disabled = true;
        }

    } catch (error) {
        console.error('Error updating status:', error);
    }
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

    indexProgress.classList.remove('hidden');
    progressText.textContent = 'Starting indexing... 0%';
    progressFill.style.width = '0%';

    // Listen for progress updates
    const progressListener = (event, progress) => {
        const percentage = progress.percentage || 0;
        progressFill.style.width = `${percentage}%`;

        if (progress.status === 'cancelled') {
            progressText.textContent = 'Cancelled';
            return;
        }

        if (percentage < 90) {
            progressText.textContent = `Indexing files... ${percentage}%`;
        } else if (percentage < 100) {
            progressText.textContent = `Building embeddings... ${percentage}%`;
        } else {
            progressText.textContent = `Complete! 100%`;
        }
    };

    ipcRenderer.on('index-progress-update', progressListener);

    try {
        const result = await ipcRenderer.invoke('index-files', path, false);

        if (result.status === 'cancelled') {
            progressText.textContent = 'Indexing cancelled';
            progressFill.style.width = '0%';

            addAssistantMessage(
                'Indexing was cancelled.',
                [],
                ''
            );

            setTimeout(() => {
                indexProgress.classList.add('hidden');
            }, 2000);
        } else {
            // Ensure we show 100%
            progressText.textContent = 'Complete! 100%';
            progressFill.style.width = '100%';

            await updateStatus();

            addAssistantMessage(
                `✓ Indexed ${result.files_indexed} files successfully!\n\nStart searching for your files!`,
                [],
                ''
            );

            setTimeout(() => {
                indexProgress.classList.add('hidden');
            }, 3000);
        }

    } catch (error) {
        progressText.textContent = 'Error - indexing failed';
        progressFill.style.width = '0%';
        alert(`Error: ${error.message}`);
    } finally {
        // Remove progress listener
        ipcRenderer.removeListener('index-progress-update', progressListener);

        isIndexing = false;
        selectFolderBtn.disabled = false;
        quickIndexBtn.disabled = false;
    }
}

async function handleCancelIndex() {
    if (!isIndexing) return;

    if (confirm('Are you sure you want to cancel indexing?')) {
        try {
            await ipcRenderer.invoke('cancel-index');
            progressText.textContent = 'Cancelling...';
        } catch (error) {
            console.error('Error cancelling index:', error);
        }
    }
}

async function handleClearConversation() {
    if (!confirm('Clear the conversation history?')) return;

    try {
        await ipcRenderer.invoke('clear-conversation');

        // Clear messages except welcome
        const messages = chatMessages.querySelectorAll('.message');
        messages.forEach((msg, index) => {
            if (index > 0) msg.remove(); // Keep first welcome message
        });

    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function handleClearIndex() {
    if (!confirm('Clear all indexed files? You will need to re-index.')) return;

    try {
        await ipcRenderer.invoke('clear-index');
        await updateStatus();
        addAssistantMessage('Index cleared. Please re-index your files to continue.', [], '');
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== Authentication Functions =====

function checkAuth() {
    // Load auth token and user info from localStorage
    authToken = localStorage.getItem('auth_token');
    const userInfoStr = localStorage.getItem('user_info');
    const guestMode = localStorage.getItem('guest_mode');

    if (authToken && userInfoStr) {
        // User is logged in
        currentUser = JSON.parse(userInfoStr);
        displayUserInfo();
    } else if (guestMode) {
        // Guest mode
        currentUser = { name: 'Guest', email: 'guest@local' };
        displayUserInfo();
    } else {
        // Not logged in, redirect to login page
        window.location.href = 'login.html';
    }

    // Setup logout button
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

function displayUserInfo() {
    if (!userInfoDiv) return;

    if (currentUser) {
        const isGuest = currentUser.name === 'Guest';
        userInfoDiv.innerHTML = `
            <div class="user-profile">
                ${currentUser.picture ?
                    `<img src="${currentUser.picture}" alt="Profile" class="user-avatar">` :
                    `<div class="user-avatar-placeholder">${currentUser.name.charAt(0).toUpperCase()}</div>`
                }
                <div class="user-details">
                    <div class="user-name">${currentUser.name}</div>
                    <div class="user-email">${currentUser.email}</div>
                </div>
                ${!isGuest ? '<button id="logout-btn" class="logout-btn">Logout</button>' : ''}
            </div>
        `;

        // Re-attach logout handler if button was created
        const logoutButton = document.getElementById('logout-btn');
        if (logoutButton) {
            logoutButton.addEventListener('click', handleLogout);
        }
    }
}

async function handleLogout() {
    if (!confirm('Are you sure you want to logout?')) return;

    try {
        // Call logout endpoint if authenticated
        if (authToken) {
            await fetch('http://localhost:8001/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear local storage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        localStorage.removeItem('guest_mode');

        // Redirect to login
        window.location.href = 'login.html';
    }
}

// Add authentication headers to API requests
function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    return headers;
}

// ===== Theme Toggle Functions =====

function loadTheme() {
    const themeMode = localStorage.getItem('themeMode') || 'dark';
    const themeIcon = document.querySelector('.theme-icon');

    if (themeMode === 'auto') {
        applyAutoTheme();
        // Check every minute for time changes
        setInterval(applyAutoTheme, 60000);
    } else if (themeMode === 'light') {
        document.body.classList.add('light-theme');
        themeIcon.textContent = '🌙';
    } else {
        document.body.classList.remove('light-theme');
        themeIcon.textContent = '☀️';
    }
}

function applyAutoTheme() {
    const hour = new Date().getHours();
    const themeIcon = document.querySelector('.theme-icon');

    // Dark mode from 6 PM (18:00) to 6 AM (6:00)
    if (hour >= 18 || hour < 6) {
        document.body.classList.remove('light-theme');
        themeIcon.textContent = '☀️';
    } else {
        document.body.classList.add('light-theme');
        themeIcon.textContent = '🌙';
    }
}

function toggleTheme() {
    const themeIcon = document.querySelector('.theme-icon');
    const currentMode = localStorage.getItem('themeMode') || 'dark';

    if (document.body.classList.contains('light-theme')) {
        // Switch to dark
        document.body.classList.remove('light-theme');
        themeIcon.textContent = '☀️';
        localStorage.setItem('themeMode', 'dark');
    } else {
        // Switch to light
        document.body.classList.add('light-theme');
        themeIcon.textContent = '🌙';
        localStorage.setItem('themeMode', 'light');
    }
}

// ===== Settings Functions =====

function openSettings() {
    settingsModal.classList.remove('hidden');
    loadSettingsValues();
}

function closeSettingsModal() {
    settingsModal.classList.add('hidden');
}

function loadSettingsValues() {
    // Load saved settings
    const themeMode = localStorage.getItem('themeMode') || 'dark';
    const maxResults = localStorage.getItem('maxResults') || '5';
    const showPreviews = localStorage.getItem('showFilePreviews') !== 'false';
    const autoIndex = localStorage.getItem('autoIndex') !== 'false';
    const enableAnimations = localStorage.getItem('enableAnimations') !== 'false';
    const clearOnExit = localStorage.getItem('clearOnExit') === 'true';

    document.getElementById('theme-mode').value = themeMode;
    document.getElementById('max-results').value = maxResults;
    document.getElementById('show-file-previews').checked = showPreviews;
    document.getElementById('auto-index').checked = autoIndex;
    document.getElementById('enable-animations').checked = enableAnimations;
    document.getElementById('clear-on-exit').checked = clearOnExit;
}

function saveSettingsHandler() {
    // Save settings
    const themeMode = document.getElementById('theme-mode').value;
    const maxResults = document.getElementById('max-results').value;
    const showPreviews = document.getElementById('show-file-previews').checked;
    const autoIndex = document.getElementById('auto-index').checked;
    const enableAnimations = document.getElementById('enable-animations').checked;
    const clearOnExit = document.getElementById('clear-on-exit').checked;

    localStorage.setItem('themeMode', themeMode);
    localStorage.setItem('maxResults', maxResults);
    localStorage.setItem('showFilePreviews', showPreviews);
    localStorage.setItem('autoIndex', autoIndex);
    localStorage.setItem('enableAnimations', enableAnimations);
    localStorage.setItem('clearOnExit', clearOnExit);

    // Apply theme change immediately
    loadTheme();

    // Apply animations setting
    if (!enableAnimations) {
        document.body.style.setProperty('--animation-speed', '0s');
    } else {
        document.body.style.removeProperty('--animation-speed');
    }

    closeSettingsModal();

    // Show confirmation
    addAssistantMessage('Settings saved successfully!', [], '');
}

// Click outside modal to close
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        closeSettingsModal();
    }
});

// ===== File Type Filter Functions =====

function setupFilterDropdown() {
    const dropdownBtn = document.getElementById('filter-dropdown-btn');
    const dropdownMenu = document.getElementById('filter-dropdown-menu');
    const filterCheckboxes = document.querySelectorAll('.filter-checkbox');
    const clearBtn = document.getElementById('filter-clear-btn');
    const selectedText = document.getElementById('filter-selected-text');

    // Toggle dropdown
    dropdownBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle('hidden');
        dropdownBtn.classList.toggle('open');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
            dropdownMenu.classList.add('hidden');
            dropdownBtn.classList.remove('open');
        }
    });

    // Handle checkbox changes
    filterCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateActiveFilters();
            updateFilterDisplay();

            if (lastSearchResults.length > 0) {
                displayFilteredResults(lastSearchResults);
            }
        });
    });

    // Clear all filters
    clearBtn.addEventListener('click', () => {
        filterCheckboxes.forEach(cb => cb.checked = false);
        updateActiveFilters();
        updateFilterDisplay();

        if (lastSearchResults.length > 0) {
            displayFilteredResults(lastSearchResults);
        }
    });
}

function updateActiveFilters() {
    const checkboxes = document.querySelectorAll('.filter-checkbox:checked');
    activeFileTypeFilters = Array.from(checkboxes).map(cb => cb.value);
}

function updateFilterDisplay() {
    const selectedText = document.getElementById('filter-selected-text');

    if (activeFileTypeFilters.length === 0) {
        selectedText.textContent = 'All Files';
    } else if (activeFileTypeFilters.length === 1) {
        const type = activeFileTypeFilters[0];
        selectedText.textContent = type.charAt(0).toUpperCase() + type.slice(1);
    } else {
        selectedText.textContent = `${activeFileTypeFilters.length} Types Selected`;
    }
}

function filterFilesByType(files, types) {
    // If no filters selected, show all files
    if (!types || types.length === 0) return files;

    const typeMap = {
        'documents': ['.pdf', '.doc', '.docx'],
        'code': ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.html', '.css', '.scss'],
        'spreadsheets': ['.xlsx', '.xls', '.csv'],
        'presentations': ['.pptx', '.ppt'],
        'text': ['.txt', '.md', '.markdown', '.log', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']
    };

    // Collect all extensions from selected types
    const allExtensions = types.flatMap(type => typeMap[type] || []);

    // Filter files that match any of the extensions
    return files.filter(f =>
        allExtensions.some(ext => f.file_name.toLowerCase().endsWith(ext))
    );
}

function displayFilteredResults(files) {
    // Filter files based on selected types
    const filteredFiles = filterFilesByType(files, activeFileTypeFilters);

    // Find the last assistant message and update its files
    const assistantMessages = Array.from(chatMessages.querySelectorAll('.assistant-message'));
    const lastMessage = assistantMessages[assistantMessages.length - 1];

    if (!lastMessage) return;

    // Find the file-results container
    const fileResultsContainer = lastMessage.querySelector('.file-results');
    if (!fileResultsContainer) return;

    // Clear and rebuild file results
    fileResultsContainer.innerHTML = '';

    filteredFiles.forEach(file => {
        const scorePercent = Math.round(file.similarity_score * 100);
        const fileResultHTML = `
            <div class="file-result" data-path="${escapeHtml(file.file_path)}">
                <div class="file-result-header">
                    <div>
                        <div class="file-name">${escapeHtml(file.file_name)}</div>
                        <div class="file-path">${escapeHtml(file.file_path)}</div>
                    </div>
                    <div class="file-actions">
                        <button class="file-action-btn show-folder-btn" title="Show in folder" data-path="${escapeHtml(file.file_path)}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                            </svg>
                        </button>
                        <button class="file-action-btn summarize-btn" title="Summarize file" data-path="${escapeHtml(file.file_path)}">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="m21 21-4.35-4.35"></path>
                            </svg>
                        </button>
                        <div class="file-type">${file.file_type || 'file'}</div>
                    </div>
                </div>
                ${file.preview ? `<div class="file-preview">${escapeHtml(file.preview)}</div>` : ''}
                <div class="file-summary" style="display: none;"></div>
            </div>
        `;
        fileResultsContainer.insertAdjacentHTML('beforeend', fileResultHTML);
    });

    // Reattach event handlers
    fileResultsContainer.querySelectorAll('.file-result').forEach(el => {
        el.addEventListener('click', async (e) => {
            if (e.target.closest('.summarize-btn') || e.target.closest('.show-folder-btn')) return;
            const path = el.dataset.path;
            await ipcRenderer.invoke('open-file', path);
        });
    });

    fileResultsContainer.querySelectorAll('.show-folder-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const path = btn.dataset.path;
            await ipcRenderer.invoke('show-in-folder', path);
        });
    });

    fileResultsContainer.querySelectorAll('.summarize-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const path = btn.dataset.path;
            const summaryContainer = btn.closest('.file-result').querySelector('.file-summary');

            if (summaryContainer.style.display === 'block') {
                summaryContainer.style.display = 'none';
                btn.classList.remove('active');
                return;
            }

            btn.classList.add('active');
            summaryContainer.style.display = 'block';
            summaryContainer.innerHTML = '<div class="summary-loading">Generating summary...</div>';

            try {
                const result = await ipcRenderer.invoke('summarize-file', path);
                summaryContainer.innerHTML = `
                    <div class="summary-header">📝 Summary</div>
                    <div class="summary-text">${escapeHtml(result.summary)}</div>
                `;
            } catch (error) {
                summaryContainer.innerHTML = `
                    <div class="summary-error">Failed to generate summary: ${escapeHtml(error.message)}</div>
                `;
            }
        });
    });
}
