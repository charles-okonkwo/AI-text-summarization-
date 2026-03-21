// ============================================================================
// ChatGPT-Style Text Summarizer - Frontend JavaScript
// ============================================================================

// Check if speech recognition is supported
const speechRecognitionSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
console.log('Speech Recognition Supported:', speechRecognitionSupported);

// Use localhost for development, production URL for deployed version
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://ai-text-summarization-4.onrender.com';

let conversationHistory = [];

// Speech-to-Text state
let isListening = false;
let recognition = null;

// Initialize Speech Recognition if available
function initSpeechRecognition() {
    try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Speech Recognition not supported in this browser');
            return;
        }
        
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onstart = () => {
            isListening = true;
            const micBtn = document.getElementById('micBtn');
            if (micBtn) micBtn.classList.add('listening');
            console.log('Speech recognition started');
        };
        
        recognition.onresult = (event) => {
            const userInputEl = document.getElementById('userInput');
            if (!userInputEl) return;
            
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            
            if (transcript) {
                userInputEl.value = transcript;
                userInputEl.style.height = 'auto';
                userInputEl.style.height = Math.min(userInputEl.scrollHeight, 200) + 'px';
                console.log('Transcript:', transcript);
            }
        };
        
        recognition.onend = () => {
            isListening = false;
            const micBtn = document.getElementById('micBtn');
            if (micBtn) micBtn.classList.remove('listening');
            console.log('Speech recognition ended');
        };
        
        recognition.onerror = (event) => {
            isListening = false;
            const micBtn = document.getElementById('micBtn');
            if (micBtn) micBtn.classList.remove('listening');
            console.error('Speech recognition error:', event.error);
            alert('Microphone error: ' + event.error);
        };
    } catch (error) {
        console.error('Failed to initialize speech recognition:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM Content Loaded - Initializing Speech Recognition');
        initSpeechRecognition();
    });
} else {
    console.log('DOM Already Loaded - Initializing Speech Recognition');
    initSpeechRecognition();
}

// Also make toggleMicrophone globally available
window.toggleMicrophone = toggleMicrophone;

// DOM Elements
const userInput = document.getElementById('userInput');
const chatMessages = document.getElementById('chatMessages');
const sendBtn = document.querySelector('.send-btn');
const loadingIndicator = document.querySelector('.loading-indicator');
const sidebar = document.getElementById('sidebar');
const newChatBtn = document.querySelector('.new-chat-btn');
const mobileSidebarToggle = document.querySelector('.mobile-sidebar-toggle');
const sidebarToggle = document.querySelector('.sidebar-toggle');
const historyList = document.getElementById('historyList');

// PDF Upload elements
const inputTabs = document.querySelectorAll('.input-tab');
const textMode = document.getElementById('textMode');
const pdfMode = document.getElementById('pdfMode');
const pdfUploadArea = document.getElementById('pdfUploadArea');
let pdfInput = document.getElementById('pdfInput');  // Changed from const to let
const pdfPreview = document.getElementById('pdfPreview');
const pdfFileName = document.getElementById('pdfFileName');
const pdfInstruction = document.getElementById('pdfInstruction');
const sendPdfBtn = document.getElementById('sendPdfBtn');

let selectedPdfFile = null;

// ============================================================================
// Helper Functions for PDF Upload
// ============================================================================

function clickUploadHandler() {
    const fileInput = document.getElementById('pdfInput');
    if (fileInput) {
        fileInput.click();
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

// Input mode tab switching
inputTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const mode = tab.dataset.mode;
        switchInputMode(mode);
    });
});

// PDF upload area click
pdfUploadArea.addEventListener('click', clickUploadHandler);

// PDF file selection
pdfInput.addEventListener('change', handlePdfFileSelect);

// PDF upload area drag and drop
pdfUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    pdfUploadArea.classList.add('dragover');
});

pdfUploadArea.addEventListener('dragleave', () => {
    pdfUploadArea.classList.remove('dragover');
});

pdfUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    pdfUploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        pdfInput.files = files;
        handlePdfFileSelect({ target: { files } });
    }
});

// Send PDF button
sendPdfBtn.addEventListener('click', sendPdfFile);

// Send message on button click
sendBtn.addEventListener('click', sendMessage);

// Send message on Ctrl+Enter or Cmd+Enter
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        sendMessage();
    }
});

