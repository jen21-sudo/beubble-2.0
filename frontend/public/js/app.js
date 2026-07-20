// ============================================================
// CONFIGURATION
// ============================================================

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${protocol}//${window.location.host}/ws/agent`;
const API_BASE = window.location.origin;

// ============================================================
// DOM REFS
// ============================================================

const terminalEl = document.getElementById('terminal');
const chatMessages = document.getElementById('chat-messages');
const status = document.getElementById('status');
const promptInput = document.getElementById('promptInput');
const sendBtn = document.getElementById('sendBtn');
const sessionInfo = document.getElementById('session-info');
const fileTree = document.getElementById('file-tree');

let isLoading = false;
let ws = null;

// ============================================================
// WEBSOCKET
// ============================================================

function connectWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        status.className = 'status online';
        status.textContent = '● Online';
        promptInput.disabled = false;
        sendBtn.disabled = false;
        addSystemMessage('✅ Connected to Beubble 2.0');
        addTerminalLine('SYSTEM', '✅ Connected to Beubble 2.0', 'status');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = () => {
        status.className = 'status offline';
        status.textContent = '● Offline';
        promptInput.disabled = true;
        sendBtn.disabled = true;
        hideLoading();
        addTerminalLine('ERROR', '❌ Disconnected from server', 'error');
    };
    
    ws.onerror = () => {
        status.className = 'status error';
        status.textContent = '● Error';
    };
}

function handleWebSocketMessage(data) {
    const type = data.type;
    
    switch (type) {
        case 'plan':
            addPlanDisplay(data.content);
            break;
            
        case 'screenshot':
            const tab = data.data?.tab_name || 'N/A';
            const url = data.data?.url || 'N/A';
            addTerminalLine('BROWSER', `📸 Screenshot - Tab: ${tab} | URL: ${url}`, 'browser');
            break;
            
        case 'bot_response':
            addAgentMessage(data.content);
            if (data.files && data.files.length > 0) {
                const filesList = data.files.join(', ');
                addTerminalLine('DATA', `📁 Files created: ${filesList}`, 'data');
                addFileNotification(`📁 ${data.files.length} file(s) created`);
                refreshWorkspace();
            }
            hideLoading();
            break;
            
        case 'log':
            handleLogMessage(data);
            break;
            
        case 'status':
            addTerminalLine('STATUS', `⏳ ${data.content}`, 'status');
            break;
            
        case 'error':
            addTerminalLine('ERROR', `❌ ${data.content}`, 'error');
            addSystemMessage(`❌ Error: ${data.content}`);
            hideLoading();
            break;
            
        case 'info':
            if (data.content.includes('Session:')) {
                sessionInfo.textContent = `📝 ${data.content}`;
            }
            addTerminalLine('INFO', `ℹ️ ${data.content}`, 'info');
            break;
            
        default:
            addTerminalLine('LOG', data.content || 'Unknown message', 'log');
    }
}

function handleLogMessage(data) {
    const content = data.content || '';
    let tag = 'log';
    let color = '#8e8e93';
    
    if (content.includes('Navigator') || content.includes('🌐')) {
        tag = 'SUB-AGENT';
        color = '#5ac8fa';
    } else if (content.includes('Terminal') || content.includes('💻')) {
        tag = 'SUB-AGENT';
        color = '#5ac8fa';
    } else if (content.includes('API') || content.includes('🔌')) {
        tag = 'SUB-AGENT';
        color = '#5ac8fa';
    } else if (content.includes('Phase')) {
        tag = 'SUB-AGENT';
        color = '#5ac8fa';
    } else if (content.includes('✅') && content.includes('[Shared]')) {
        tag = 'STATUS';
        color = '#34c759';
    } else if (content.includes('⚠️')) {
        tag = 'STATUS';
        color = '#ff9500';
    } else if (content.includes('❌') || content.toLowerCase().includes('error')) {
        tag = 'ERROR';
        color = '#ff3b30';
    } else if (data.level === 'ERROR') {
        tag = 'ERROR';
        color = '#ff3b30';
    } else if (content.includes('Files created')) {
        tag = 'DATA';
        color = '#af52de';
    } else if (content.includes('⏱️')) {
        tag = 'STATUS';
        color = '#34c759';
    } else {
        tag = 'LOG';
        color = '#8e8e93';
    }
    
    addTerminalLine(tag, content, tag.toLowerCase());
}

