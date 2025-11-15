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

// State
let isProcessing = false;
let isIndexing = false;

// Initialize
init();

async function init() {
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

    // Auto-resize textarea
    chatInput.addEventListener('input', autoResize);

    // Check status periodically
    setInterval(async () => {
        await checkBackendStatus();
        await updateStatus();
    }, 5000);
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
        // Send to backend
        const response = await ipcRenderer.invoke('chat-with-ai', message);

        // Remove thinking indicator
        removeThinking(thinkingId);

        // Add assistant response
        addAssistantMessage(response.response, response.files, response.reasoning);

    } catch (error) {
        removeThinking(thinkingId);
        addAssistantMessage(
            `Sorry, I encountered an error: ${error.message}\n\nMake sure:\n1. Ollama is running (ollama serve)\n2. Llama 3.1 model is installed (ollama pull llama3.1:8b)\n3. Files are indexed`,
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
                        <div class="file-type">${file.file_type || 'file'}</div>
                    </div>
                    ${file.preview ? `<div class="file-preview">${escapeHtml(file.preview)}</div>` : ''}
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
        el.addEventListener('click', () => {
            const path = el.dataset.path;
            shell.openPath(path);
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
    progressText.textContent = 'Indexing files...';
    progressFill.style.width = '50%';

    try {
        const result = await ipcRenderer.invoke('index-files', path, false);

        progressText.textContent = 'Complete!';
        progressFill.style.width = '100%';

        await updateStatus();

        // Add system message to chat
        addAssistantMessage(
            `I've indexed ${result.files_indexed} files from your Desktop. You can now ask me to find files!`,
            [],
            ''
        );

        setTimeout(() => {
            indexProgress.classList.add('hidden');
        }, 3000);

    } catch (error) {
        progressText.textContent = 'Error';
        progressFill.style.width = '0%';
        alert(`Error: ${error.message}`);
    } finally {
        isIndexing = false;
        selectFolderBtn.disabled = false;
        quickIndexBtn.disabled = false;
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