// Auto-resize textarea as user types
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 200) + 'px';
});

// New chat button
newChatBtn.addEventListener('click', startNewChat);

// Sidebar toggle buttons (mobile and desktop)
if (mobileSidebarToggle) {
    mobileSidebarToggle.addEventListener('click', toggleSidebar);
}

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
}

// Prevent sidebar from closing when clicking inside it (mobile)
document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !mobileSidebarToggle?.contains(e.target) && !sidebarToggle?.contains(e.target)) {
        if (window.innerWidth < 900) {
            sidebar.classList.remove('open');
        }
    }
});

// ============================================================================
// Message Sending
// ============================================================================

async function sendMessage() {
    const text = userInput.value.trim();

    if (!text) {
        userInput.focus();
        return;
    }

    // Display user message
    displayMessage(text, 'user');

    // Clear input and reset height
    userInput.value = '';
    userInput.style.height = 'auto';

    // Show loading indicator
    showLoading(true);

    try {
        const summary = await getSummary(text);
        displayMessage(summary, 'ai');
        
        // Save to conversation history
        conversationHistory.push({
            timestamp: new Date(),
            userText: text,
            aiResponse: summary
        });
        
        // Save to localStorage
        saveConversationHistory();
    } catch (error) {
        console.error('Error:', error);
        displayMessage(
            'Error: Unable to generate summary. Please try again.',
            'ai'
        );
    } finally {
        showLoading(false);
        userInput.focus();
    }
}

// ============================================================================
// API Communication
// ============================================================================

async function getSummary(text) {
    const response = await fetch(`${API_BASE_URL}/summarize`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get summary');
    }

    const data = await response.json();
    return data.summary;
}

// ============================================================================
// Message Display
// ============================================================================

function displayMessage(message, sender) {
    // Remove welcome section on first message
    const welcomeSection = chatMessages.querySelector('.welcome-section');
    if (welcomeSection) {
        welcomeSection.remove();
    }

    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);

    // Create message content
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.textContent = message;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================================================
// Loading Indicator
// ============================================================================

function showLoading(show) {
    if (show) {
        loadingIndicator.classList.add('active');
    } else {
        loadingIndicator.classList.remove('active');
    }
}

// ============================================================================
// Chat Management
// ============================================================================

function startNewChat() {
    // Clear conversation
    conversationHistory = [];
    
    // Clear messages
    chatMessages.innerHTML = '';
    
    // Reset input
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Reset PDF upload state
    resetPdfUpload();
    
    // Switch back to text mode
    switchInputMode('text');
    
    // Add welcome section back
    const welcomeSection = document.createElement('div');
    welcomeSection.classList.add('welcome-section');
    welcomeSection.innerHTML = `
        <h1>Text Summarizer</h1>
        <p>Paste any text and get an AI-powered summary instantly</p>
    `;
    chatMessages.appendChild(welcomeSection);
    
    // Close sidebar on mobile
    if (window.innerWidth < 900) {
        sidebar.classList.remove('open');
    }
    
    // Focus input
    userInput.focus();
}

// ============================================================================
// Sidebar Management
// ============================================================================

function toggleSidebar() {
    sidebar.classList.toggle('open');
}

// ============================================================================
// History Management
// ============================================================================

function saveConversationHistory() {
    // Save to localStorage
    localStorage.setItem('summarizerHistory', JSON.stringify(conversationHistory));
    updateHistoryUI();
}

function updateHistoryUI() {
    historyList.innerHTML = '';
    
    if (conversationHistory.length === 0) {
        historyList.innerHTML = '<div class="empty-state">No conversation history</div>';
        return;
    }
    
    // Show only last 10 conversations
    const recentConversations = conversationHistory.slice(-10).reverse();
    
    recentConversations.forEach((conv, index) => {
        const historyItem = document.createElement('button');
        historyItem.classList.add('history-item');
        
        // Extract first 30 characters of user text as label
        const label = conv.userText.substring(0, 30) + (conv.userText.length > 30 ? '...' : '');
        historyItem.textContent = label;
        historyItem.title = conv.userText;
        
        // Load conversation on click
        historyItem.addEventListener('click', () => {
            loadConversation(conv);
        });
        
        historyList.appendChild(historyItem);
    });
}

