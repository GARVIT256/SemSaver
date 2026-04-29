const API_BASE = 'http://127.0.0.1:8000';

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const uploadStatus = document.getElementById('upload-status');
const uploadStatusText = document.getElementById('upload-status-text');
const filesList = document.getElementById('files-list');

const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');

// ── Upload Logic ────────────────────────────────────────────────────────────

// Trigger file input when clicking browse button or drop zone
browseBtn.addEventListener('click', (e) => {
    e.preventDefault();
    fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        handleFiles(fileInput.files);
    }
});

async function handleFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    uploadStatus.classList.remove('hidden');
    uploadStatusText.textContent = `Uploading ${files.length} file(s)...`;
    uploadStatus.querySelector('.spinner').style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData,
            // headers: { 'X-Api-Key': 'if-you-enable-auth-later' }
        });

        const data = await response.json();

        if (response.ok) {
            uploadStatusText.textContent = "Upload successful!";
            uploadStatus.style.color = "var(--success)";
            uploadStatus.querySelector('.spinner').style.display = 'none';
            
            // Add to list
            data.files.forEach(fileName => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <svg class="file-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>${fileName}</span>
                `;
                filesList.appendChild(item);
            });
            
            // Add a bot message notifying success
            appendMessage('bot', `I've successfully ingested ${data.files.length} document(s). You can now ask questions about them!`);
        } else {
            throw new Error(data.detail || "Upload failed");
        }
    } catch (error) {
        uploadStatusText.textContent = error.message;
        uploadStatus.style.color = "var(--error)";
        uploadStatus.querySelector('.spinner').style.display = 'none';
    }
    
    // Reset input
    fileInput.value = '';
}


// ── Chat Logic ──────────────────────────────────────────────────────────────

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Display user message
    appendMessage('user', query);
    chatInput.value = '';
    
    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        removeTypingIndicator(typingId);

        if (response.ok) {
            appendMessage('bot', data.answer, data.sources);
        } else {
            appendMessage('system', data.detail || "Sorry, I encountered an error processing that.");
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        appendMessage('system', "Network error. Make sure the backend is running.");
    }
});

function appendMessage(sender, text, sources = []) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-msg`;
    
    let avatarSvg = '';
    if (sender === 'user') {
        avatarSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path fill-rule="evenodd" d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" clip-rule="evenodd" />
        </svg>`;
    } else {
        avatarSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M11.25 4.533A9.707 9.707 0 006 3a9.735 9.735 0 00-3.25.555.75.75 0 00-.5.707v14.25a.75.75 0 001 .707A8.237 8.237 0 016 18.75c1.995 0 3.823.707 5.25 1.886V4.533zM12.75 20.636A8.214 8.214 0 0118 18.75c1.68 0 3.282.426 4.75 1.191a.75.75 0 001-.707V4.262a.75.75 0 00-.5-.707A9.735 9.735 0 0018 3a9.707 9.707 0 00-5.25 1.533v16.103z" />
        </svg>`;
    }

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        // Filter unique source names using Set
        const uniqueSources = [...new Set(sources)];
        const tags = uniqueSources.map(s => `<span class="source-tag">${s}</span>`).join('');
        sourcesHtml = `<div class="msg-sources">Sources: ${tags}</div>`;
    }

    // Convert newlines to br for basic formatting
    const formattedText = text.replace(/\n/g, '<br>');

    msgDiv.innerHTML = `
        <div class="avatar">${avatarSvg}</div>
        <div class="msg-content">
            <p>${formattedText}</p>
            ${sourcesHtml}
        </div>
    `;
    
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.id = id;
    msgDiv.className = `message bot-msg`;
    msgDiv.innerHTML = `
        <div class="avatar">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M11.25 4.533A9.707 9.707 0 006 3a9.735 9.735 0 00-3.25.555.75.75 0 00-.5.707v14.25a.75.75 0 001 .707A8.237 8.237 0 016 18.75c1.995 0 3.823.707 5.25 1.886V4.533zM12.75 20.636A8.214 8.214 0 0118 18.75c1.68 0 3.282.426 4.75 1.191a.75.75 0 001-.707V4.262a.75.75 0 00-.5-.707A9.735 9.735 0 0018 3a9.707 9.707 0 00-5.25 1.533v16.103z" />
            </svg>
        </div>
        <div class="msg-content typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
