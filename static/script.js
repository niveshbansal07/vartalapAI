// Global state
let currentConversationId = null;
let isTyping = false;

// DOM Elements
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// Chat containers
const firstMessages = document.getElementById('firstMessages');   // Gemini
const firstChatContainer = document.getElementById('firstChatContainer');
const firstWelcomeScreen = document.getElementById('firstWelcomeScreen');
const firstTypingIndicator = document.getElementById('firstTypingIndicator');

const secondMessages = document.getElementById('secondMessages'); // HuggingFace
const secondChatContainer = document.getElementById('secondChatContainer');
const secondWelcomeScreen = document.getElementById('secondWelcomeScreen');
const secondTypingIndicator = document.getElementById('secondTypingIndicator');

const githubBtn = document.getElementById('githubBtn');

// Sidebar
const historyBtn = document.getElementById('historyBtn');
const historySidebar = document.getElementById('historySidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistoryFromStorage();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    historyBtn.addEventListener('click', toggleSidebar);
    closeSidebarBtn.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);

    githubBtn.addEventListener('click', () => {
        window.open('https://github.com/niveshbansal07', '_blank');
    });

    clearHistoryBtn.addEventListener('click', clearAllHistory);
}

// Send Message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isTyping) return;

    messageInput.value = '';
    sendBtn.disabled = true;
    isTyping = true;

    firstWelcomeScreen.classList.add('hidden');
    secondWelcomeScreen.classList.add('hidden');

    // Add user message to both chats
    addMessage(firstMessages, 'user', message);
    addMessage(secondMessages, 'user', message);

    showTyping(firstTypingIndicator, firstChatContainer);
    showTyping(secondTypingIndicator, secondChatContainer);

    // Call single API
    await callCompareChatAPI(message);

    sendBtn.disabled = false;
    isTyping = false;
    messageInput.focus();
}

// Single API call
async function callCompareChatAPI(message) {
    try {
        const response = await fetch('/compare_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_id: currentConversationId
            })
        });

        const data = await response.json();
        hideTyping(firstTypingIndicator);
        hideTyping(secondTypingIndicator);

        if (response.ok) {
            currentConversationId = data.conversation_id;

            // Add replies to respective chats
            addMessage(firstMessages, 'assistant', data.replies.left, true);
            addMessage(secondMessages, 'assistant', data.replies.right, true);

            saveToLocalStorage(message, `Gemini: ${data.replies.left}\nHuggingFace: ${data.replies.right}`);

            scrollToBottom(firstChatContainer);
            scrollToBottom(secondChatContainer);
        } else {
            addMessage(firstMessages, 'assistant', 'Something went wrong');
            addMessage(secondMessages, 'assistant', 'Something went wrong');
        }
    } catch (err) {
        hideTyping(firstTypingIndicator);
        hideTyping(secondTypingIndicator);
        addMessage(firstMessages, 'assistant', 'Server error');
        addMessage(secondMessages, 'assistant', 'Server error');
    }
}

// Add Message to UI
function addMessage(container, role, content, isMarkdown = false) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const inner = document.createElement('div');
    inner.className = 'message-content';
    inner.innerHTML = isMarkdown ? marked.parse(content) : content;

    msg.appendChild(inner);
    container.appendChild(msg);
}

// Scroll
function scrollToBottom(container) {
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 50);
}

// Typing Indicator
function showTyping(indicator, container) {
    indicator.style.display = 'flex';
    scrollToBottom(container);
}
function hideTyping(indicator) {
    indicator.style.display = 'none';
}

// Sidebar
function toggleSidebar() {
    historySidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
}
function closeSidebar() {
    historySidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
}

// History
function saveToLocalStorage(user, bot) {
    const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    history.push({
        user,
        bot,
        time: new Date().toISOString()
    });
    localStorage.setItem('chatHistory', JSON.stringify(history));
}
function loadHistoryFromStorage() {
    const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    if (!history.length) {
        historyList.innerHTML = '<p class="empty-state">No conversations yet</p>';
        return;
    }
    historyList.innerHTML = history
        .reverse()
        .map(h => `
            <div class="history-item">
                <div>${escapeHtml(h.user)}</div>
                <small>${formatDate(h.time)}</small>
            </div>
        `)
        .join('');
}
function clearAllHistory() {
    if (!confirm('Clear all history?')) return;
    localStorage.removeItem('chatHistory');
    historyList.innerHTML = '<p class="empty-state">No conversations yet</p>';
}

// Utils
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
function formatDate(dateString) {
    const d = new Date(dateString);
    return d.toLocaleString();
}