function loadConversation(conv) {
    // Clear current chat
    chatMessages.innerHTML = '';
    
    // Display the conversation
    displayMessage(conv.userText, 'user');
    displayMessage(conv.aiResponse, 'ai');
    
    // Close sidebar on mobile
    if (window.innerWidth < 900) {
        sidebar.classList.remove('open');
    }
}

// ============================================================================
// Input Mode Management
// ============================================================================

function switchInputMode(mode) {
    // Update tabs
    inputTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.mode === mode);
    });
    
    // Update modes
    if (mode === 'text') {
        textMode.style.display = 'flex';
        pdfMode.style.display = 'none';
        userInput.focus();
    } else if (mode === 'pdf') {
        textMode.style.display = 'none';
        pdfMode.style.display = 'flex';
    }
}

// ============================================================================
// Speech-to-Text Functions
// ============================================================================

function toggleMicrophone() {
    console.log('Toggle microphone called, recognition:', recognition, 'isListening:', isListening);
    
    if (!recognition) {
        alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
        return;
    }
    
    try {
        if (isListening) {
            console.log('Stopping speech recognition');
            recognition.stop();
        } else {
            // Clear previous input and start listening
            const userInputEl = document.getElementById('userInput');
            if (userInputEl) {
                userInputEl.value = '';
            }
            console.log('Starting speech recognition');
            recognition.start();
        }
    } catch (error) {
        console.error('Error toggling microphone:', error);
        alert('Microphone error: ' + error.message);
    }
}

// ============================================================================
// PDF File Handling
// ============================================================================

function resetPdfUpload() {
    // Clear the selected file
    selectedPdfFile = null;
    
    // Clear instruction text
    if (pdfInstruction) {
        pdfInstruction.value = '';
    }
    
    // Reset file input by setting value to empty string
    // This allows selecting the same file again or different files
    if (pdfInput) {
        pdfInput.value = '';
    }
    
    // Reset UI
    pdfUploadArea.style.display = 'flex';
    pdfPreview.style.display = 'none';
}

function handlePdfFileSelect(event) {
    const files = event.target.files;
    if (files.length === 0) return;
    
    const file = files[0];
    
    // Validate file type
    if (!file.type.includes('pdf')) {
        alert('Please select a valid PDF file');
        return;
    }
    
    // Validate file size (50MB limit)
    if (file.size > 50 * 1024 * 1024) {
        alert('File is too large. Maximum size is 50MB');
        return;
    }
    
    // Store file and show preview
    selectedPdfFile = file;
    pdfUploadArea.style.display = 'none';
    pdfPreview.style.display = 'flex';
    pdfFileName.textContent = `📄 ${file.name}`;
}

async function sendPdfFile() {
    if (!selectedPdfFile) {
        alert('Please select a PDF file first');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedPdfFile);
    
    // Get instruction text if provided
    const instruction = pdfInstruction.value.trim();
    if (instruction) {
        formData.append('instruction', instruction);
    }
    
    // Display file info message with instruction if provided
    let userMessage = `📄 Processing PDF: ${selectedPdfFile.name}`;
    if (instruction) {
        userMessage += `\n📝 Instructions: ${instruction}`;
    }
    displayMessage(userMessage, 'user');
    
    // Show loading
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/summarize-pdf`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to summarize PDF');
        }
        
        const data = await response.json();
        displayMessage(data.summary, 'ai');
        
        // Save to history
        conversationHistory.push({
            timestamp: new Date(),
            userText: `PDF: ${selectedPdfFile.name}${instruction ? '\nInstructions: ' + instruction : ''}`,
            aiResponse: data.summary
        });
        
        saveConversationHistory();
    } catch (error) {
        console.error('Error:', error);
        displayMessage(
            'Error: Unable to summarize PDF. Please try again.',
            'ai'
        );
    } finally {
        showLoading(false);
        
        // Reset PDF upload state to allow uploading another PDF in same chat
        resetPdfUpload();
    }
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load history from localStorage
    const savedHistory = localStorage.getItem('summarizerHistory');
    if (savedHistory) {
        try {
            conversationHistory = JSON.parse(savedHistory);
            updateHistoryUI();
        } catch (e) {
            console.error('Error loading history:', e);
        }
    } else {
        historyList.innerHTML = '<div class="empty-state">No conversation history</div>';
    }
    
    // Focus input on load
    userInput.focus();
});