// ============================================================
// TERMINAL
// ============================================================

function addTerminalLine(tag, content, className) {
    const line = document.createElement('div');
    line.className = 'line';
    
    const timestamp = new Date().toLocaleTimeString();
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = `[${timestamp}] `;
    
    const tagSpan = document.createElement('span');
    tagSpan.className = `tag-${className || 'log'}`;
    tagSpan.textContent = `[${tag}] `;
    
    const contentSpan = document.createElement('span');
    contentSpan.textContent = content;
    
    line.appendChild(timeSpan);
    line.appendChild(tagSpan);
    line.appendChild(contentSpan);
    
    // Remove placeholder if exists
    const placeholder = terminalEl.querySelector('.terminal-placeholder');
    if (placeholder) placeholder.remove();
    
    terminalEl.appendChild(line);
    terminalEl.scrollTop = terminalEl.scrollHeight;
}

function clearTerminal() {
    terminalEl.innerHTML = '';
    const placeholder = document.createElement('div');
    placeholder.className = 'terminal-placeholder';
    placeholder.textContent = '⏳ Waiting for agent output...';
    terminalEl.appendChild(placeholder);
}

// ============================================================
// CHAT
// ============================================================

function addUserMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message user';
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addAgentMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message agent';
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addSystemMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message system';
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addFileNotification(text) {
    const msg = document.createElement('div');
    msg.className = 'message system file-notification';
    msg.textContent = `📁 ${text}`;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addPlanDisplay(text) {
    const msg = document.createElement('div');
    msg.className = 'message system';
    msg.style.cssText = `
        align-self: center;
        background: rgba(0, 122, 255, 0.08);
        border: 1px solid rgba(0, 122, 255, 0.2);
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 12px;
        font-family: monospace;
        max-width: 95%;
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
        color: var(--text-primary);
    `;
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading() {
    isLoading = true;
    sendBtn.disabled = true;
    promptInput.disabled = true;
    
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'message agent';
    loadingMsg.id = 'loading-message';
    loadingMsg.innerHTML = `
        <span class="loading-spinner"></span>
        Processing<span class="loading-dots"></span>
    `;
    chatMessages.appendChild(loadingMsg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    addTerminalLine('STATUS', '⏳ Processing request...', 'status');
}

function hideLoading() {
    isLoading = false;
    sendBtn.disabled = false;
    promptInput.disabled = false;
    const loadingMsg = document.getElementById('loading-message');
    if (loadingMsg) loadingMsg.remove();
}

function sendMission() {
    const input = promptInput;
    if (input.value.trim() === '' || isLoading) return;
    
    addUserMessage(input.value);
    showLoading();
    ws.send(JSON.stringify({ prompt: input.value }));
    input.value = '';
}

// ============================================================
// WORKSPACE
// ============================================================

async function refreshWorkspace() {
    try {
        const response = await fetch('/api/workspace');
        const data = await response.json();
        renderTree(data.items);
    } catch (e) {
        fileTree.innerHTML = '<div style="color: #ff3b30;">❌ Error loading workspace</div>';
    }
}

function renderTree(items, container) {
    const tree = container || fileTree;
    if (!container) tree.innerHTML = '';
    
    if (!items || items.length === 0) {
        const empty = document.createElement('div');
        empty.style.cssText = 'color: #63636b; font-size: 12px; padding: 10px 0;';
        empty.textContent = '📂 Empty workspace';
        tree.appendChild(empty);
        return;
    }
    
    for (const item of items) {
        const div = document.createElement('div');
        const icon = item.type === 'folder' ? '📁' : '📄';
        
        if (item.type === 'folder') {
            div.innerHTML = `
                <span class="item folder">
                    <span>${icon}</span>
                    <span>${escapeHtml(item.name)}</span>
                </span>
            `;
            div.onclick = (e) => {
                e.stopPropagation();
                const children = div.nextElementSibling;
                if (children) {
                    children.style.display = children.style.display === 'none' ? 'block' : 'none';
                }
            };
            tree.appendChild(div);
            
            if (item.children && item.children.length > 0) {
                const childContainer = document.createElement('div');
                childContainer.className = 'children';
                renderTree(item.children, childContainer);
                tree.appendChild(childContainer);
            }
        } else {
            div.className = 'item file';
            div.innerHTML = `
                <span>${icon}</span>
                <span>${escapeHtml(item.name)}</span>
                <span class="file-size">${item.size_str || ''}</span>
            `;
            div.onclick = () => {
                window.open(`/api/workspace/download/${encodeURIComponent(item.path)}`, '_blank');
            };
            
            div.oncontextmenu = async (e) => {
                e.preventDefault();
                if (confirm(`Delete ${item.name}?`)) {
                    await fetch(`/api/workspace/${encodeURIComponent(item.path)}`, { method: 'DELETE' });
                    refreshWorkspace();
                    addTerminalLine('DATA', `🗑️ Deleted: ${item.name}`, 'data');
                }
            };
            tree.appendChild(div);
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// FILE UPLOAD
// ============================================================

async function uploadFiles(event) {
    const files = event.target.files;
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        await fetch('/api/workspace/upload', { method: 'POST', body: formData });
    }
    refreshWorkspace();
    event.target.value = '';
    addTerminalLine('DATA', `📤 Uploaded ${files.length} file(s)`, 'data');
}

// Drag & Drop
const uploadZone = document.getElementById('upload-zone');
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '#007aff';
});
uploadZone.addEventListener('dragleave', () => {
    uploadZone.style.borderColor = '';
});
uploadZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '';
    for (const file of e.dataTransfer.files) {
        const formData = new FormData();
        formData.append('file', file);
        await fetch('/api/workspace/upload', { method: 'POST', body: formData });
    }
    refreshWorkspace();
    addTerminalLine('DATA', `📤 Uploaded ${e.dataTransfer.files.length} file(s)`, 'data');
});

// ============================================================
// FOLDER MANAGEMENT
// ============================================================

function showCreateFolder() {
    document.getElementById('folder-modal').classList.remove('hidden');
    document.getElementById('folder-name-input').value = '';
    document.getElementById('folder-name-input').focus();
}

function closeModal() {
    document.getElementById('folder-modal').classList.add('hidden');
}

async function createFolder() {
    const name = document.getElementById('folder-name-input').value.trim();
    if (!name) return;
    
    try {
        const response = await fetch('/api/workspace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: name, type: 'folder' })
        });
        if (response.ok) {
            refreshWorkspace();
            addTerminalLine('DATA', `📁 Folder created: ${name}`, 'data');
            closeModal();
        } else {
            addTerminalLine('ERROR', `❌ Failed to create folder: ${name}`, 'error');
        }
    } catch (e) {
        addTerminalLine('ERROR', `❌ Error creating folder: ${e.message}`, 'error');
    }
}

// Enter key for modal
document.getElementById('folder-name-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') createFolder();
});

// Close modal on backdrop click
document.getElementById('folder-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeModal();
});

// ============================================================
// THEME TOGGLE
// ============================================================

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================

promptInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !isLoading) sendMission();
});

// ============================================================
// INIT
// ============================================================

connectWebSocket();
refreshWorkspace();

console.log('🚀 Beubble 2.0 Frontend loaded');
console.log(`🔗 WebSocket: ${WS_URL}`);
console.log(`🌓 Theme: ${savedTheme}`);
